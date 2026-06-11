from pendulum import duration
from airflow.configuration import AIRFLOW_HOME
from airflow.exceptions import AirflowSkipException
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.standard.operators.hitl import HITLBranchOperator
from airflow.sdk import Asset, chain, dag, task, task_group
from pydantic_ai.toolsets import FunctionToolset

from include.agent_tools import find_similar_reviews, lookup_booking

_DUCKDB_CONN_ID = "duckdb_astrotrips"


@dag(
    schedule=(Asset("routed-reviews") & Asset("embedded-reviews")),
    tags=["astrotrips", "ai", "reviews", "hitl"],
    template_searchpath=f"{AIRFLOW_HOME}/include/sql",
    default_args={"retries": 3, "retry_delay": duration(seconds=10)},
)
def respond_reviews():

    _reviews = SQLExecuteQueryOperator(
        task_id="get_reviews",
        conn_id=_DUCKDB_CONN_ID,
        sql=(
            "SELECT review_id, booking_id, review_text, sentiment, category, summary "
            "FROM trip_reviews WHERE status = 'routed' AND ai_response IS NULL "
            "ORDER BY submitted_at ASC LIMIT 1"
        ),
    )

    @task
    def prepare_review(query_result):
        if not query_result:
            raise AirflowSkipException("No unprocessed reviews found")
        row = query_result[0]
        return {
            "review_id": row[0],
            "booking_id": row[1],
            "text": row[2],
            "sentiment": row[3],
            "category": row[4],
            "summary": row[5],
        }

    _review_data = prepare_review(_reviews.output)

    @task_group
    def respond_one_review(review_data):

        @task
        def format_context(data):
            return (
                f"Review #{data['review_id']} (booking #{data['booking_id']}):\n"
                f"Category: {data['category']} | Sentiment: {data['sentiment']}\n"
                f"Summary: {data['summary']}\n\n"
                f"Full review:\n{data['text']}"
            )

        @task.agent(
            llm_conn_id="pydanticai_default",
            system_prompt=(
                "You are a customer service agent for AstroTrips, an interplanetary travel company. "
                "Your job is to draft a professional, empathetic response to a customer's trip review.\n\n"
                "Guidelines:\n"
                "- Use the lookup_booking tool to find the customer's booking details.\n"
                "- Use the find_similar_reviews tool to see how similar feedback was handled.\n"
                "- Address the customer's specific concerns with empathy.\n"
                "- Reference concrete details from their booking (destination, dates, fare paid).\n"
                "- For safety concerns: acknowledge and assure investigation.\n"
                "- For billing issues: reference actual amounts and offer to review.\n"
                "- For positive reviews: thank them warmly and invite them back.\n"
                "- Keep the response under 200 words.\n"
                "- Sign off as 'AstroTrips Customer Experience Team'."
            ),
            toolsets=[FunctionToolset(tools=[lookup_booking, find_similar_reviews])],
            enable_hitl_review=True,
        )
        def draft_response(prompt: str) -> str:
            return prompt

        @task
        def extract_id(data):
            return data["review_id"]

        _context = format_context(review_data)
        _response = draft_response(_context)
        _id = extract_id(review_data)

        _save_draft = SQLExecuteQueryOperator(
            task_id="save_draft",
            conn_id=_DUCKDB_CONN_ID,
            sql=(
                "UPDATE trip_reviews SET status = 'response_drafted', "
                "ai_response = $response WHERE review_id = $id::INT"
            ),
            parameters={"id": _id, "response": _response},
        )

        _review_branch = HITLBranchOperator(
            task_id="review_response",
            subject="Review response approval",
            body=(
                "Please review the AI-drafted response and approve or reject it.\n\n"
                "**Review ID:** {{ ti.xcom_pull(task_ids='respond_one_review.extract_id') }}\n\n"
                "**Drafted response:**\n\n"
                "{{ ti.xcom_pull(task_ids='respond_one_review.draft_response') }}"
            ),
            options=["Approve", "Reject"],
            options_mapping={
                "Approve": "respond_one_review.finalize",
                "Reject": "respond_one_review.mark_rejected",
            },
        )

        _finalize = SQLExecuteQueryOperator(
            task_id="finalize",
            conn_id=_DUCKDB_CONN_ID,
            sql=(
                "UPDATE trip_reviews SET status = 'approved', "
                "approved_at = CURRENT_TIMESTAMP WHERE review_id = $id::INT"
            ),
            parameters={"id": _id},
        )

        _mark_rejected = SQLExecuteQueryOperator(
            task_id="mark_rejected",
            conn_id=_DUCKDB_CONN_ID,
            sql="UPDATE trip_reviews SET status = 'rejected' WHERE review_id = $id::INT",
            parameters={"id": _id},
        )

        chain(_save_draft, _review_branch, [_finalize, _mark_rejected])

    @task(outlets=[Asset("responded-reviews")], trigger_rule="none_failed_min_one_success")
    def response_gen_complete():
        print("Response generation complete for all new reviews")

    chain(
        respond_one_review(review_data=_review_data),
        response_gen_complete()
    )


respond_reviews()
