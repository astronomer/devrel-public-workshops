from pendulum import duration
from airflow.configuration import AIRFLOW_HOME
from airflow.providers.common.ai.operators.llamaindex_embedding import (
    LlamaIndexEmbeddingOperator,
)
from airflow.providers.common.sql.operators.sql import (
    SQLExecuteQueryOperator,
    SQLInsertRowsOperator,
)
from airflow.sdk import Asset, chain, dag, task

_DUCKDB_CONN_ID = "duckdb_astrotrips"


@dag(
    schedule=Asset("routed-reviews"),
    tags=["astrotrips", "ai", "reviews", "embeddings"],
    template_searchpath=f"{AIRFLOW_HOME}/include/sql",
    default_args={"retries": 3, "retry_delay": duration(seconds=10)},
)
def embed_reviews():

    _reviews = SQLExecuteQueryOperator(
        task_id="get_reviews",
        conn_id=_DUCKDB_CONN_ID,
        sql="SELECT review_id, review_text FROM trip_reviews WHERE status != 'pending'",
    )

    @task
    def format_documents(query_result):
        return [
            {"text": row[1], "metadata": {"review_id": row[0]}}
            for row in query_result
        ]

    _documents = format_documents(_reviews.output)

    _embeddings = LlamaIndexEmbeddingOperator(
        task_id="create_embeddings",
        documents=_documents,
        llm_conn_id="pydanticai_default",
        embed_model="text-embedding-3-small",
        persist_dir=f"{AIRFLOW_HOME}/include/review_index",
    )

    @task
    def prepare_rows(result):
        """Load the persisted index and map each vector back to its review."""
        from llama_index.core import StorageContext

        ctx = StorageContext.from_defaults(persist_dir=result["persist_dir"])
        return [
            (ctx.docstore.get_node(node_id).metadata["review_id"], vector)
            for node_id, vector in ctx.vector_store.data.embedding_dict.items()
        ]

    _prepared_rows = prepare_rows(_embeddings.output)

    _save_embeddings = SQLInsertRowsOperator(
        task_id="save_embeddings",
        conn_id=_DUCKDB_CONN_ID,
        table_name="review_embeddings",
        rows=_prepared_rows,
        columns=["review_id", "embedding"],
        preoperator="DELETE FROM review_embeddings",
    )

    _get_embedded_reviews = SQLExecuteQueryOperator(
        task_id="get_embedded_reviews",
        conn_id=_DUCKDB_CONN_ID,
        sql=(
            "SELECT re.review_id, tr.review_text, tr.category, re.embedding "
            "FROM review_embeddings re "
            "JOIN trip_reviews tr ON tr.review_id = re.review_id "
            "ORDER BY re.review_id"
        ),
    )

    @task(outlets=[Asset("embedded-reviews")])
    def compute_similarity(rows):
        """Compute pairwise cosine similarity and print clusters."""
        if not rows:
            print("No embeddings found.")
            return

        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        print("::group::Top similar review pairs")
        pairs = []
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                sim = cosine_sim(rows[i][3], rows[j][3])
                pairs.append((rows[i][0], rows[j][0], sim, rows[i][2], rows[j][2]))

        pairs.sort(key=lambda x: x[2], reverse=True)

        for r1_id, r2_id, sim, cat1, cat2 in pairs[:10]:
            marker = " <-- same cluster" if cat1 == cat2 else ""
            print(f"  Review #{r1_id} ({cat1}) <-> Review #{r2_id} ({cat2}): {sim:.3f}{marker}")
        print("::endgroup::")

    chain(_prepared_rows, _save_embeddings, _get_embedded_reviews)
    compute_similarity(_get_embedded_reviews.output)


embed_reviews()
