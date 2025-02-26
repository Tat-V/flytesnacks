"""
Data Cleaning Imperative Workflow
---------------------------------------

This workflow makes use of the feature engineering tasks defined in the other file. 
We'll build an SQLite3 data cleaning pipeline utilizing these tasks.

.. tip::

    You can simply import the tasks, but we use references because we are referring to the existing code.
"""

# %%
# Let's import the libraries.
import pandas as pd
from flytekit import CronSchedule, LaunchPlan, Workflow, kwtypes, reference_task
from flytekit.extras.sqlite3.task import SQLite3Config, SQLite3Task
from flytekit.types.schema import FlyteSchema


# %%
# Next, we define the reference tasks. A :py:func:`flytekit.reference_task` references the Flyte tasks that have already been defined, serialized, and registered.
# The primary advantage of using a reference task is to reduce the redundancy; we needn't define the task(s) again if we have multiple datasets that need to be feature-engineered.
#
# .. note::
#
#    The Macro ``{{ registration.version }}`` is filled during the registration time by `flytectl register`. This is usually not required for using reference tasks, you should
#    ideally bind to a specific version of the entity - task / launchplan. But, in the case of this example, we are registering both the actual task ``sqlite_datacleaning.tasks.mean_median_imputer`` and
#    and the workflow that references it. Thus we want it to actually be updated to the version of a specific release of FlyteSnacks. This is why we use the ``{{ registration.version }}`` macro.
#    A typical example of reference task would look more like
#
#    .. code-block:: python
#
#       @reference_task(
#            project="flytesnacks",
#            domain="development",
#            name="sqlite_datacleaning.tasks.mean_median_imputer",
#            version="d06cebcfbeabc02b545eefa13a01c6ca992940c8", # If using GIT for versioning OR 0.16.0 is using semver
#        )
#        def mean_median_imputer()
#            ...
#
@reference_task(
    project="flytesnacks",
    domain="development",
    name="sqlite_datacleaning.datacleaning_tasks.mean_median_imputer",
    version="{{ registration.version }}",
)
def mean_median_imputer(
    dataframe: pd.DataFrame,
    imputation_method: str,
) -> pd.DataFrame:
    ...


@reference_task(
    project="flytesnacks",
    domain="development",
    name="sqlite_datacleaning.datacleaning_tasks.univariate_selection",
    version="{{ registration.version }}",
)
def univariate_selection(
    dataframe: pd.DataFrame,
    split_mask: int,
    num_features: int,
) -> pd.DataFrame:
    ...


# %%
# .. note::
#
#   The ``version`` varies depending on the version assigned during the task registration process.

# %%
# Finally, we define an imperative workflow that accepts the two reference tasks we've prototyped above. The data flow can be interpreted as follows:
#
# #. An SQLite3 task is defined to fetch the data batch
# #. The output (FlyteSchema) is passed to the ``mean_median_imputer`` task
# #. The output produced by ``mean_median_imputer`` is given to the ``univariate_selection`` task
# #. The dataframe generated by ``univariate_selection`` is the workflow output
wb = Workflow(name="sqlite_datacleaning.workflow.fe_wf")
wb.add_workflow_input("imputation_method", str)
wb.add_workflow_input("limit", int)
wf_in = wb.add_workflow_input("num_features", int)

sql_task = SQLite3Task(
    name="sqlite3.horse_colic",
    query_template="select * from data limit {{ .inputs.limit }}",
    inputs=kwtypes(limit=int),
    output_schema_type=FlyteSchema,
    task_config=SQLite3Config(
        uri="https://cdn.discordapp.com/attachments/545481172399030272/852144760273502248/horse_colic.db.zip",
        compressed=True,
    ),
)

node_t1 = wb.add_entity(
    sql_task,
    limit=wb.inputs["limit"],
)
node_t2 = wb.add_entity(
    mean_median_imputer,
    dataframe=node_t1.outputs["results"],
    imputation_method=wb.inputs["imputation_method"],
)
node_t3 = wb.add_entity(
    univariate_selection,
    dataframe=node_t2.outputs["o0"],
    split_mask=23,
    num_features=wf_in,
)
wb.add_workflow_output(
    "output_from_t3", node_t3.outputs["o0"], python_type=pd.DataFrame
)

DEFAULT_INPUTS = {"limit": 100, "imputation_method": "mean", "num_features": 15}

sqlite_dataclean_lp = LaunchPlan.get_or_create(
    workflow=wb,
    name="sqlite_datacleaning",
    default_inputs=DEFAULT_INPUTS,
    schedule=CronSchedule("0 10 * * ? *"),
)

if __name__ == "__main__":
    print(
        wb(
            limit=100,
            imputation_method="mean",
            num_features=15,
        )
    )
