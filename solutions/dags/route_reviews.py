from pendulum import duration
from airflow.configuration import AIRFLOW_HOME
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sdk import Asset, dag, task, task_group, chain

from include.mission_control import MissionControlOperator

_DUCKDB_CONN_ID = "duckdb_astrotrips"


@dag(
    schedule=Asset("analyzed-reviews"),
    tags=["astrotrips", "ai", "reviews"],
    template_searchpath=f"{AIRFLOW_HOME}/include/sql",
    default_args={"retries": 3, "retry_delay": duration(seconds=10)},
    max_active_tasks=1,
)
def route_reviews():

    _reviews = SQLExecuteQueryOperator(
        task_id="get_reviews",
        conn_id=_DUCKDB_CONN_ID,
        sql=(
            "SELECT review_id, review_text, sentiment, category, summary "
            "FROM trip_reviews WHERE status = 'analyzed' "
            "ORDER BY submitted_at ASC"
        ),
    )

    @task
    def prepare_review_list(query_result):
        if not query_result:
            return []
        return [
            {
                "review_id": row[0],
                "text": row[1],
                "sentiment": row[2],
                "category": row[3],
                "summary": row[4],
            }
            for row in query_result
        ]

    _review_list = prepare_review_list(_reviews.output)

    @task_group
    def handle_review(review_data):

        # route based on review content using LLM

        @task
        def format_context(data):
            return (
                f"Review #{data['review_id']} (sentiment: {data['sentiment']}, "
                f"category: {data['category']}):\n"
                f"Summary: {data['summary']}\n\n"
                f"Full review:\n{data['text']}"
            )

        @task.llm_branch(
            llm_conn_id="pydanticai_default",
            system_prompt=(
                "You are a support ticket router for AstroTrips, an interplanetary travel company. "
                "Based on the customer review below, decide which team should handle it.\n\n"
                "Choose exactly one of the following task IDs:\n"
                "- route_refund: The customer has a billing complaint, feels overcharged, "
                "or is questioning the value for money. Route here for potential refund processing.\n"
                "- route_safety: The customer reports a safety concern such as rough landings, "
                "turbulence, equipment warnings, or anything that could endanger passengers.\n"
                "- route_marketing: The customer left a very positive review praising "
                "the experience. Route here so marketing can use it as a testimonial.\n"
                "- route_general: The review contains mixed feedback about service quality, "
                "suggestions for improvement, or does not clearly fit the other categories."
            ),
        )
        def route_review(review_text: str) -> str:
            return review_text

        _formatted_context = format_context(review_data)
        _route_review = route_review(_formatted_context)

        # handle routing in the database by updating the review status and assigned team

        @task
        def extract_id(review_data):
            return review_data["review_id"]

        _id = extract_id(review_data)

        _route_refund = SQLExecuteQueryOperator(
            task_id="route_refund",
            conn_id=_DUCKDB_CONN_ID,
            sql="UPDATE trip_reviews SET status = 'routed', routed_to = 'refund' WHERE review_id = $id::INT",
            parameters={"id": _id}
        )

        _route_safety = SQLExecuteQueryOperator(
            task_id="route_safety",
            conn_id=_DUCKDB_CONN_ID,
            sql="UPDATE trip_reviews SET status = 'routed', routed_to = 'safety' WHERE review_id = $id::INT",
            parameters={"id": _id}
        )

        _route_marketing = SQLExecuteQueryOperator(
            task_id="route_marketing",
            conn_id=_DUCKDB_CONN_ID,
            sql="UPDATE trip_reviews SET status = 'routed', routed_to = 'marketing' WHERE review_id = $id::INT",
            parameters={"id": _id}
        )

        _route_general = SQLExecuteQueryOperator(
            task_id="route_general",
            conn_id=_DUCKDB_CONN_ID,
            sql="UPDATE trip_reviews SET status = 'routed', routed_to = 'general' WHERE review_id = $id::INT",
            parameters={"id": _id}
        )

        chain(
            _route_review, [
                _route_refund,
                _route_safety,
                _route_marketing,
                _route_general,
            ]
        )

    @task(outlets=[Asset("routed-reviews")], trigger_rule="none_failed_min_one_success")
    def routing_complete():
        print("Routing complete for all new reviews")

    _mission_control = MissionControlOperator(task_id="mission_control")

    chain(
        handle_review.expand(review_data=_review_list),
        routing_complete(),
        _mission_control
    )


route_reviews()
