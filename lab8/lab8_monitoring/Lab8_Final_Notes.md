# Lab 8 Todo And Demo Notes

This file is the final working guide for Lab 8 using team topic `movielog18`.

It covers:
- what we already completed
- what each component does
- how the pieces depend on each other
- what to verify in Prometheus and Grafana
- what to say to the TA with the deliverables in mind

## 1. What We Completed

### Code completed

- [x] Updated [kafka-monitoring.py](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/kafka-monitoring.py) to use topic `movielog18` by default.
- [x] Added a Prometheus `Counter` named `request_count` with label `http_status`.
- [x] Kept the `Histogram` named `request_latency_seconds`.
- [x] Added parsing logic for recommendation-request events from Kafka.
- [x] Added parsing logic for request latency in milliseconds and converted it to seconds for Prometheus.
- [x] Made the parser more defensive so non-recommendation records are skipped.

### Environment completed

- [x] Created a local virtual environment at `.venv`.
- [x] Installed dependencies from [requirements.txt](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/requirements.txt).
- [x] Started the SSH tunnel from local `localhost:9092` to Kafka on `128.2.220.241:9092`.
- [x] Started Docker Desktop.
- [x] Started Prometheus, Grafana, and Node Exporter with [docker-compose.yaml](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/docker-compose.yaml).

### Monitoring completed

- [x] Verified the exporter exposes metrics on `http://localhost:8765/metrics`.
- [x] Verified Prometheus is available at `http://localhost:9090`.
- [x] Verified Grafana is available at `http://localhost:3000`.
- [x] Verified Prometheus targets are `UP`.
- [x] Created the Grafana Prometheus data source.
- [x] Created the Grafana dashboard with the required panels.

## 2. Files In This Repo

- [README.md](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/README.md)
  The lab instructions and deliverables.
- [kafka-monitoring.py](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/kafka-monitoring.py)
  The Python exporter that reads Kafka and exposes Prometheus metrics.
- [docker-compose.yaml](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/docker-compose.yaml)
  Starts Prometheus, Grafana, and Node Exporter.
- [prometheus/prometheus.yml](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/prometheus/prometheus.yml)
  Tells Prometheus what to scrape.
- [requirements.txt](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/requirements.txt)
  Python packages used by the exporter.
- [grafana-datasource.json](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/grafana-datasource.json)
  API payload used to create the Grafana Prometheus data source.
- [grafana-dashboard.json](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/grafana-dashboard.json)
  API payload used to create the Grafana dashboard.

## 3. How The Whole System Works

This is the main dependency chain:

1. Kafka events exist remotely on `128.2.220.241`.
2. The SSH tunnel forwards remote Kafka port `9092` to your local `localhost:9092`.
3. The Python script reads from Kafka topic `movielog18` through that local tunnel.
4. The Python script exposes Prometheus metrics on local port `8765`.
5. Prometheus runs in Docker and scrapes `host.docker.internal:8765`.
6. Prometheus also scrapes itself and Node Exporter.
7. Grafana connects to Prometheus and visualizes those metrics.

In short:

`Kafka -> SSH tunnel -> kafka-monitoring.py -> /metrics -> Prometheus -> Grafana`

## 4. What Each Component Does

### Kafka

- Kafka is the source of the log events.
- The relevant topic for this team is `movielog18`.
- The exporter only reads from Kafka. It does not write to Kafka.

### SSH tunnel

- Kafka is not directly exposed to your machine on `128.2.220.241:9092`.
- The tunnel makes Kafka appear locally at `localhost:9092`.
- Without the tunnel, the Python consumer gets `NoBrokersAvailable`.

Tunnel command:

```bash
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 9092:localhost:9092 tunnel@128.2.220.241 -NT
```

Password:

```text
mlip-kafka
```

### kafka-monitoring.py

- This script is the custom metrics exporter.
- It consumes Kafka events.
- It filters for recommendation requests.
- It increments a counter per HTTP status code.
- It records request latency in a histogram.
- It starts an HTTP endpoint on port `8765` so Prometheus can scrape metrics.

Important metrics:

- `request_count_total`
  Total recommendation requests, labeled by `http_status`.
- `request_latency_seconds_bucket`
  Histogram buckets for request latency.
- `request_latency_seconds_sum`
  Sum of observed latencies.
- `request_latency_seconds_count`
  Count of observed latency samples.

### Prometheus

- Prometheus is the metrics collector.
- It uses a pull model, meaning it periodically scrapes `/metrics` endpoints.
- In this lab, it scrapes:
  - itself
  - the Kafka exporter
  - Node Exporter
- It stores the results as time-series data.

### Node Exporter

- Node Exporter provides system metrics from the host environment.
- In this lab, it is used for metrics like CPU usage.
- The panel for CPU comes from `node_cpu_seconds_total`.

### Grafana

- Grafana is the visualization layer.
- It does not collect data by itself here.
- It sends PromQL queries to Prometheus and plots the results.

## 5. Important Config Relationships

### Python exporter to Kafka

In [kafka-monitoring.py](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/kafka-monitoring.py):

- `bootstrap_servers="localhost:9092"`
- default topic is `movielog18`

This only works if the SSH tunnel is active.

### Prometheus to exporter

In [prometheus/prometheus.yml](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/prometheus/prometheus.yml):

- the `kafka-monitoring` job scrapes `host.docker.internal:8765`

This only works if:

- the Python exporter is running
- port `8765` is bound successfully
- Docker can reach the host through `host.docker.internal`

### Grafana to Prometheus

Grafana must use:

```text
http://prometheus:9090
```

not:

```text
http://localhost:9090
```

Reason:

- Grafana is running inside Docker
- inside the Docker network, Prometheus is reachable by service name `prometheus`

## 6. Exact Commands We Used

### Create virtual environment

```bash
python3 -m venv .venv
```

### Install dependencies

```bash
.venv/bin/python -m pip install -r requirements.txt
```

### Start Kafka tunnel

```bash
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 9092:localhost:9092 tunnel@128.2.220.241 -NT
```

### Start Docker services

```bash
docker compose up -d
```

### Run exporter

```bash
.venv/bin/python kafka-monitoring.py
```

### Check exporter metrics

```bash
curl -s http://localhost:8765/metrics
```

## 7. Where To See Everything

### Prometheus

URL:

```text
http://localhost:9090
```

What to check:

- `Status -> Targets`
- all three targets should be `UP`
- use the query bar to run PromQL queries

### Grafana

URL:

```text
http://localhost:3000
```

Login:

- username: `admin`
- password: `admin`

Dashboard URL:

```text
http://localhost:3000/d/lab8-monitoring/lab-8-monitoring
```

## 8. What To Verify In Prometheus

Go to `Status -> Targets` and show:

- `kafka-monitoring` is `UP`
- `node_exporter` is `UP`
- `prometheus` is `UP`

Then run these queries:

### Request count by status

```promql
request_count_total
```

What it shows:

- separate time series by `http_status`
- for example `200`

### Request rate over time

```promql
sum(rate(request_count_total[5m]))
```

What it shows:

- overall recommendation request throughput
- this is requests per second over the last 5 minutes

### Histogram buckets

```promql
request_latency_seconds_bucket
```

What it shows:

- latency distribution buckets used for percentile calculations

### p95 latency

```promql
histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[5m])) by (le))
```

What it shows:

- the estimated 95th percentile latency over time

### Average latency

```promql
rate(request_latency_seconds_sum[5m]) / rate(request_latency_seconds_count[5m])
```

What it shows:

- mean request latency over time

## 9. What To Verify In Grafana

Open the `Lab 8 Monitoring` dashboard and show these panels:

### Panel 1

Title:

`Total Successful Requests`

Query:

```promql
request_count_total{http_status="200"}
```

Meaning:

- total number of successful recommendation requests

### Panel 2

Title:

`Total Recommendation Requests Over Time`

Query:

```promql
sum(rate(request_count_total[5m]))
```

Meaning:

- total throughput of recommendation requests

### Panel 3

Title:

`Node CPU Usage (system mode)`

Query:

```promql
sum(rate(node_cpu_seconds_total{mode="system"}[5m]))
```

Meaning:

- amount of CPU time spent in system mode

### Panel 4

Title:

`95th Percentile Request Latency`

Query:

```promql
histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[5m])) by (le))
```

Meaning:

- high-end request latency

### Panel 5

Title:

`Average Request Latency`

Query:

```promql
rate(request_latency_seconds_sum[5m]) / rate(request_latency_seconds_count[5m])
```

Meaning:

- average request latency

## 10. Important Notes About The Data

- Most successful requests are labeled as `http_status="200"`.
- Some events may still appear as `http_status="unknown"` if the event format does not match the expected `status NNN` pattern.
- This does not block the required success-count panel, because that panel filters specifically for `http_status="200"`.

## 11. Common Failure Cases

### If Kafka consumer fails with `NoBrokersAvailable`

Cause:

- the SSH tunnel is down

Fix:

- restart the SSH tunnel
- confirm local port `9092` is listening

### If Prometheus shows `kafka-monitoring` as `DOWN`

Cause:

- exporter is not running
- exporter crashed
- exporter cannot bind to port `8765`

Fix:

- restart `kafka-monitoring.py`
- open `http://localhost:8765/metrics`
- confirm the exporter endpoint responds

### If Grafana cannot query Prometheus

Cause:

- wrong Prometheus URL

Fix:

- use `http://prometheus:9090` inside Grafana

### If the graphs are empty

Cause:

- no recent Kafka events
- tunnel down
- exporter down
- Prometheus target down

Fix:

- check tunnel
- check exporter
- check Prometheus targets

## 12. Deliverables Mapping

This lab has three deliverables. Here is how your setup satisfies each one.

### Deliverable 1

`Setup Docker with Prometheus and Grafana. Modify and Run Kafka Monitoring Script.`

What to show:

- Docker services are running
- [docker-compose.yaml](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/docker-compose.yaml) starts Prometheus, Grafana, and Node Exporter
- [kafka-monitoring.py](/Users/bhuvan/Desktop/MLIP/Lab8/lab8_monitoring/kafka-monitoring.py) was completed
- exporter is running and serving metrics at `http://localhost:8765/metrics`

### Deliverable 2

`Verify Prometheus targets and metrics. Run queries in Prometheus. Explain how Prometheus reads and stores metric data, and how it handles counter resets when a service restarts.`

What to show:

- `Status -> Targets` with all targets `UP`
- `request_count_total`
- `sum(rate(request_count_total[5m]))`
- `histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[5m])) by (le))`

What to explain:

- Prometheus scrapes metrics using a pull model
- it stores timestamped time-series data locally
- if the exporter restarts, counters reset to zero
- functions like `rate()` handle resets by looking at the slope of the counter over time

### Deliverable 3

`Configure Grafana Dashboard and add visualizations. Explain how you would aggregate or synchronize metrics if multiple instances of the same service were running.`

What to show:

- Grafana dashboard panels
- Prometheus data source
- the required visualizations rendering live data

What to explain:

- each service instance would expose its own metrics endpoint
- Prometheus would scrape each instance separately
- the time series would differ by labels like `instance` and `job`
- to aggregate across instances, use PromQL such as:

```promql
sum(rate(request_count_total[5m]))
```

or, if there were more labels:

```promql
sum by (http_status) (rate(request_count_total[5m]))
```

## 13. TA Demo Script

Use this script when showing the assignment.

### Opening

"This lab sets up a monitoring pipeline where Kafka events are consumed by a Python exporter, exposed as Prometheus metrics, scraped by Prometheus, and visualized in Grafana."

### Deliverable 1 script

"We used Docker Compose to start Prometheus, Grafana, and Node Exporter. Then we completed `kafka-monitoring.py` for our topic `movielog18`. The script reads recommendation-request events from Kafka through an SSH tunnel, increments a request counter labeled by HTTP status, records latency in a histogram, and exposes everything on `localhost:8765/metrics`."

### Deliverable 2 script

"In Prometheus, under Targets, all three scrape jobs are up: Prometheus itself, Node Exporter, and our Kafka monitoring exporter. Prometheus reads metrics by scraping each target’s `/metrics` endpoint every few seconds. It stores those metric samples as time-series data with timestamps and labels."

"For example, `request_count_total` shows request counts by HTTP status. `sum(rate(request_count_total[5m]))` shows total request throughput, and the histogram-based query gives p95 latency."

"If the exporter restarts, counters reset to zero. Prometheus does not treat that as normal growth forever; functions like `rate()` are designed to work with counter resets by analyzing how the counter changes over a time window."

### Deliverable 3 script

"In Grafana, we connected to Prometheus as the data source and built panels for successful requests, total request rate, node CPU usage, 95th percentile latency, and average latency. Grafana does not collect the data itself here; it visualizes PromQL query results from Prometheus."

"If multiple instances of the same service were running, Prometheus would scrape each instance separately and attach labels such as `instance` and `job`. We would aggregate across instances in PromQL using expressions like `sum(rate(request_count_total[5m]))` or group by status with `sum by (http_status) (...)`."

### Closing

"So the full chain is Kafka to Python exporter to Prometheus to Grafana, and we verified it by checking live metrics, Prometheus targets, and dashboard panels."

## 14. Final Quick Checklist Before Demo

- [ ] Keep Docker running.
- [ ] Keep the SSH tunnel alive.
- [ ] Keep `kafka-monitoring.py` running.
- [ ] Confirm `http://localhost:9090` loads.
- [ ] Confirm `http://localhost:3000` loads.
- [ ] Confirm all Prometheus targets are `UP`.
- [ ] Open the `Lab 8 Monitoring` dashboard before the demo starts.
