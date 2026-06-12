import os
from pathlib import Path

from airflow.configuration import AIRFLOW_HOME
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sdk import Asset, chain, dag, task

_DUCKDB_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_SEED_EMAIL_DIR = Path(AIRFLOW_HOME) / "include" / "seed_emails"
_SEED_ML_DIR = Path(AIRFLOW_HOME) / "include" / "seed"


@dag(
    template_searchpath=f"{AIRFLOW_HOME}/include/sql",
    tags=["exercise 1"],
)
def setup():
    cleanup = SQLExecuteQueryOperator(
        task_id="cleanup", conn_id=_DUCKDB_CONN_ID, sql="cleanup.sql"
    )
    schema = SQLExecuteQueryOperator(
        task_id="schema", conn_id=_DUCKDB_CONN_ID, sql="schema.sql"
    )
    mlops_schema = SQLExecuteQueryOperator(
        task_id="mlops_schema", conn_id=_DUCKDB_CONN_ID, sql="mlops_schema.sql"
    )
    ai_schema = SQLExecuteQueryOperator(
        task_id="ai_schema", conn_id=_DUCKDB_CONN_ID, sql="aiops_schema.sql"
    )
    fixtures = SQLExecuteQueryOperator(
        task_id="fixtures", conn_id=_DUCKDB_CONN_ID, sql="fixtures.sql"
    )
    generate_data = SQLExecuteQueryOperator(
        task_id="generate_data", conn_id=_DUCKDB_CONN_ID, sql="generate_data.sql"
    )

    @task
    def clear_variables():
        from airflow.sdk import Variable

        from include.aimlops.persistence import VARIABLE_PREFIX

        mirrored_tables = [
            "planets", "routes", "customers", "promo_codes", "bookings", "payments",
            "menu_items", "meal_orders", "cosmarket_orders", "ai_features",
            "spend_features", "spend_labels",
            "email_threads", "email_messages", "decision_traces",
            "context_units", "context_graph",
        ]
        keys = ["mlops_plugin_data"] + [f"{VARIABLE_PREFIX}{t}" for t in mirrored_tables]
        for key in keys:
            # get-first so deleting an absent key does not log an exception
            if Variable.get(key, default=None) is not None:
                Variable.delete(key)

    @task
    def seed_emails():
        import yaml

        from include.aimlops.persistence import get_duckdb_conn, sync_table_to_variable

        messages = []
        for path in sorted(_SEED_EMAIL_DIR.glob("*.md")):
            _, frontmatter, body = path.read_text().split("---", 2)
            meta = yaml.safe_load(frontmatter)
            meta["body"] = body.strip()
            messages.append(meta)

        if not messages:
            return

        conn = get_duckdb_conn()
        threads = {}
        for m in sorted(messages, key=lambda x: (x["thread"], x["turn"])):
            if m["thread"] not in threads:
                threads[m["thread"]] = conn.execute(
                    "INSERT INTO email_threads (customer_id, subject) VALUES (?, ?) RETURNING thread_id",
                    [m["customer_id"], m["subject"]],
                ).fetchone()[0]
            conn.execute(
                "INSERT INTO email_messages "
                "(thread_id, turn, direction, sender, body, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    threads[m["thread"]],
                    m["turn"],
                    m["direction"],
                    m["sender"],
                    m["body"],
                    m.get("created_at"),
                ],
            )
        conn.close()
        sync_table_to_variable("email_threads")
        sync_table_to_variable("email_messages")

    @task
    def sync_source_tables():
        from include.aimlops.persistence import sync_table_to_variable

        for table in [
            "planets",
            "routes",
            "customers",
            "promo_codes",
            "bookings",
            "payments",
            "menu_items",
            "meal_orders",
            "cosmarket_orders",
        ]:
            sync_table_to_variable(table)

    @task(outlets=[Asset("plugin_sync")])
    def seed_ml_tracking():
        from include.aimlops.persistence import get_duckdb_conn

        conn = get_duckdb_conn()
        for table in ["ml_experiments", "ml_runs", "ml_models", "ml_plots"]:
            csv_path = _SEED_ML_DIR / f"{table}.csv"
            if not csv_path.exists():
                continue
            conn.execute(f"DELETE FROM {table}")
            conn.execute(
                f"INSERT INTO {table} SELECT * "
                f"FROM read_csv_auto('{csv_path}', max_line_size=50000000)"
            )
        conn.close()

    chain(
        clear_variables(),
        cleanup,
        schema,
        mlops_schema,
        ai_schema,
        fixtures,
        generate_data,
        seed_emails(),
        sync_source_tables(),
        seed_ml_tracking(),
    )


setup()
