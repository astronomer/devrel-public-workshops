# DevRel public workshops

Workshops for public events, managed by the DevRel team

This repo contains public Apache Airflow and Astro workshops maintained by Astronomer's DevRel team. To find code for your workshop, choose the appropriate branch.

## AstroTrips workshop series

All workshops share the same scenario: **AstroTrips**, a fictional interplanetary travel company. You play the role of a data engineer working with real Airflow patterns, DuckDB, and the Astro IDEm  no local setup required.

### ELT/ETL workshop

**Branch:** [`workshops/astrotrips/etl`](https://github.com/astronomer/devrel-public-workshops/tree/workshops/astrotrips/etl)

Build and orchestrate data pipelines for AstroTrips reporting.

| | |
|---|---|
| **Level** | Beginner to intermediate |
| **Prerequisites** | Astro IDE access |
| **API key** | Not required |

What you will learn:
- Authoring parameterized SQL pipelines with the TaskFlow API and classic operators
- Asset-aware scheduling for data-driven Dag dependencies
- Dynamic task mapping for scalable data processing
- Data quality checks as part of a pipeline
- Human-in-the-loop patterns for manual intervention

### AI workshop

**Branch:** [`workshops/astrotrips/ai`](https://github.com/astronomer/devrel-public-workshops/tree/workshops/astrotrips/ai)

Build an AI-powered customer review intelligence pipeline using Airflow's LLM task decorators.

| | |
|---|---|
| **Level** | Intermediate |
| **Prerequisites** | Astro IDE access |
| **API key** | OpenAI API key (or compatible) |

What you will learn:
- Structured data extraction from text and images with `@task.llm`
- LLM-powered branching with `@task.llm_branch` inside dynamic task groups
- Generating text embeddings and computing similarity with `@task.embed`
- Building multi-step AI agents with tools using `@task.agent`
- Human-in-the-loop review and approval for AI-generated content
- Asset-aware scheduling for chaining Dags together

### MLOps 101 workshop

**Branch:** [`workshops/astrotrips/mlops-101`](https://github.com/astronomer/devrel-public-workshops/tree/workshops/astrotrips/mlops-101)

Build ML pipelines for all three fundamental paradigms: classification, regression, and clustering, with experiment tracking in an Airflow plugin.

| | |
|---|---|
| **Level** | Intermediate |
| **Prerequisites** | Astro IDE access |
| **API key** | Not required |

What you will learn:
- Feature engineering orchestrated with Airflow
- Asset-based scheduling to chain Dag runs on successful completion
- Dynamic task mapping for hyperparameter tuning across multiple model configurations
- Tracking ML experiments directly in the Airflow UI via a custom plugin

## Running a workshop

All workshops are designed for the **Astro IDE** (no local setup needed). Each workshop README contains full setup instructions, including how to connect the repository in the IDE.

## Repository structure

```
main                             This overview
workshops/astrotrips/_base       Shared components (schema, fixtures, utilities)
workshops/astrotrips/etl         ELT/ETL workshop
workshops/astrotrips/ai          AI workshop
workshops/astrotrips/mlops-101   MLOps 101 workshop
```
