from pathlib import Path

from airflow.configuration import AIRFLOW_HOME
from airflow.sdk import dag, task

from include.aimlops.assets import INBOUND_PROSPECT_EMAIL

_RIKER_EMAIL = Path(AIRFLOW_HOME) / "include" / "seed_emails" / "riker.md"


@dag(schedule=None, tags=["Bonus exercise 2"], doc_md=__doc__)
def send_riker_email():

    @task(outlets=[INBOUND_PROSPECT_EMAIL])
    def deliver() -> None:
        import yaml

        from include.aimlops.persistence import get_duckdb_conn, sync_table_to_variable

        _, frontmatter, body = _RIKER_EMAIL.read_text().split("---", 2)
        email = yaml.safe_load(frontmatter)

        conn = get_duckdb_conn()
        thread_id = conn.execute(
            "INSERT INTO email_threads (customer_id, subject) VALUES (?, ?) RETURNING thread_id",
            [email["customer_id"], email["subject"]],
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO email_messages (thread_id, turn, direction, sender, body) "
            "VALUES (?, 1, 'inbound', ?, ?)",
            [thread_id, email["sender"], body.strip()],
        )
        conn.close()
        sync_table_to_variable("email_threads")
        sync_table_to_variable("email_messages")

    deliver()


send_riker_email()
