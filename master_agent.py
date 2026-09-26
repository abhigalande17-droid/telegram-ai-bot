import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).parent
AGENTS_DIR = ROOT / "agents"
BUILDER = ROOT / "agent_builder.py"
STOP_WORDS = {
    "agent", "an", "and", "for", "from", "give", "that", "the", "this",
    "with", "your", "create", "tiny", "task", "user",
}


@dataclass
class TaskAnalysis:
    name: str
    keywords: set[str]
    tools: list[str]


class SmartRouter:
    CATEGORIES = ("hacker_news", "scheduler", "weather", "market_analysis", "custom_workflow")

    def classify(self, task: str) -> str | None:
        provider = os.getenv("MASTER_BRAIN", "auto").lower()
        if provider in {"auto", "gemini"} and os.getenv("GEMINI_API_KEY"):
            try:
                response = self.call_gemini(task)
                category = self._parse_category(response)
                if category:
                    return category
            except Exception:
                pass
        if provider in {"auto", "gemini", "ollama"}:
            try:
                category = self._parse_category(self.call_local_brain(task))
                if category:
                    return category
            except Exception:
                pass
        return None

    def _prompt(self, task: str) -> str:
        categories = ", ".join(self.CATEGORIES)
        return (
            "Classify this user task into exactly one category: "
            f"{categories}. Reply with only the category name. Task: {task}"
        )

    def _parse_category(self, response: str) -> str | None:
        response = response.lower().strip()
        for category in self.CATEGORIES:
            if re.search(rf"\b{re.escape(category)}\b", response):
                return category
        return None

    def call_gemini(self, task: str) -> str:
        from google import genai
        from google.genai import types

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=30_000),
        )
        response = client.models.generate_content(model=model, contents=self._prompt(task))
        if not response.text:
            raise RuntimeError("Gemini returned an empty response")
        return response.text

    def call_local_brain(self, task: str) -> str:
        from langchain_ollama import OllamaLLM

        model = os.getenv("OLLAMA_MODEL", "qwen:0.5b")
        response = OllamaLLM(model=model, temperature=0, num_predict=24).invoke(self._prompt(task))
        return str(response)


def analyze_task(task: str, routed_category: str | None = None) -> TaskAnalysis:
    words = set(re.findall(r"[a-z0-9]+", task.lower()))
    words -= STOP_WORDS
    words = {word for word in words if len(word) >= 4}
    if routed_category == "hacker_news" or {"headline", "headlines", "hacker", "news"} & words:
        name = "hacker_news"
        tools = ["web scraping", "HTML parsing", "file output"]
    elif routed_category == "scheduler" or {"schedule", "scheduler", "task", "reminder", "alert"} & words:
        name = "scheduler"
        tools = ["JSON storage", "background polling", "notifications"]
    elif routed_category == "weather" or {"weather", "temperature", "forecast"} & words:
        name = "weather"
        tools = ["weather API", "HTTP client"]
    elif routed_category == "market_analysis" or {"forex", "currency", "exchange", "market", "stock", "stocks"} & words:
        name = "market_analysis"
        tools = ["market data", "analysis", "file or console output"]
    else:
        name = "custom_workflow"
        tools = ["Python standard library"]
    return TaskAnalysis(name, words, tools)


def read_plan(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").lower()
    except OSError:
        return ""


def find_matching_agent(analysis: TaskAnalysis):
    if not AGENTS_DIR.exists():
        return None

    best_path = None
    best_score = (0, 0)
    for script in AGENTS_DIR.glob("*.py"):
        if script.name == "__init__.py":
            continue
        searchable = f"{script.stem} {read_plan(script.with_name(f'{script.stem}_plan.json'))}"
        score = sum(1 for keyword in analysis.keywords if keyword in searchable)
        if analysis.name in searchable:
            score += 3
        priority = (score, int(script.stem == analysis.name))
        if priority > best_score:
            best_path, best_score = script, priority
    return best_path if best_score[0] >= 2 else None


def build_subagent(task: str, before: dict[Path, int]) -> Path:
    prompt = (
        f"Build a sub-agent for this task: {task}. "
        "The script must accept the complete task as a positional argument, "
        "perform the workflow, print only the final result, and support --self-test."
    )
    result = subprocess.run(
        [sys.executable, str(BUILDER), prompt],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=240,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "agent_builder.py failed")
    created = [
        path
        for path in AGENTS_DIR.glob("*.py")
        if path not in before or path.stat().st_mtime_ns > before[path]
    ]
    if not created:
        raise RuntimeError("agent_builder.py did not create a sub-agent")
    return max(created, key=lambda path: path.stat().st_mtime)


def run_in_background(agent_path: Path, task: str) -> str:
    process = subprocess.Popen(
        [sys.executable, str(agent_path), task],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(timeout=240)
    if process.returncode != 0 and "unrecognized arguments" in stderr:
        process = subprocess.Popen(
            [sys.executable, str(agent_path)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(timeout=240)
    if process.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "sub-agent failed")
    return stdout.strip()


def execute(task: str) -> str:
    routed_category = SmartRouter().classify(task)
    analysis = analyze_task(task, routed_category)
    existing = find_matching_agent(analysis)
    if existing is None:
        before = {
            path: path.stat().st_mtime_ns
            for path in AGENTS_DIR.glob("*.py")
        } if AGENTS_DIR.exists() else {}
        existing = build_subagent(task, before)
    return run_in_background(existing, task)


def main():
    parser = argparse.ArgumentParser(description="Autonomous controller for local agents.")
    parser.add_argument("task", nargs="+", help="High-level task for the controller")
    args = parser.parse_args()
    try:
        result = execute(" ".join(args.task))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"Controller failed: {error}")
    print(result)


if __name__ == "__main__":
    main()