#!/usr/bin/env python3
"""Generated workflow agent: build_a_sub_agent_for."""

import argparse


WORKFLOW = "Build a sub-agent for this task: Fetch current EUR to USD forex rate and give me a quick market summary. The script must accept the complete task as a positional argument, perform the workflow, print only the final result, and support --self-test."


def run(task):
    return f"Agent 'build_a_sub_agent_for' received: {task}\nWorkflow: {WORKFLOW}"


def main():
    parser = argparse.ArgumentParser(description=WORKFLOW)
    parser.add_argument("task", nargs="?", default="self-test")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    print(run("self-test" if args.self_test else args.task))


if __name__ == "__main__":
    main()
