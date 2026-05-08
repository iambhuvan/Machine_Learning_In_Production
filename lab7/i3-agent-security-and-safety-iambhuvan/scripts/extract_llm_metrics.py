#!/usr/bin/env python3
"""Extract llm_call metrics from python/agent/messages.log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "logfile",
        nargs="?",
        default="python/agent/messages.log",
        help="Path to the JSONL agent log file.",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=10,
        help="Show the last N llm_call events.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.logfile)
    events = []

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("event") != "llm_call":
            continue
        events.append(
            {
                "latency_ms": payload.get("latency_ms"),
                "prompt_tokens": payload.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": payload.get("usage", {}).get("completion_tokens"),
                "total_tokens": payload.get("usage", {}).get("total_tokens"),
            }
        )

    if not events:
        print("No llm_call events found.")
        return

    print("idx latency_ms prompt_tokens completion_tokens total_tokens")
    start = max(len(events) - args.last, 0)
    for idx, event in enumerate(events[start:], start=start + 1):
        print(
            f"{idx:>3} "
            f"{event['latency_ms']!s:>10} "
            f"{event['prompt_tokens']!s:>13} "
            f"{event['completion_tokens']!s:>17} "
            f"{event['total_tokens']!s:>12}"
        )


if __name__ == "__main__":
    main()
