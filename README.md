> [!WARNING]
> **This repository is no longer actively maintained.**
>
> The workshop has moved to the [`workshops/astrotrips/dag-writing`](https://github.com/astronomer/devrel-public-workshops/tree/workshops/astrotrips/dag-writing) branch of [`astronomer/devrel-public-workshops`](https://github.com/astronomer/devrel-public-workshops), where it is kept up to date alongside the other AstroTrips workshops. Please use that branch instead.

![Workshop Airflow version](https://img.shields.io/badge/Airflow_version-3.3-blue?style=for-the-badge)

# Dag writing best practices

Welcome! 🚀

This is a workshop about Dag writing best practices. It is designed to help you learn about Airflow best practices by working through a series of exercises.

**What you will learn:**

- Connecting Dags with asset-aware scheduling, including conditional expressions and `AssetOrTimeSchedule`.
- Adapting a Dag to its data at runtime with dynamic task mapping.
- Using Dag parameters to make retries, ownership and failure handling explicit.
- Spotting and removing top-level Dag code, one of the most common Airflow anti-patterns.
- Writing a Dag validation test that stops the next Dag from regressing your standards.

> [!NOTE]
> tl;dr: jump directly to the [exercises](exercises.md).

## Prerequisites

- Access to the [Astro IDE](https://www.astronomer.io/product/ide/). _You don't need to set this up now. It is part of the exercise later._

No API keys and no external services are required. Every Dag in this repository runs against a built-in, mocked API.

## Scenario: AstroTrips

AstroTrips is a fictional travel company specializing in interplanetary trips. Customers can book journeys to destinations like the Moon, Mars, or Europa, complete with launch windows and passenger manifests.

You are joining the AstroTrips **flight operations** team. Before any ship leaves the pad, mission control needs a launch readiness report: what the conditions look like at each destination, what they looked like on the day the launch window opens, and whether the transfer trajectory is taking a radiation hit.

The Dags that produce that report already exist, but they work by accident. They only ever look at a single planet, they are not connected to each other, and the report Dag has no owner, no retries and no cap on consecutive failures. A fourth Dag, unrelated to the report, makes an expensive call every time it is parsed. Your job is to fix them.

![AstroTrips](doc/astrotrips-banner.png)

## Using Astro CLI (optional)

> [!CAUTION]
> This optional step can be skipped for regular workshop participation. It is intended for advanced exploration after the workshop.

Workshops can also be worked on using the Astro CLI and a local Airflow setup. You can start the project with `astro dev start`. However, these workshops are primarily designed for use with the Astro IDE.

## Get started

Please proceed by following the exercises in [exercises.md](exercises.md).
