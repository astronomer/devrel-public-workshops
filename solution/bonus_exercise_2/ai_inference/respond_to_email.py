from airflow.providers.standard.operators.hitl import HITLOperator
from airflow.sdk import Param, chain, dag, task
from pydantic import BaseModel, Field
from pydantic_ai.usage import UsageLimits

from include.aimlops.assets import INBOUND_PROSPECT_EMAIL, INTERACTION_COMPLETE
from include.prompts import DRAFTER_SYSTEM_PROMPT, JUDGE_SYSTEM_PROMPT
from include.rag import CONTEXT_TOOLSET
from include.spend import PREDICT_FOOD_SPEND_TOOL
from include.sql_tools import SQL_TOOLSET as _SQL_TOOLSET

_LLM_CONN_ID = "pydanticai_default"
_AGENT_SENDER = "john@astrotrips.example"
_USAGE_LIMITS = UsageLimits(request_limit=50)


class DraftResult(BaseModel):
    email: str = Field(description="The full email reply body to send to the prospect")
    context_used: list[str] = Field(
        default_factory=list,
        description="chunk_ids of the context units you relied on to write this reply",
    )
    estimated_spend: float | None = Field(
        default=None,
        description="Predicted food spend per person per day from the spend tool, if you used it; null otherwise",
    )
    reasoning: str = Field(
        default="",
        description="One or two sentences on why this reply and any offer you made",
    )


class JudgeVerdict(BaseModel):
    grade: str = Field(description="A-F quality grade for the drafted reply")
    reasoning: str = Field(description="Why the draft earned this grade")
    issues: list[str] = Field(
        description="At most 5 concrete problems to fix, each a single short sentence"
    )


def _conversation(thread: dict) -> str:
    return "\n\n".join(
        f"[{m['direction']}] {m['sender']}\n{m['body']}" for m in thread["messages"]
    )


def _email_of(draft) -> str:
    return draft["email"] if isinstance(draft, dict) else draft


@dag(
    schedule=[INBOUND_PROSPECT_EMAIL],
    tags=["Bonus exercise 2"],
)
def respond_to_email():

    @task
    def load_thread() -> dict:
        from collections import defaultdict

        from include.aimlops.persistence import load_records

        by_thread = defaultdict(list)
        for m in load_records("email_messages"):
            by_thread[m["thread_id"]].append(m)

        awaiting = []
        for thread in load_records("email_threads"):
            msgs = sorted(by_thread.get(thread["thread_id"], []), key=lambda m: m["turn"])
            if msgs and msgs[-1]["direction"] == "inbound":
                awaiting.append((thread, msgs))

        if not awaiting:
            raise ValueError("No thread is awaiting a reply.")

        thread, msgs = max(awaiting, key=lambda a: a[0]["thread_id"])
        return {
            "thread_id": thread["thread_id"],
            "subject": thread["subject"],
            "customer_id": thread["customer_id"],
            "next_turn": msgs[-1]["turn"] + 1,
            "messages": [
                {"direction": m["direction"], "sender": m["sender"], "body": m["body"]}
                for m in msgs
            ],
        }

    @task.agent(
        llm_conn_id=_LLM_CONN_ID,
        system_prompt=DRAFTER_SYSTEM_PROMPT,
        output_type=DraftResult,
        toolsets=[CONTEXT_TOOLSET, _SQL_TOOLSET, PREDICT_FOOD_SPEND_TOOL],
        usage_limits=_USAGE_LIMITS,
    )
    def draft_reply(thread: dict) -> str:
        return (
            "Write a reply to the most recent email in this thread. Return the email "
            "body, the chunk_ids of the context units you used, and a one sentence "
            "rationale.\n\n"
            f"Customer ID: {thread['customer_id']}\n"
            f"Subject: {thread['subject']}\n\n{_conversation(thread)}"
        )

    @task.agent(
        llm_conn_id=_LLM_CONN_ID,
        output_type=JudgeVerdict,
        system_prompt=JUDGE_SYSTEM_PROMPT,
        toolsets=[CONTEXT_TOOLSET, _SQL_TOOLSET],
        usage_limits=_USAGE_LIMITS,
    )
    def judge_reply(draft: dict) -> str:
        from airflow.sdk import get_current_context

        spend = get_current_context()["ti"].xcom_pull(
            task_ids="draft_reply", key="estimated_spend"
        )
        spend_line = (
            f"Predicted food spend for this prospect: ${spend:.0f} per person per day."
            if spend is not None
            else "No food spend was predicted for this prospect."
        )
        return (
            f"Review and grade this drafted sales reply.\n\n{spend_line}\n\n{_email_of(draft)}"
        )

    _human_in_the_loop = HITLOperator(
        task_id="human_in_the_loop",
        subject="Review the prospect reply",
        body=(
            "{% set t = ti.xcom_pull(task_ids='load_thread') %}"
            "{% set inquiry = t['messages'] | last %}"
            "{% set d = ti.xcom_pull(task_ids='draft_reply') %}"
            "{% set spend = ti.xcom_pull(task_ids='draft_reply', key='estimated_spend') %}"
            "{% set v = ti.xcom_pull(task_ids='judge_reply') %}"
            "## Original inquiry\n\n"
            "{{ inquiry['body'] }}\n\n"
            "---\n\n"
            "## Drafted reply\n\n"
            "{{ d['email'] }}\n\n"
            "---\n\n"
            "## Predicted food spend\n\n"
            "{% if spend is not none %}**${{ spend | round | int }} per person per day**"
            "{% else %}Not estimated for this prospect.{% endif %}\n\n"
            "---\n\n"
            "## Judge verdict\n\n"
            "**Grade: {{ v['grade'] }}**\n\n"
            "{{ v['reasoning'] }}\n\n"
            "{% if v['issues'] %}**Issues to fix**\n\n"
            "{% for issue in v['issues'] %}{{ loop.index }}. {{ issue }}\n"
            "{% endfor %}{% endif %}"
        ),
        options=["approve", "rewrite", "reject"],
        defaults="approve",
        params={
            "reason": Param(
                "",
                type="string",
                title="Reason / rewrite instructions",
                description="Why you approved or rejected, or what to change on a rewrite.",
            ),
            "apply_judge_suggestions": Param(
                False,
                type="boolean",
                title="Make AI suggestions available to rewrite agent",
                description="When checked, the rewrite agent has access to the judge suggestions, use the rewrite instructions to say which to implement.",
            ),
        },
    )

    @task.branch
    def route(decision: dict) -> str:
        chosen = decision.get("chosen_options", []) if isinstance(decision, dict) else []
        if "approve" in chosen:
            return "send_as_drafted"
        if "rewrite" in chosen:
            return "revise_reply"
        return "reject_reply"

    @task
    def send_as_drafted(draft: dict) -> dict:
        return draft

    @task.agent(
        llm_conn_id=_LLM_CONN_ID,
        system_prompt=DRAFTER_SYSTEM_PROMPT,
        output_type=DraftResult,
        usage_limits=_USAGE_LIMITS,
    )
    def revise_reply(draft: dict, decision: dict, verdict: dict) -> str:
        params = decision.get("params_input") or {}
        reason = params.get("reason", "")
        judge_block = ""
        if params.get("apply_judge_suggestions"):
            points = "\n".join(
                f"{i}. {issue}" for i, issue in enumerate(verdict.get("issues", []), 1)
            ) or "(none)"
            judge_block = f"\n\n<judge_suggestions>\n{points}\n</judge_suggestions>"
        return (
            "You are revising a drafted sales reply. Make ONLY the changes the "
            "reviewer asks for and leave everything else in the email exactly as it "
            "is, including any personalization or offers you were not asked to "
            "change. Do not rewrite or improve anything you were not told to change.\n\n"
            "If a <judge_suggestions> section is present, also apply those numbered "
            "fixes, unless the reviewer names specific ones (for example 'apply only "
            "1 and 3'), in which case apply only those. If there is no "
            "<judge_suggestions> section, ignore the judge entirely.\n\n"
            "Return the revised email body and a one sentence rationale.\n\n"
            f"<reviewer_instructions>\n{reason}\n</reviewer_instructions>\n\n"
            f"<original_draft>\n{_email_of(draft)}\n</original_draft>"
            f"{judge_block}"
        )

    @task
    def reject_reply() -> None:
        raise RuntimeError("Prospect reply rejected by the human reviewer.")

    @task(trigger_rule="none_failed_min_one_success", outlets=[INTERACTION_COMPLETE])
    def send_reply(thread: dict, approved: dict, revised: dict) -> None:
        # Runs on approve or rewrite; skipped when the branch routed to reject.
        final = revised or approved
        if not final:
            return

        from include.aimlops.persistence import get_duckdb_conn, sync_table_to_variable

        conn = get_duckdb_conn()
        conn.execute(
            "INSERT INTO email_messages (thread_id, turn, direction, sender, body) "
            "VALUES (?, ?, 'outbound', ?, ?)",
            [thread["thread_id"], thread["next_turn"], _AGENT_SENDER, _email_of(final)],
        )
        conn.close()
        sync_table_to_variable("email_messages")

    _thread = load_thread()
    _draft = draft_reply(_thread)
    _verdict = judge_reply(_draft)
    chain(_verdict, _human_in_the_loop)

    _route = route(_human_in_the_loop.output)
    _approved = send_as_drafted(_draft)
    _revised = revise_reply(_draft, _human_in_the_loop.output, _verdict)
    _rejected = reject_reply()
    chain(_route, [_approved, _revised, _rejected])

    _send_reply = send_reply(_thread, _approved, _revised)
    chain(_rejected, _send_reply)


respond_to_email()
