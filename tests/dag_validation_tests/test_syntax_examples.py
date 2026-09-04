"""
Import test for the code syntax examples.

The examples in `dags/code_syntax_examples` are a reference library, not part of any
exercise, so `dags/.airflowignore` keeps them out of the Airflow UI and out of the Dag
processor. That also keeps them out of the regular Dag validation tests, so this test
loads that folder explicitly and makes sure every example still imports.

Delete the entry in `dags/.airflowignore` if you want to run the examples in Airflow.
"""

import logging
from contextlib import contextmanager
from pathlib import Path

import pytest
from airflow.models import DagBag

_EXAMPLES_DIR = Path(__file__).parents[2] / "dags" / "code_syntax_examples"


@contextmanager
def suppress_logging(namespace):
    logger = logging.getLogger(namespace)
    old_value = logger.disabled
    logger.disabled = True
    try:
        yield
    finally:
        logger.disabled = old_value


def _example_dag_bag() -> DagBag:
    with suppress_logging("airflow"):
        # Pointing DagBag straight at the folder bypasses the .airflowignore in dags/,
        # which only applies from the directory the search starts in.
        return DagBag(dag_folder=str(_EXAMPLES_DIR), include_examples=False)


def _example_files() -> list[str]:
    return sorted(p.name for p in _EXAMPLES_DIR.glob("*.py"))


def test_examples_folder_is_not_empty():
    assert _example_files(), f"No syntax examples found in {_EXAMPLES_DIR}"


@pytest.mark.parametrize("filename", _example_files())
def test_example_imports(filename):
    """Every syntax example must import without errors."""
    errors = {Path(k).name: v for k, v in _example_dag_bag().import_errors.items()}

    assert filename not in errors, f"{filename} failed to import with message \n {errors[filename]}"


def test_every_example_file_defines_a_dag():
    """A file that silently stops registering a Dag is broken, even if it imports."""
    dag_bag = _example_dag_bag()
    files_with_dags = {Path(dag.fileloc).name for dag in dag_bag.dags.values()}

    missing = sorted(set(_example_files()) - files_with_dags)

    assert not missing, f"These example files define no Dag: {missing}"
