# Airflow MLOps Workshop

## Exercises

- [Exercise 0: Astro, Astro IDE, and the MLOps Dashboard](#exercise-0-astro-astro-ide-and-the-mlops-dashboard)
- [Exercise 1: Add a feature engineering Dag](#exercise-1-add-a-feature-engineering-dag)
- [Exercise 2: Classification: predict dessert choice based on enriched features](#exercise-2-classification-predict-dessert-choice-based-on-enriched-features)
- [Challenge: Mission control](#challenge-mission-control)
- [Extra 1: Regression: Hyperparameters and dynamic task mapping](#extra-1-regression-hyperparameters-and-dynamic-task-mapping)
- [Extra 2: Clustering: Find spending groups of customers](#extra-2-clustering-find-spending-groups-of-customers)

---

# Exercise 0: Astro, Astro IDE, and the MLOps Dashboard

## Set Up Astro IDE

This workshop does not require any local Airflow installation. Instead, all development takes place within Astro and the Astro IDE.

1. Create a [free trial of Astro](https://www.astronomer.io/lp/signup/?utm_source=conference&utm_medium=web&utm_campaign=devrel-workshop).

 - After creating an account, verifying your email, and logging in, choose _Personal_ in the first step.
 - Next, choose an _Organization_ and _Workspace_ name. These can be fictional names and you can change them later.
 - In the third step, click the small link at the bottom under the two boxes: _Or skip this and go to your workspace_.
 - You should now see the Astro platform UI.

2. Open the _Astro IDE_ from the left navigation and select _Connect Git project..._
3. Under _Select a Git provider for manual configuration_, select _GitHub_ and enter the following details:

 - **ACCOUNT**: `astronomer`
 - **REPOSITORY**: `devrel-public-workshops`
 - _Keep Astro Project Path empty_
 - **BRANCH**: `workshops/astrotrips/mlops-101`
 - **AUTHENTICATION TYPE**: `None (public repository)`
 - Click _Connect_. The IDE will import and open the project for you.

**You now have the Astro IDE with the project ready to go.**

> [!NOTE]
> You don't need to commit your changes. If you want to keep your code after the workshop, fork the repository first.

> [!TIP]
> The Astro IDE comes with an integrated AI assistant, optimized for workflow orchestration with Apache Airflow. Feel free to interact with it during this workshop to learn more about certain concepts.

## Set Up the Connection

This workshop relies on a DuckDB database. To ensure your test environments can connect to it, the next step is to create a workspace-wide connection.

> [!NOTE]
> The next two steps take place in the main Astro platform UI, not inside the Astro IDE. If you collapsed the sidebar, expand it to navigate.

1. In Astro, navigate to _Environment_ → _Connections_ and click the _+ Connection_ button.
2. In the dialog, search for and select _Generic_, then enter the following details:

 - **CONNECTION ID**: `duckdb_astrotrips`
 - **TYPE**: `duckdb`
 - **HOST**: `include/astrotrips.duckdb`
 - Set **AUTOMATICALLY LINK TO ALL DEPLOYMENTS** to _On_

3. Click _Create Connection_.

> [!TIP]
> Learn more about [Airflow connections](https://www.astronomer.io/docs/learn/connections).

## Set Up the Environment Variable

The MLOps Dashboard needs to know it's running in workshop mode so it can display results from your Dag runs based on XCom values, instead of relying on an external database.

1. In Astro, navigate to _Environment_ → _Environment Variables_ and click the _+ Environment Variable_ button.
2. Enter the following details:

 - **ENVIRONMENT VARIABLE KEY**: `MLOPS_WORKSHOP_MODE`
 - **ENVIRONMENT VARIABLE VALUE**: `true`
 - Set **AUTOMATICALLY LINK TO ALL DEPLOYMENTS** to _On_

3. Click _Create Environment Variable_.

> [!TIP]
> This is not necessary if you are using MotherDuck as your database.

## Start the test deployment and run the setup Dag

1. Navigate to the _Astro IDE_ and click _Start Test Deployment_ in the top right corner. The deployment takes 3-5 minutes to spin up.
2. Once the test deployment is ready, select _Open Airflow_, from the same dropdown menu.
3. In the Airflow UI, open the Dags view from the left menu you can see 5 Dags: `setup`, `feature_engineering`, `space_dessert_classification`, `astro_trip_catering_revenue_prediction`, and `food_preference_clustering`.
4. Under the **Browse** category, you can opent eh MLOps plugin.

**Once the Dag run completes successfully, your database and pre-seeded ML tracking data are ready.**

> [!IMPORTANT]
> Running this Dag resets and re-creates the database. If you encounter any issues in the following exercises, simply run this Dag again.

## Explore the project

Take a moment to explore the project structure in the Astro IDE. You will find several pre-built Dags in the `dags/` folder:

| Dag | Purpose |
|---|---|
| `setup` | Initialises the DuckDB database with sample data and pre-seeded ML tracking records. |
| `feature_engineering` | Creates derived features from raw booking and customer data. Currently incomplete -- you will finish it in Exercise 1. |
| `space_dessert_classification` | Predicts which of 5 desserts a customer will order using a `RandomForestClassifier`. |
| `astro_trip_catering_revenue_prediction` | Predicts daily catering revenue. Currently trains a single model -- you will add dynamic task mapping in Extra 1. |
| `food_preference_clustering` | Segments customers into culinary personas using KMeans clustering. |

Supporting code lives in `include/`:

- `include/mlops_tracking.py` -- a lightweight MLOps tracker (parameters, metrics, models, plots).
- `include/ml_queries.py` -- SQL queries for data extraction (base and enriched versions).
- `include/ml_plots.py` -- plotting functions for each ML paradigm.
- `include/feature_helpers.py` -- pure Python functions for feature engineering.

## The MLOps Dashboard

Before we start coding, take a look at the **MLOps Dashboard**. In the Airflow sidebar, click the _MLOps Dashboard_ link to open it.

This is a custom **Airflow plugin** built with FastAPI and React, one of the new extension points in Airflow 3. It provides a dashboard that tracks ML experiments, runs, models, and visualizations -- an Airflow-native alternative to MLflow.

The dashboard is already pre-seeded with one baseline run for each of the three ML use cases:

- **dessert_prediction** (classification): a baseline run with raw features only
- **daily_catering_revenue** (regression): a baseline run with raw features only
- **culinary_personas** (clustering): a baseline run with raw features only

Click through the experiments and inspect the baseline runs. Notice how each run tracks hyperparameters, metrics, and model artifacts. As you work through the exercises, your own runs will appear here alongside the baselines, showing how feature engineering and model tuning improve results.

> [!NOTE]
> Building plugins is not part of this workshop. The MLOps Dashboard is pre-built. If you're curious about the implementation, explore `plugins/airflow-mlops-plugin/` after the workshop.

> [!TIP]
> Learn more about [Airflow plugins](https://www.astronomer.io/docs/learn/using-airflow-plugins).

---

# Exercise 1: Add a feature engineering Dag

In this exercise, you will complete a feature engineering pipeline that transforms raw booking data into powerful predictive features. These features will dramatically improve every ML model in the workshop.

**What you will learn:**

- Writing `@task` functions and wiring task dependencies.
- How derived features encode relationships that raw columns cannot capture.
- Running and inspecting Dags in Airflow.

## Inspect the feature engineering Dag

Open `dags/feature_engineering.py` in the Astro IDE.

This Dag creates a `booking_meal_features` table with derived features: trip context (child ratios) and booking demographics (agent type, accommodation, destination meal plan, loyalty tier). But it's missing an important piece: **compound interaction features** that combine multiple signals into scores.

1. Open `include/feature_helpers.py` and find the `compound_scores` function. It creates features like `c_gemini_highorbit_allinc_biz` -- a score combining booking agent, accommodation type, destination meal plan, and travel type. These compound features encode relationships that individual columns can't capture.

## Add the compound scores task

1. In `dags/feature_engineering.py`, add a new `@task` that calls this helper. Place it after the `booking_demographics` task:

    ```python
    @task
    def compound_scores(trip_data, demo_data):
        import pandas as pd
        from include.feature_helpers import compound_scores as _fn

        return _fn(
            pd.DataFrame(trip_data),
            pd.DataFrame(demo_data),
        ).to_dict(orient="list")
    ```

2. Update the `save_booking_features` task to also accept and merge the compound data. Add `compound_data` as a third parameter:

    ```python
    @task
    def save_booking_features(trip_data, demo_data, compound_data):
    ```

    And include it in the list of DataFrames to merge:

    ```python
        dfs = [
            pd.DataFrame(d) for d in [trip_data, demo_data, compound_data]
        ]
    ```

3. Wire the new task into the Dag at the bottom. The compound scores depend on both `trip_context` and `booking_demographics`:

    ```python
    _extract_bookings = extract_bookings()
    _trip_context = trip_context(_extract_bookings)
    _booking_demographics = booking_demographics(_extract_bookings)
    _compound_scores = compound_scores(_trip_context, _booking_demographics)
    _save_booking_features = save_booking_features(
        _trip_context,
        _booking_demographics,
        _compound_scores,
    )
    ```

## Run the feature engineering Dag

1. Sync your changes and trigger the `feature_engineering` Dag.

> [!TIP]
> **Sync tips:**
> - Changes to Dag files sync fast. Changes to files in `include/` trigger an image rebuild, which takes longer.
> - While waiting for a sync, you can ask the Astro IDE AI questions about your Dag or about Airflow.

Once the Dag completes, the `booking_meal_features` table now contains trip context, booking demographics, **and** compound interaction scores. Every ML Dag in the project will automatically detect this table and use the enriched features.

> [!TIP]
> Learn more about the [TaskFlow API](https://www.astronomer.io/docs/learn/airflow-decorators) and [@task decorator](https://www.astronomer.io/docs/learn/airflow-decorators).

---

# Exercise 2: Classification: predict dessert choice based on enriched features

In this exercise, you will see how the features you just engineered improve a dessert prediction model, and then tune the model's hyperparameters for an additional boost.

**What you will learn:**

- How feature engineering dramatically improves ML model performance.
- How model hyperparameters affect accuracy.
- Comparing experiment runs in the MLOps Dashboard.

## Step 1: Run classification with enriched features

The `space_dessert_classification` Dag is already provided. It trains a `RandomForestClassifier` to predict which of 5 desserts a customer orders, based on booking context.

> [!TIP]
> Open `dags/space_dessert_classification.py` and read through the code. Notice the `extract → train → visualize → promote` pipeline. The `extract` task automatically detects whether engineered features are available and adjusts the query accordingly. Since you ran the `feature_engineering` Dag in Exercise 1, the enriched features are already available.

1. In the Airflow UI, trigger the `space_dessert_classification` Dag.
2. Once complete, check the `train` task logs. You should see something like:

    ```
    Classification metrics (enriched=True): {
      "accuracy": 0.55,
      "f1_weighted": 0.53,
      ...
    }
    ```

3. Open the **MLOps Dashboard** and click on the `dessert_prediction` experiment. Your new run appears alongside the pre-seeded baseline.

The pre-seeded baseline was trained with only 3 raw features and had an accuracy of ~25% -- barely better than random guessing among 5 desserts. Your run uses 22 enriched features including compound interaction scores and already reaches ~55%. But the model itself is still constrained (`max_depth=2`, allowing only very shallow decision trees). Can we do better?

## Step 2: Tune the model

Now that the model has strong features, let's give it more capacity to learn from them.

1. In `dags/space_dessert_classification.py`, find the `model_config` dict near the top of the `train` task and change `max_depth` from `2` to `10`:

    ```python
        model_config = {
            "n_estimators": 100,
            "max_depth": 10,
            "random_state": 42,
        }
    ```

2. Sync your changes and trigger the `space_dessert_classification` Dag again.
3. Check the `train` task logs:

    ```
    Classification metrics (enriched=True): {
      "accuracy": 0.74,
      "f1_weighted": 0.73,
      ...
    }
    ```

Another jump -- from **~55% to ~74%**. Deeper trees let the model capture subtler patterns in the compound features.

## Compare runs in the MLOps Dashboard

1. Open the **MLOps Dashboard** and navigate to the `dessert_prediction` experiment.
2. You should now see your runs alongside the pre-seeded baseline. Compare the metrics across all three: the raw-data baseline (~25%), enriched with `max_depth=2` (~55%), and enriched with `max_depth=10` (~74%).
3. Click on the final run and examine the visualization:
 - The **confusion matrix** shows a much cleaner diagonal (correct predictions).
 - The **feature importance chart** reveals that compound scores like `c_gemini_highorbit_allinc_biz` are among the strongest predictors.
 - The **dessert distribution** shows actual vs predicted counts are now much closer.

Notice that feature engineering (~25% → ~55%) gave a bigger lift than model tuning (~55% → ~74%). This is the fundamental lesson of ML engineering: **better features beat better algorithms**.

> [!NOTE]
> The compound scores (`c_gemini_highorbit_allinc_biz`, `c_chatgpt_gold_kids`, etc.) are powerful because they encode relationships between booking agent, accommodation type, and destination meal plan. The raw individual columns are not very predictive on their own, but the derived combinations are.

---

# Challenge: Mission control

It is time for a challenge. The workshop provides a custom `MissionControlOperator` that generates an interstellar clearance code based on your implementation. Only if the Dag has the correct task IDs and dependencies will the code be valid.

Within your `space_dessert_classification` Dag:

1. Import the `MissionControlOperator` from `include.mission_control`.
2. Create a task instance with `task_id="mission_control"`.
3. Add it as the **last step** in the Dag (downstream of `visualize`).
4. Sync your changes.
5. Trigger the `setup` Dag to reset the state, then run `feature_engineering`, then `space_dessert_classification`.
6. Check the `mission_control` task logs for your clearance code and share it!

> [!IMPORTANT]
> The first 3 that finish this challenge successfully receive a gift from Astronomer!

---

# Extra 1: Regression: Hyperparameters and dynamic task mapping

In this exercise, you will extend a revenue prediction pipeline to train multiple model architectures in parallel using **dynamic task mapping**, then compare them side-by-side in the MLOps Dashboard.

**What you will learn:**

- Using `.partial().expand()` for dynamic task mapping.
- Comparing multiple model architectures in a single Dag run.
- How model choice impacts performance.

## Step 1: Run the revenue prediction baseline

The `astro_trip_catering_revenue_prediction` Dag is already provided. It predicts catering revenue per booking party, but currently trains only a single `DecisionTreeRegressor` with `max_depth=2`.

1. Trigger the `astro_trip_catering_revenue_prediction` Dag.
2. Check the `train` task logs:

    ```
    DecisionTreeRegressor metrics (enriched=True): {
      "rmse": ...,
      "r2": 0.42,
      ...
    }
    ```

An R² of ~0.42 means the model explains less than half the variance. A shallow decision tree is too simple to capture the relationships in the data. Can a different model architecture do better? Instead of trying one at a time, let's compare four in parallel.

## Step 2: Define multiple model configs

1. In `dags/astro_trip_catering_revenue_prediction.py`, find the single default config near the top of the file. Replace it with a list of four model configurations:

    ```python
    _MODEL_CONFIGS = [
        {"model_type": "DecisionTreeRegressor", "max_depth": 2},
        {"model_type": "LinearRegression"},
        {"model_type": "Ridge", "alpha": 10.0},
        {"model_type": "GradientBoostingRegressor", "n_estimators": 200, "max_depth": 5},
    ]
    ```

## Step 3: Add dynamic task mapping

The `train` task already accepts a `config` parameter, so it's ready for expansion. Replace the single-config wiring at the bottom of the Dag function with dynamic task mapping:

```python
_extract = extract()
_train = train.partial(payload=_extract).expand(config=_MODEL_CONFIGS)
_visualize = visualize.expand(results=_train)
```

The `.partial()` method fixes the `payload` argument (same for all), while `.expand()` fans out over the list of configs. Airflow creates 4 parallel `train` task instances, one per model config, each followed by its own `visualize` task.

> [!NOTE]
> `.partial().expand()` is the pattern for dynamic task mapping when you have both shared and varying arguments. The number of task instances is determined at runtime from the list length.

## Step 4: Test and compare

1. Sync your changes.
2. Trigger the `astro_trip_catering_revenue_prediction` Dag.
3. In the Airflow UI, open the graph view. You should see `train` and `visualize` each fanned out into 4 mapped instances.
4. Once complete, check the logs for each `train` instance. You will see very different R² values:

 - **DecisionTreeRegressor** (max_depth=2): R² ~0.42 -- underfitting
 - **LinearRegression**: R² ~0.91 -- solid baseline
 - **Ridge** (alpha=10): R² ~0.90 -- slight regularization penalty
 - **GradientBoostingRegressor**: R² ~0.95 -- the clear winner

5. Open the **MLOps Dashboard**. Navigate to the `daily_catering_revenue` experiment. All 4 runs appear from the same Dag run, each tagged with its `model_type`. Sort by R² to instantly see which architecture wins.
6. In the **Model Registry**, notice that each model type is registered under its own name (e.g., `catering_revenue_gradient_boosting_regressor`), with the best model automatically promoted to production.

> [!TIP]
> Learn more about [dynamic task mapping](https://www.astronomer.io/docs/learn/dynamic-tasks).

---

---

# Extra 2: Clustering: Find spending groups of customers

In this exercise, you will run an unsupervised learning pipeline that segments customers into spending groups based on their dining behavior. Unlike classification and regression, clustering has no target variable -- the algorithm discovers natural groupings in the data.

**What you will learn:**

- Unsupervised learning with KMeans.
- Feature scaling with `StandardScaler` (critical for distance-based algorithms).
- Evaluating clusters with the silhouette score.
- How enriched features change cluster profiles.

## Run clustering

The `food_preference_clustering` Dag is already provided. Like the other ML Dags, it automatically detects whether the `booking_meal_features` table exists. Since you ran the `feature_engineering` Dag in Exercise 1, it will use 8 enriched features instead of 3 base features, and segment customers into 3 groups.

1. Trigger the `food_preference_clustering` Dag.
2. Once complete, open the **MLOps Dashboard** and navigate to the `culinary_personas` experiment.
3. Compare your enriched run with the pre-seeded baseline:
 - The baseline used 3 raw features (`total_orders`, `avg_price`, `total_spend`) to find basic spending tiers.
 - Your enriched run adds 5 features from the feature engineering table (`avg_child_ratio`, `avg_is_all_inclusive`, `avg_is_budget_plan`, `avg_is_high_orbit`, `avg_is_low_orbit`), producing more nuanced customer personas.
4. Click on your run and examine the visualization. The **persona profiles** chart shows how each cluster differs across the features, and the **scatter plot** reveals the separation between groups.

> [!TIP]
> Try changing `n_clusters` in the `train` task (e.g., from `3` to `4`) and re-running to see how the groups change. Compare the silhouette scores -- a higher score means better-separated clusters.

---

Congratulations! You've built and improved ML pipelines covering classification, regression, clustering, and feature engineering, all orchestrated by Apache Airflow.

The key takeaways:

- **Better features beat better algorithms** (Exercise 2: features alone took accuracy from ~25% to ~55%, then model tuning pushed it to ~74%).
- **Dynamic task mapping** lets you run models with different hyperparameters in parallel.
- **Airflow is not just for ETL.** With Airflow 3's plugin system it can orchestrate and track the entire ML lifecycle.

We recommend checking out the linked resources and continuing to extend your project during your Astro trial.
