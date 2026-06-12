from typing import Literal

from airflow.sdk import chain, dag, task
from pydantic import BaseModel, Field

from include.aimlops.assets import AI_FEATURES_READY
from include.mission_control import MissionControlOperator
from include.prompts import FEATURE_EXTRACTION_SYSTEM_PROMPT

_LLM_CONN_ID = "pydanticai_default"
_MAX_PROSPECT_EMAILS = 5


class ProspectFeatures(BaseModel):
    """Enum features extracted from email text, one-hot encoded for the regression."""

    trip_occasion: Literal[
        "celebration", "family", "business", "budget", "adventure", "other"
    ] = Field(description="What kind of trip the prospect is planning")
    enthusiasm: Literal["low", "medium", "high"] = Field(
        description="How eager and ready to book the prospect sounds"
    )
    budget_signal: Literal["low", "medium", "high"] = Field(
        description="low = cost-conscious language, high = premium / price-insensitive"
    )


@dag(
    schedule=None,
    tags=["exercise 3"],
    doc_md=__doc__,
)
def feature_engineering_ai():

    @task
    def load_prospect_emails() -> list[dict]:
        from include.aimlops.persistence import load_records

        inbound = [
            {"thread_id": m["thread_id"], "body": m["body"]}
            for m in load_records("email_messages")
            if m["direction"] == "inbound"
        ]
        return inbound[:_MAX_PROSPECT_EMAILS]

    @task.agent(
        llm_conn_id=_LLM_CONN_ID,
        output_type=ProspectFeatures,
        system_prompt=FEATURE_EXTRACTION_SYSTEM_PROMPT,
    )
    def extract_features(email: dict) -> str:
        return f"Extract the features from this prospect email:\n\n{email['body']}"

    @task
    def fill_historical_features() -> None:
        from include.aimlops.ai_features import synthetic_ai_features
        from include.aimlops.persistence import get_duckdb_conn, load_records, replace_table

        records = synthetic_ai_features(load_records("bookings"))
        columns = ["booking_id", "trip_occasion", "enthusiasm", "budget_signal"]
        with get_duckdb_conn() as conn:
            replace_table(conn, "ai_features", columns, records)

    @task(outlets=[AI_FEATURES_READY])
    def write_features(extracted: list) -> None:
        from include.aimlops.persistence import get_duckdb_conn, sync_table_to_variable

        def _field(item, name):
            return item[name] if isinstance(item, dict) else getattr(item, name)

        with get_duckdb_conn() as conn:
            for booking_id, feat in enumerate(extracted, start=1):
                conn.execute(
                    "UPDATE ai_features SET trip_occasion = ?, enthusiasm = ?, "
                    "budget_signal = ? WHERE booking_id = ?",
                    [
                        _field(feat, "trip_occasion"),
                        _field(feat, "enthusiasm"),
                        _field(feat, "budget_signal"),
                        booking_id,
                    ],
                )
        sync_table_to_variable("ai_features")

    _emails = load_prospect_emails()
    _extracted = extract_features.expand(email=_emails)
    _filled = fill_historical_features()
    _written = write_features(_extracted)
    mission_control = MissionControlOperator(task_id="mission_control")
    chain(_filled, _written, mission_control)


feature_engineering_ai()