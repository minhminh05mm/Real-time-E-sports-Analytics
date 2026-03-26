# Real-time E-sports Analytics Pipeline

English version: `README.md`

Pipeline Data Engineering cho bài toán phân tích trận đấu League of Legends theo hướng real-time, kết hợp:
- thu thập dữ liệu từ Riot API
- phát sự kiện qua Kafka
- xử lý stream và ghi vào ClickHouse
- huấn luyện mô hình XGBoost để dự đoán win rate
- phục vụ dashboard/BI qua Metabase

Dự án được tổ chức theo kiểu production-oriented module để dễ mở rộng, test, và đưa lên GitHub/portfolio.

## Mục tiêu dự án

Mục tiêu chính của dự án là xây dựng một hệ thống end-to-end cho bài toán Real-time E-sports Analytics với 3 lớp năng lực:

1. Data Engineering:
   crawl dữ liệu trận đấu League of Legends, mô phỏng hoặc phát luồng dữ liệu thời gian thực, xử lý stream, và lưu trữ analytics-ready data.
2. Machine Learning:
   tạo feature dataset từ dữ liệu lịch sử, huấn luyện mô hình dự đoán xác suất thắng theo diễn biến trận đấu.
3. Analytics / Visualization:
   đưa dữ liệu vào ClickHouse để Metabase có thể query trực tiếp và dựng dashboard theo thời gian thực.

## Bài toán mà dự án giải quyết

Với dữ liệu timeline của một trận LoL, hệ thống cố gắng trả lời các câu hỏi như:
- Ở phút thứ `N`, đội xanh đang có bao nhiêu phần trăm cơ hội thắng?
- Chênh lệch vàng, XP, objective ảnh hưởng thế nào đến dự đoán?
- Có thể xây dashboard theo trận, theo rank, theo patch, theo champion pool hay không?

## Kiến trúc tổng thể

Luồng dữ liệu tổng thể:

1. `data_ingestion`
   lấy danh sách người chơi theo bậc rank được chọn, lấy match IDs từ Riot API, chống trùng theo `match_id`, rồi publish dữ liệu raw lên Kafka.
2. `stream_processing`
   consume dữ liệu từ Kafka, tách `match_detail` và `timeline`, làm phẳng dữ liệu, suy luận AI, rồi ghi vào ClickHouse.
3. `machine_learning`
   đọc dữ liệu đã chuẩn hóa từ ClickHouse, tạo training dataset, huấn luyện XGBoost, lưu model.
4. `Metabase`
   kết nối trực tiếp vào ClickHouse để dựng dashboard.

Kiến trúc logic:

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

## Cấu trúc thư mục

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
└── README.md
```

## Vai trò của từng module

### `infrastructure/`
Chứa phần hạ tầng cần cho pipeline:
- Kafka + Zookeeper
- Kafka UI
- ClickHouse
- Metabase
- DDL schema cho ClickHouse

### `data_ingestion/`
Chịu trách nhiệm phát dữ liệu raw lên Kafka.

Các thành phần chính:
- `config.py`: cấu hình ingestion
- `riot_api_client.py`: wrapper cho Riot API
- `kafka_producer.py`: publish message vào Kafka
- `simulator_job.py`: entrypoint chạy ingestion real-time

Lưu ý:
- ingestion hiện lấy toàn bộ người chơi theo `tier` được chọn mỗi lần chạy
- có chống trùng `match_id` trong toàn bộ lượt chạy
- nếu người A và B cùng nằm trong một trận, trận đó chỉ được publish 1 lần

### `machine_learning/`
Chịu trách nhiệm crawl lịch sử, tạo feature dataset, và huấn luyện model.

Các thành phần chính:
- `historical_crawler.py`: crawl offline theo rank tier, lưu raw JSON
- `feature_engineering.py`: đọc dữ liệu từ ClickHouse và tạo dataset train
- `train_xgboost.py`: train model XGBoost và lưu artifact
- `config.py`: cấu hình ML

Lưu ý:
- offline crawler cũng chống trùng `match_id`
- model chính hiện lưu ở `machine_learning/models/win_rate_model.pkl`
- model legacy JSON vẫn được giữ để tương thích ngược

### `stream_processing/`
Chịu trách nhiệm xử lý dữ liệu real-time và suy luận.

Các thành phần chính:
- `consumer_job.py`: consumer Kafka chính
- `data_transformer.py`: transform raw payload thành row insertable
- `ai_inference.py`: load model, tính scaling, predict win rate
- `clickhouse_client.py`: kết nối/ghi ClickHouse
- `check_data.py`: kiểm tra nhanh dữ liệu đã được ghi hay chưa
- `clean_db.py`: truncate bảng phục vụ test

## Liên kết giữa các thư mục

Đây là điểm quan trọng nhất để hiểu repo:

- `data_ingestion` không train model
- `machine_learning` không consume Kafka
- `stream_processing` không crawl Riot API

Mỗi module có trách nhiệm riêng nhưng liên kết với nhau qua artifact chung:

1. `data_ingestion` -> Kafka
   publish raw messages vào topic `esports_raw_events`
2. `stream_processing` -> ClickHouse
   consume Kafka và ghi thành bảng phân tích
3. `machine_learning` -> model artifact
   đọc từ ClickHouse, train model, lưu `win_rate_model.pkl`
4. `stream_processing` -> model artifact
   load model từ `machine_learning/models/` để infer real-time

## Các bảng chính trong ClickHouse

Schema hiện tại gồm:
- `matches`: thông tin chung của trận đấu
- `participants`: thống kê cuối trận theo người chơi
- `timeline_events`: các event quan trọng trong timeline
- `match_stats_per_minute`: snapshot theo phút để phục vụ ML
- `win_predictions`: kết quả dự đoán win rate theo phút

## Cách chạy dự án

### 1. Chuẩn bị môi trường

Cập nhật `.env` với Riot API key còn hạn:

```env
RIOT_API_KEY=your_riot_api_key
```

### 2. Khởi động hạ tầng

Chạy từ root repo:

```bash
docker compose up -d
```

Kiểm tra service:

```bash
docker compose ps
docker compose logs -f
```

### 3. Apply schema ClickHouse

Nếu ClickHouse đang chạy với volume cũ, apply lại schema:

```bash
./venv/bin/python infrastructure/apply_clickhouse_schema.py
```

### 4. Chạy stream processing

Mở terminal 1:

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m stream_processing.src.consumer_job
```

### 5. Chạy ingestion real-time

Mở terminal 2:

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m data_ingestion.src.simulator_job --tier CHALLENGER --target-match-count 50 --matches-per-player 25
```

### 6. Kiểm tra dữ liệu đã được ghi

```bash
./venv/bin/python -m stream_processing.src.check_data
```

### 7. Tạo dataset và train AI

```bash
./venv/bin/python -m machine_learning.src.feature_engineering
./venv/bin/python -m machine_learning.src.train_xgboost
```

## Cách crawl offline

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m machine_learning.src.historical_crawler --tier CHALLENGER --target-match-count 50 --matches-per-player 25
```

Ví dụ:

```bash
./venv/bin/python -m machine_learning.src.historical_crawler --tier MASTER --target-match-count 200 --matches-per-player 20
./venv/bin/python -m machine_learning.src.historical_crawler --tier GRANDMASTER --target-match-count 100 --matches-per-player 30
```

## Cách chạy real-time theo cùng kiểu với offline

```bash
cd /home/minhminh05mm/esports_analytics
./venv/bin/python -m data_ingestion.src.simulator_job --tier CHALLENGER --target-match-count 50 --matches-per-player 25
```

Ví dụ:

```bash
./venv/bin/python -m data_ingestion.src.simulator_job --tier MASTER --target-match-count 100 --matches-per-player 20
./venv/bin/python -m data_ingestion.src.simulator_job --tier GRANDMASTER --target-match-count 100 --matches-per-player 30
```

## Chống trùng dữ liệu

Đây là một yêu cầu quan trọng của dự án.

### Offline crawler
- chống trùng theo `match_id`
- kiểm tra cả dữ liệu đã có sẵn trong `machine_learning/data/raw_matches/` và `raw_timelines/`
- nếu cùng một trận xuất hiện khi quét từ nhiều người chơi, chỉ lưu 1 lần

### Real-time ingestion
- chống trùng theo `match_id` trong toàn bộ lượt publish hiện tại
- nếu A và B cùng chơi một trận thì chỉ publish một bản tin logic cho trận đó

## Gợi ý thứ tự test hệ thống

Thứ tự test khuyến nghị:

1. `docker compose up -d`
2. `./venv/bin/python infrastructure/apply_clickhouse_schema.py`
3. `./venv/bin/python -m stream_processing.src.consumer_job`
4. `./venv/bin/python -m data_ingestion.src.simulator_job --tier CHALLENGER --target-match-count 50 --matches-per-player 25`
5. `./venv/bin/python -m stream_processing.src.check_data`
6. `./venv/bin/python -m machine_learning.src.feature_engineering`
7. `./venv/bin/python -m machine_learning.src.train_xgboost`

## Lưu ý khi sử dụng

- Riot API có rate limit, nên crawl số lượng lớn sẽ mất thời gian.
- `RIOT_API_KEY` là key tạm thời, có thể hết hạn bất cứ lúc nào.
- `feature_engineering.py` hiện tạo dataset từ ClickHouse, không đọc trực tiếp từ raw JSON.
- Để train được model, bạn cần có dữ liệu đã đi qua `stream_processing` và được ghi vào ClickHouse.
- `python3` hệ thống có thể thiếu package; nên ưu tiên dùng `./venv/bin/python`.
- Dữ liệu trong `machine_learning/data/*.csv` và `machine_learning/models/*` thường không nên commit lên GitHub nếu là artifact sinh ra trong quá trình chạy.

## Hướng mở rộng tiếp theo

Một số hướng phát triển tiếp:
- thêm orchestration bằng Airflow hoặc Dagster
- thêm unit tests / integration tests
- thêm Kafka topic schema rõ ràng hơn cho từng loại message
- thêm feature store hoặc model registry
- thêm dashboard Metabase hoàn chỉnh cho match analytics và win prediction
- mở rộng từ rank solo queue sang giải đấu chuyên nghiệp nếu có nguồn dữ liệu phù hợp

## Tech stack

- Python
- Riot API
- Kafka
- ClickHouse
- Metabase
- XGBoost
- Docker Compose

## Tác giả

Đây là một dự án portfolio/Data Engineering project theo hướng production-style refactor, tập trung vào:
- kiến trúc module rõ ràng
- stream processing
- real-time analytics
- machine learning inference trên dữ liệu trận đấu e-sports
