#!/usr/bin/env python3
"""Local JSON task scheduler with a notifier interface ready for Telegram."""

import argparse
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol


DATE_FORMAT = "%Y-%m-%d %H:%M"
DEFAULT_STORE = Path(__file__).with_name("tasks.json")


class Notifier(Protocol):
    def send(self, message: str) -> None:
        """Deliver an alert to a console, Telegram, or another channel."""


class ConsoleNotifier:
    def send(self, message: str) -> None:
        print(f"ALERT: {message}", flush=True)


class TelegramNotifier:
    """Adapter point for python-telegram-bot or the Telegram HTTP API."""

    def __init__(self, send_message):
        self.send_message = send_message

    def send(self, message: str) -> None:
        self.send_message(message)


def parse_due_at(value: str) -> str:
    due_at = datetime.strptime(value, DATE_FORMAT)
    return due_at.strftime(DATE_FORMAT)


class TaskStore:
    def __init__(self, path=DEFAULT_STORE):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        if not self.path.exists():
            return []
        with self.lock, self.path.open(encoding="utf-8") as file:
            contents = file.read().strip()
        return json.loads(contents) if contents else []

    def save(self, tasks):
        with self.lock, self.path.open("w", encoding="utf-8") as file:
            json.dump(tasks, file, indent=2)
            file.write("\n")

    def add(self, title, due_at):
        task = {
            "id": uuid.uuid4().hex[:8],
            "title": title,
            "due_at": parse_due_at(due_at),
            "notified": False,
        }
        tasks = self.load()
        tasks.append(task)
        self.save(tasks)
        return task

    def due_tasks(self, now=None):
        now = now or datetime.now()
        tasks = self.load()
        due = []
        changed = False
        for task in tasks:
            due_at = datetime.strptime(task["due_at"], DATE_FORMAT)
            if not task.get("notified") and due_at <= now:
                task["notified"] = True
                due.append(task)
                changed = True
        if changed:
            self.save(tasks)
        return due

    def remove(self, task_id):
        tasks = self.load()
        remaining = [task for task in tasks if task["id"] != task_id]
        if len(remaining) == len(tasks):
            return False
        self.save(remaining)
        return True


class Scheduler:
    def __init__(self, store, notifier, interval=30):
        self.store = store
        self.notifier = notifier
        self.interval = interval
        self.stop_event = threading.Event()

    def check_once(self):
        for task in self.store.due_tasks():
            self.notifier.send(f"{task['title']} (due {task['due_at']})")

    def watch(self):
        print(f"Watching tasks every {self.interval} seconds. Press Ctrl+C to stop.")
        while not self.stop_event.is_set():
            self.check_once()
            self.stop_event.wait(self.interval)

    def stop(self):
        self.stop_event.set()


def self_test():
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        store = TaskStore(Path(directory) / "tasks.json")
        task = store.add("Test reminder", "2000-01-01 09:00")
        messages = []

        class TestNotifier:
            def send(self, message):
                messages.append(message)

        scheduler = Scheduler(store, TestNotifier(), interval=0)
        scheduler.check_once()
        assert task["id"]
        assert len(messages) == 1
        assert store.due_tasks() == []
    print("Self-test passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a task")
    add_parser.add_argument("title")
    add_parser.add_argument("--at", required=True, help="Due time: YYYY-MM-DD HH:MM")
    subparsers.add_parser("list", help="List stored tasks")
    remove_parser = subparsers.add_parser("remove", help="Remove a task")
    remove_parser.add_argument("task_id")
    watch_parser = subparsers.add_parser("watch", help="Watch for due tasks")
    watch_parser.add_argument("--interval", type=int, default=30)
    subparsers.add_parser("self-test", help="Run an offline self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        self_test()
        return

    store = TaskStore(args.store)
    if args.command == "add":
        print(json.dumps(store.add(args.title, args.at), indent=2))
    elif args.command == "list":
        print(json.dumps(store.load(), indent=2))
    elif args.command == "remove":
        print("Removed" if store.remove(args.task_id) else "Task not found")
    elif args.command == "watch":
        try:
            Scheduler(store, ConsoleNotifier(), args.interval).watch()
        except KeyboardInterrupt:
            print("\nStopped")


if __name__ == "__main__":
    main()
