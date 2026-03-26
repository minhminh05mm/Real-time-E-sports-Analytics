# Real-time E-sports Analytics Pipeline

Vietnamese version: `README.md`

A production-oriented Data Engineering project for League of Legends match analytics, combining:
- data collection from the Riot API
- Kafka-based event streaming
- real-time stream processing into ClickHouse
- XGBoost-based win probability prediction
- BI/dashboard consumption through Metabase

This repository is structured in a modular, portfolio-ready way so it is easier to maintain, test, extend, and present on GitHub.

## Project Goals

This project was built to demonstrate an end-to-end real-time analytics pipeline for e-sports data, with three main capabilities:

1. Data Engineering:
   collect League of Legends match data, simulate or publish real-time streams, process events, and store analytics-ready tables.
2. Machine Learning:
   build training features from historical match data and train an XGBoost model to estimate win probability over time.
3. Analytics / Visualization:
   store processed data in ClickHouse so Metabase can query it directly and power dashboards.

## Problem Statement

Given LoL timeline data, the system aims to answer questions such as:
- At minute `N`, what is Blue side's probability of winning?
- How do gold difference, XP difference, and objectives influence the prediction?
- Can we build dashboards by match, rank tier, patch, player pool, or champion composition?

## High-level Architecture

End-to-end data flow:

1. `data_ingestion`
   fetches players from a selected rank tier, retrieves match IDs from the Riot API, deduplicates by `match_id`, and publishes raw messages to Kafka.
2. `stream_processing`
   consumes Kafka messages, separates `match_detail` and `timeline`, transforms them into analytics-ready rows, runs AI inference, and writes into ClickHouse.
3. `machine_learning`
   reads processed data from ClickHouse, creates a training dataset, trains the XGBoost model, and stores the model artifact.
4. `Metabase`
   connects directly to ClickHouse for dashboarding and exploration.

Logical architecture:

```text
Riot API
   |
   v
data_ingestion
   |
   v
Kafka (esports_raw_events)
   |
   v
stream_processing
   |
   +--> ClickHouse: matches
   +--> ClickHouse: participants
   +--> ClickHouse: timeline_events
   +--> ClickHouse: match_stats_per_minute
   +--> ClickHouse: win_predictions
   |
   v
machine_learning
   |
   v
win_rate_model.pkl
   |
   v
stream_processing / inference
```

## Repository Structure

```text
esports_analytics/
├── infrastructure/
│   ├── docker-compose.yml
│   ├── apply_clickhouse_schema.py
│   └── clickhouse_init/
│       └── init_schema.sql
│
├── data_ingestion/
│   ├── requirements.txt
│   └── src/
│       ├── __init__.py
│       ├── config.py
│       ├── kafka_producer.py
│       ├── riot_api_client.py
│       └── simulator_job.py
│
├── machine_learning/
│   ├── requirements.txt
│   ├── data/
│   │   ├── champion_scaling.json
│   │   ├── raw_matches/
│   │   ├── raw_timelines/
│   │   └── training_dataset_advanced.csv
│   ├── models/
│   │   ├── win_rate_model.pkl
│   │   └── win_rate_model.legacy.json
│   └── src/
│       ├── __init__.py
│       ├── config.py
│       ├── feature_engineering.py
│       ├── historical_crawler.py
│       └── train_xgboost.py
│
├── stream_processing/
│   ├── requirements.txt
│   └── src/
│       ├── __init__.py
│       ├── ai_inference.py
│       ├── check_data.py
│       ├── clean_db.py
│       ├── clickhouse_client.py
│       ├── config.py
│       ├── consumer_job.py
│       └── data_transformer.py
│
├── data/
│   └── clickhouse_data/
├── metabase-plugins/
├── docker-compose.yml
├── .env
├── .gitignore
├── README.md
└── README_EN.md
```

## Module Responsibilities

### `infrastructure/`
Contains the infrastructure layer required by the pipeline:
- Kafka + Zookeeper
- Kafka UI
- ClickHouse
- Metabase
- ClickHouse schema DDL

### `data_ingestion/`
Responsible for publishing raw match data into Kafka.

Key files:
- `config.py`: ingestion configuration
- `riot_api_client.py`: Riot API wrapper
- `kafka_producer.py`: Kafka publishing utilities
- `simulator_job.py`: real-time ingestion entrypoint

Notes:
- ingestion fetches all players from the selected rank tier
- deduplication is handled by `match_id` across the entire run
- if player A and player B belong to the same match, that match is published only once

### `machine_learning/`
Responsible for offline crawling, feature generation, and model training.

Key files:
- `historical_crawler.py`: offline crawler by selected rank tier, storing raw JSON
- `feature_engineering.py`: creates the ML training dataset from ClickHouse
- `train_xgboost.py`: trains and stores the XGBoost model
- `config.py`: ML configuration

Notes:
- the offline crawler also deduplicates by `match_id`
- the main model artifact is stored at `machine_learning/models/win_rate_model.pkl`
- a legacy JSON model is still kept for backward compatibility

### `stream_processing/`
Responsible for real-time consumption, transformation, inference, and persistence.

Key files:
- `consumer_job.py`: main Kafka consumer
- `data_transformer.py`: converts raw payloads into insertable rows
- `ai_inference.py`: loads the model, calculates scaling, and predicts win rate
- `clickhouse_client.py`: ClickHouse connection and insert utilities
- `check_data.py`: quick validation script for processed data
- `clean_db.py`: truncates tables for testing

## How the Modules Connect

This is the core idea behind the repository:

- `data_ingestion` does not train the model
- `machine_learning` does not consume Kafka
- `stream_processing` does not crawl the Riot API

Each module has a dedicated responsibility, but they are connected through shared artifacts:

1. `data_ingestion` -> Kafka
   publishes raw messages into topic `esports_raw_events`
2. `stream_processing` -> ClickHouse
   consumes Kafka and writes analytics tables
3. `machine_learning` -> model artifact
   reads from ClickHouse, trains a model, saves `win_rate_model.pkl`
4. `stream_processing` -> model artifact
   loads the model from `machine_learning/models/` for real-time inference

## Main ClickHouse Tables

The current schema includes:
- `matches`: match-level metadata
- `participants`: final per-player match statistics
- `timeline_events`: important timeline events
- `match_stats_per_minute`: minute-level snapshots used for ML features
- `win_predictions`: minute-level win probability predictions

## How to Run the Project

### 1. Prepare the environment

Update `.env` with a valid Riot API key:

```env
RIOT_API_KEY=your_riot_api_key
```

### 2. Start infrastructure

From the repository root:

```bash
docker compose up -d
```

Check the services:

```bash
docker compose ps
docker compose logs -f
```

### 3. Apply ClickHouse schema

If ClickHouse is already running with an existing volume, apply the schema manually:

```bash
./venv/bin/python infrastructure/apply_clickhouse_schema.py
```

### 4. Run stream processing

Open terminal 1:

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m stream_processing.src.consumer_job
```

### 5. Run real-time ingestion

Open terminal 2:

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m data_ingestion.src.simulator_job --tier CHALLENGER --target-match-count 50 --matches-per-player 25
```

### 6. Validate processed data

```bash
./venv/bin/python -m stream_processing.src.check_data
```

### 7. Build features and train the model

```bash
./venv/bin/python -m machine_learning.src.feature_engineering
./venv/bin/python -m machine_learning.src.train_xgboost
```

## Offline Crawling

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m machine_learning.src.historical_crawler --tier CHALLENGER --target-match-count 50 --matches-per-player 25
```

Examples:

```bash
./venv/bin/python -m machine_learning.src.historical_crawler --tier MASTER --target-match-count 200 --matches-per-player 20
./venv/bin/python -m machine_learning.src.historical_crawler --tier GRANDMASTER --target-match-count 100 --matches-per-player 30
```

## Real-time Ingestion with the Same Workflow

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m data_ingestion.src.simulator_job --tier CHALLENGER --target-match-count 50 --matches-per-player 25
```

Examples:

```bash
./venv/bin/python -m data_ingestion.src.simulator_job --tier MASTER --target-match-count 100 --matches-per-player 20
./venv/bin/python -m data_ingestion.src.simulator_job --tier GRANDMASTER --target-match-count 100 --matches-per-player 30
```

## Deduplication Strategy

This is a key requirement of the project.

### Offline crawler
- deduplicates by `match_id`
- checks both `machine_learning/data/raw_matches/` and `raw_timelines/`
- if the same match is discovered from multiple players, it is stored only once

### Real-time ingestion
- deduplicates by `match_id` across the entire current publishing session
- if player A and player B are in the same game, that match is published only once

## Recommended Test Order

Recommended validation flow:

1. `docker compose up -d`
2. `./venv/bin/python infrastructure/apply_clickhouse_schema.py`
3. `./venv/bin/python -m stream_processing.src.consumer_job`
4. `./venv/bin/python -m data_ingestion.src.simulator_job --tier CHALLENGER --target-match-count 50 --matches-per-player 25`
5. `./venv/bin/python -m stream_processing.src.check_data`
6. `./venv/bin/python -m machine_learning.src.feature_engineering`
7. `./venv/bin/python -m machine_learning.src.train_xgboost`

## Usage Notes

- Riot API is rate limited, so larger crawls may take time.
- `RIOT_API_KEY` is temporary and can expire at any time.
- `feature_engineering.py` currently builds the dataset from ClickHouse, not directly from raw JSON.
- To train the model, data must first pass through `stream_processing` and be stored in ClickHouse.
- The system Python interpreter may not have all required packages installed, so `./venv/bin/python` is recommended.
- Generated artifacts inside `machine_learning/data/*.csv` and `machine_learning/models/*` usually should not be committed to GitHub unless intentionally included for demo purposes.

## Future Improvements

Some natural next steps for the project:
- add orchestration via Airflow or Dagster
- add unit tests and integration tests
- define stronger Kafka schemas per message type
- add a feature store or model registry
- build a complete Metabase dashboard for match analytics and win prediction
- extend beyond solo queue into pro-play datasets if an appropriate source is available

## Tech Stack

- Python
- Riot API
- Kafka
- ClickHouse
- Metabase
- XGBoost
- Docker Compose

## Author Note

This is a portfolio-style Data Engineering project designed around:
- clean module boundaries
- stream processing
- real-time analytics
- machine learning inference on e-sports match data
