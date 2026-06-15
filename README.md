![Workshop Airflow version](https://img.shields.io/badge/Airflow_version-3.2-blue?style=for-the-badge)

# Apache Airflow - AI Workshop

Welcome to the Apache Airflow AI workshop! You will build an AI-powered customer review intelligence pipeline using Airflow's LLM task decorators from the [common AI provider](https://airflow.apache.org/docs/apache-airflow-providers-common-ai/stable/) and Apache Airflow 3.

**What you will learn:**

- Using LLMs for structured data extraction with `@task.llm`.
- LLM-powered branching with `@task.llm_branch` inside dynamic task groups.
- Generating text embeddings and computing similarity with the `LlamaIndexEmbeddingOperator`.
- Building multi-step AI agents with tools using `@task.agent`.
- Human-in-the-loop patterns for reviewing and refining AI-generated content.
- Asset-aware scheduling for chaining Dags together.

> [!NOTE]
> tl;dr: jump directly to the [exercises](exercises.md).

## Prerequisites

- Access to the [Astro IDE](https://www.astronomer.io/product/ide/). _You don't need to set this up now. It is part of the exercise later._
- An **OpenAI API key** (or any OpenAI-compatible provider). _Required for LLM-based exercises._

## Scenario: AstroTrips

AstroTrips is a fictional travel company specializing in interplanetary trips. Customers can book journeys to destinations like the Moon, Mars, or Europa, complete with launch windows and passenger manifests.

As AstroTrips grows, customer reviews are piling up. The support team is overwhelmed and needs automation. Your job is to build an AI-powered pipeline that analyzes reviews, routes them to the right team, finds similar complaints, drafts personalized responses, and lets a human approve or reject each one, all orchestrated with Airflow.

Throughout this workshop, you will work as an AI engineer at AstroTrips. Your task is to build and extend Airflow Dags that process customer reviews using LLMs, embeddings, and agents, while focusing on best practices rather than domain complexity.

![AstroTrips](doc/astrotrips-banner.png)

The underlying database used for AstroTrips is DuckDB, and it comes with a set of base tables and might be extended with additional tables depending on the workshop.

![AstroTrips](doc/astrotrips-base-tables.png)

## Using MotherDuck (optional)

> [!CAUTION]
> This optional step can be skipped for regular workshop participation. It is intended for advanced exploration after the workshop.

This project is configured to use DuckDB with a local database file stored in `include/astrotrips.duckdb`. While this setup is sufficient for this scenario, it has specific limitations:

- **No concurrent access:** The database cannot be written to by multiple concurrent processes.
- **No distributed processing:** Because the database is a local file, all Airflow tasks must run on the same node to access it.

To run this code in a distributed setup or enable concurrent access, you can easily switch to [MotherDuck](https://motherduck.com), a managed cloud service for DuckDB.

1. Sign up for a free account at [motherduck.com](https://motherduck.com).
2. Once logged in, create a new attached database named `astrotrips`.
3. Go to **Settings** -> **Integrations** -> **Access Tokens**.
4. Click **Create token**, keep the default settings, and select **Create token** in the popup window.
5. Copy the generated token and update the connection details in your `.env` file as follows:

```
AIRFLOW_CONN_DUCKDB_ASTROTRIPS='{
    "conn_type":"duckdb",
    "host":"md:astrotrips?motherduck_token=<YOUR_MOTHERDUCK_TOKEN>"
}'
```

> **Note:** Ensure you also update any other references to the local DuckDB file path, such as `include/connections.yaml` if applicable.

## Using Astro CLI (optional)

> [!CAUTION]
> This optional step can be skipped for regular workshop participation. It is intended for advanced exploration after the workshop.

Workshops can also be worked on using the Astro CLI and a local, containerized Airflow setup. Copy `.env.dist` to `.env` and add your OpenAI API key to the `AIRFLOW_CONN_PYDANTICAI_DEFAULT` connection, then adjust the configuration values if needed. You can start the project with `astro dev start`. However, these workshops are primarily designed for use with the Astro IDE.

## OpenAI API key

This workshop uses OpenAI-compatible models for LLM tasks and embeddings. You will need an API key from [OpenAI](https://platform.openai.com/api-keys) or any compatible provider. The key is stored in an Airflow connection during the setup exercise, together with the model to use, so no credentials or model names appear in your Dag code.

## Get started

Please proceed by following the exercises in [exercises.md](exercises.md).
