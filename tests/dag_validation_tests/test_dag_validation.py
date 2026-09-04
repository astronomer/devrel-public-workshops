"""
Example Dag validation tests.

These tests check that every Dag in the project imports cleanly and sets task retries.
This is an example pytest suite and may not fit the context of your own Dags. Feel free to
add and remove tests.

Run them with `astro dev pytest` or from the Test tab in the Astro IDE.
"""

import logging
import os
from contextlib import contextmanager

import pytest
from airflow.models import DagBag


@contextmanager
def suppress_logging(namespace):
    logger = logging.getLogger(namespace)
    old_value = logger.disabled
    logger.disabled = True
    try:
        yield
    finally:
        logger.disabled = old_value


def get_import_errors():
    """
    Generate a tuple for import errors in the Dag bag.
    """
    with suppress_logging("airflow"):
        dag_bag = DagBag(include_examples=False)

        def strip_path_prefix(path):
            return os.path.relpath(path, os.environ.get("AIRFLOW_HOME"))

        # prepend "(None,None)" to ensure that a test object is always created even if it's a no op.
        return [(None, None)] + [
            (strip_path_prefix(k), v.strip()) for k, v in dag_bag.import_errors.items()
        ]


def get_dags():
    """
    Generate a tuple of dag_id, <DAG objects> in the DagBag.
    """
    with suppress_logging("airflow"):
        dag_bag = DagBag(include_examples=False)

    def strip_path_prefix(path):
        return os.path.relpath(path, os.environ.get("AIRFLOW_HOME"))

    return [(k, v, strip_path_prefix(v.fileloc)) for k, v in dag_bag.dags.items()]


@pytest.mark.parametrize(
    "rel_path,rv", get_import_errors(), ids=[x[0] for x in get_import_errors()]
)
def test_file_imports(rel_path, rv):
    """Test for import errors on a file"""
    if rel_path and rv:
        raise Exception(f"{rel_path} failed to import with message \n {rv}")


# APPROVED_TAGS = {}


# @pytest.mark.parametrize(
#     "dag_id,dag,fileloc", get_dags(), ids=[x[2] for x in get_dags()]
# )
# def test_dag_tags(dag_id, dag, fileloc):
#     """
#     test if a Dag is tagged and if those tags are in the approved list
#     """
#     assert dag.tags, f"{dag_id} in {fileloc} has no tags"
#     if APPROVED_TAGS:
#         assert not set(dag.tags) - APPROVED_TAGS


# @pytest.mark.parametrize(
#     "dag_id,dag, fileloc", get_dags(), ids=[x[2] for x in get_dags()]
# )
# def test_dag_has_catchup_false(dag_id, dag, fileloc):
#     """
#     test if a Dag has catchup set to False
#     """
#     assert (
#         dag.catchup == False
#     ), f"{dag_id} in {fileloc} must have catchup set to False."


# ALLOWED_OPERATORS = [
#     "_PythonDecoratedOperator",  # this allows the @task decorator
#     "MyBasicMathOperator",
#     "SQLExecuteQueryOperator",
# ]


# @pytest.mark.parametrize(
#     "dag_id, dag, fileloc", get_dags(), ids=[x[0] for x in get_dags()]
# )
# def test_dag_uses_allowed_operators_only(dag_id, dag, fileloc):
#     """
#     Test if a Dag uses only allowed operators.
#     """
#     for task in dag.tasks:
#         assert any(
#             task.task_type == allowed_op for allowed_op in ALLOWED_OPERATORS
#         ), f"{task.task_id} in {dag_id} ({fileloc}) uses {task.task_type}, which is not in the list of allowed operators."


@pytest.mark.parametrize(
    "dag_id,dag, fileloc", get_dags(), ids=[x[2] for x in get_dags()]
)
def test_dag_retries(dag_id, dag, fileloc):
    """
    test if a Dag has retries set
    """
    num_retries = dag.default_args.get("retries", 0)

    assert (
        num_retries >= 2
    ), f"{dag_id} in {fileloc} must have task retries >= 2 it currently has {num_retries}."
