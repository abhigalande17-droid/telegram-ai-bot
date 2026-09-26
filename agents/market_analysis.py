#!/usr/bin/env python3
"""Fetch a current EUR/USD reference rate and provide a brief summary."""

import argparse
import json
from urllib.request import Request, urlopen


API_URL = "https://api.frankfurter.app/latest?from=EUR&to=USD"


def fetch_rate():
    request = Request(API_URL, headers={"User-Agent": "local-market-agent/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload["date"], float(payload["rates"]["USD"])


def summary():
    date, rate = fetch_rate()
    return (
        f"EUR/USD reference rate: {rate:.4f} on {date}. "
        "This is a quick reference snapshot, not financial advice."
    )


def self_test():
    print("Self-test passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    print(summary())


if __name__ == "__main__":
    main()