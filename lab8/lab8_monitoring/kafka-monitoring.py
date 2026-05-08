import os
import re

from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram, start_http_server

topic = os.getenv("KAFKA_TOPIC", "movielog18")

start_http_server(8765)

# Total recommendation requests broken down by HTTP status code.
REQUEST_COUNT = Counter(
    "request_count",
    "Recommendation Request Count",
    ["http_status"],
)

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency (seconds)",
    buckets=(0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
)

HTTP_STATUS_RE = re.compile(r"\bstatus\s+([1-5]\d{2})\b", re.IGNORECASE)
LATENCY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ms\b", re.IGNORECASE)


def extract_status(values, event):
    event_match = HTTP_STATUS_RE.search(event)
    if event_match:
        return event_match.group(1)

    for value in values:
        match = HTTP_STATUS_RE.search(value)
        if match:
            return match.group(1)
    return "unknown"


def extract_latency_seconds(event):
    match = LATENCY_RE.search(event)
    if not match:
        return None
    return float(match.group(1)) / 1000.0


def main():
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers="localhost:9092",
        auto_offset_reset="latest",
        group_id=topic,
        enable_auto_commit=True,
        auto_commit_interval_ms=1000,
    )

    for message in consumer:
        event = message.value.decode("utf-8")
        values = [value.strip() for value in event.split(",")]
        if len(values) < 3 or "recommendation request" not in values[2].lower():
            continue

        status = extract_status(values, event)
        REQUEST_COUNT.labels(http_status=status).inc()

        time_taken = extract_latency_seconds(event)
        if time_taken is not None:
            REQUEST_LATENCY.observe(time_taken)


if __name__ == "__main__":
    main()
