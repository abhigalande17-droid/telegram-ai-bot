#!/usr/bin/env python3
"""Generated workflow agent: create_an_agent_that_reports."""

import argparse


WORKFLOW = "create an agent that reports the word count of text"


def run(task):
    return f"Agent 'create_an_agent_that_reports' received: {task}\nWorkflow: {WORKFLOW}"


def main():
    parser = argparse.ArgumentParser(description=WORKFLOW)
    parser.add_argument("task", nargs="?", default="self-test")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    print(run("self-test" if args.self_test else args.task))


if __name__ == "__main__":
    main()
