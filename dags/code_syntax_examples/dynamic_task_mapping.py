"""
This Dag shows dynamic task mapping syntax for:

- .expand
- .expand_kwargs
- .map

as well as custom map indexing with map_index_template.

See also: https://www.astronomer.io/docs/learn/dynamic-tasks/
"""

from airflow.sdk import dag, task
from airflow.providers.standard.operators.bash import BashOperator


@dag(
    start_date=None,
    schedule=None,
    tags=["syntax_example"],
    default_args={"retries": 3},
)
def dynamic_task_mapping():

    # .expand with the TaskFlow API

    @task
    def upstream_task_1():
        return ["a", "b", "c"]

    @task(map_index_template="{{ my_custom_map_index }}")
    def mapped_task_1(num, letter):
        print(num)
        print(letter)

        from airflow.sdk import get_current_context

        context = get_current_context()
        context["my_custom_map_index"] = "Number: " + str(num) + " Letter: " + letter

    mapped_task_1.partial(num=42).expand(letter=upstream_task_1())

    # .expand with a traditional operator

    @task
    def upstream_task_2():
        return ["echo 1", "echo 2", "echo 3"]

    mapped_task_2 = BashOperator.partial(
        task_id="mapped_task_2",
        map_index_template="This one runs: {{ task.bash_command }}",
    ).expand(bash_command=upstream_task_2())

    # .expand_kwargs with the TaskFlow API

    @task
    def upstream_task_3():
        return [
            {"num": 1, "letter": "a"},
            {"num": 2, "letter": "b"},
            {"num": 3, "letter": "c"},
        ]

    @task(map_index_template="{{ my_custom_map_index }}")
    def mapped_task_3(num, letter):
        print(num)
        print(letter)

        from airflow.sdk import get_current_context

        context = get_current_context()
        context["my_custom_map_index"] = "Number: " + str(num) + " Letter: " + letter

    mapped_task_3.expand_kwargs(upstream_task_3())

    # .expand_kwargs with a traditional operator

    @task
    def upstream_task_4():
        return [
            {"bash_command": "echo $WORD", "env": {"WORD": "hello"}},
            {"bash_command": "echo `expr length $WORD`", "env": {"WORD": "tea"}},
            {"bash_command": "echo ${WORD//e/X}", "env": {"WORD": "goodbye"}},
        ]

    mapped_task_4 = BashOperator.partial(
        task_id="mapped_task_4",
        map_index_template="This one runs: {{ task.bash_command }}",
    ).expand_kwargs(upstream_task_4())

    # .map with the TaskFlow API

    @task
    def upstream_task_5():
        return [1, 2, 3]

    @task(map_index_template="{{ my_custom_map_index }}")
    def mapped_task_5(num):
        print(num)

        from airflow.sdk import get_current_context

        context = get_current_context()
        context["my_custom_map_index"] = "Number: " + str(num)

    num_times_100 = upstream_task_5().map(lambda num: num * 100)

    mapped_task_5.expand(num=num_times_100)

    # .map with a traditional operator

    def _multiply_and_bash(num):
        return "echo " + str(num * 1000)

    @task
    def upstream_task_6():
        return [1, 2, 3]

    num_times_10000_bash = upstream_task_6().map(_multiply_and_bash)

    mapped_task_6 = BashOperator.partial(
        task_id="mapped_task_6",
        map_index_template="This one runs: {{ task.bash_command }}",
    ).expand(bash_command=num_times_10000_bash)


dynamic_task_mapping()
