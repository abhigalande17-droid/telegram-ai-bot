#!/usr/bin/env python3
"""Fetch the top three Hacker News headlines and save them to a text file."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


HACKER_NEWS_URL = "https://news.ycombinator.com/"


class HeadlineParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headlines = []
        self.in_title = False
        self.buffer = []

    def handle_starttag(self, tag, attrs):
        if tag == "span" and dict(attrs).get("class") == "titleline":
            self.in_title = True
            self.buffer = []

    def handle_data(self, data):
        if self.in_title:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "span" and self.in_title:
            title = "".join(self.buffer).strip()
            if title:
                self.headlines.append(title)
            self.in_title = False


def extract_headlines(html, limit=3):
    parser = HeadlineParser()
    parser.feed(html)
    return parser.headlines[:limit]


def fetch_headlines():
    request = Request(HACKER_NEWS_URL, headers={"User-Agent": "headline-agent/1.0"})
    with urlopen(request, timeout=30) as response:
        return extract_headlines(response.read().decode("utf-8"))


def save_headlines(headlines, output_path):
    Path(output_path).write_text("\n".join(f"{index}. {title}" for index, title in enumerate(headlines, 1)) + "\n", encoding="utf-8")


def run(output_path="headlines.txt"):
    headlines = fetch_headlines()
    if len(headlines) < 3:
        raise RuntimeError("Hacker News returned fewer than three headlines")
    save_headlines(headlines, output_path)
    return headlines


def self_test():
    sample = "".join(
        f'<span class="titleline"><a>Headline {index}</a></span>'
        for index in range(1, 4)
    )
    headlines = extract_headlines(sample)
    if headlines != [f"Headline {index}" for index in range(1, 4)]:
        raise RuntimeError("headline parser self-test failed")
    print("Self-test passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="headlines.txt")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    headlines = run(args.output)
    print(f"Saved {len(headlines)} headlines to {args.output}")


if __name__ == "__main__":
    main()
