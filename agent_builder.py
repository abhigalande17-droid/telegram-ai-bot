import argparse
import json
import re
import subprocess
import sys
import time
from urllib.request import urlopen
from pathlib import Path

from langchain_ollama import OllamaLLM


AGENTS_DIR = Path(__file__).parent / "agents"
MODEL_NAME = "qwen:0.5b"


def slugify(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "_".join(words[:5]) or "generated_agent"


def extract_json(text):
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The model did not return a JSON object")
    return json.loads(candidate[start : end + 1])


def fallback_plan(workflow):
    name = slugify(workflow)
    return {
        "name": name,
        "tools": ["Python standard library", "argparse"],
        "workflow": workflow,
        "script": fallback_script(name, workflow),
    }


def ensure_ollama():
    api_url = "http://127.0.0.1:11434/api/tags"
    try:
        with urlopen(api_url, timeout=1):
            return
    except OSError:
        pass

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as error:
        raise RuntimeError("Ollama is not installed") from error

    for _ in range(20):
        try:
            with urlopen(api_url, timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("Ollama did not become ready")


def fallback_script(name, workflow):
    workflow_json = json.dumps(workflow)
    return f'''#!/usr/bin/env python3
"""Generated workflow agent: {name}."""

import argparse


WORKFLOW = {workflow_json}


def run(task):
    return f"Agent '{name}' received: {{task}}\\nWorkflow: {{WORKFLOW}}"


def main():
    parser = argparse.ArgumentParser(description=WORKFLOW)
    parser.add_argument("task", nargs="?", default="self-test")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    print(run("self-test" if args.self_test else args.task))


if __name__ == "__main__":
    main()
'''


def build_plan(workflow):
    prompt = f"""You are a Python workflow architect.
Given this requested agent workflow:
{workflow}

Return ONLY one valid JSON object with these string/list fields:
{{
  "name": "short_snake_case_name",
  "tools": ["required tools or libraries"],
  "workflow": "brief implementation plan",
  "script": "complete Python source code"
}}

The generated script must use only installed or Python standard-library packages,
define a run(task) function, accept a positional task argument, and support
`--self-test` without network access or credentials. Keep the script concise.
"""
    try:
        ensure_ollama()
        response = OllamaLLM(
            model=MODEL_NAME,
            temperature=0.1,
            num_predict=768,
        ).invoke(prompt)
        plan = extract_json(str(response))
        required = {"name", "tools", "workflow", "script"}
        if not required.issubset(plan) or not isinstance(plan["script"], str):
            raise ValueError("The model response is missing required fields")
        return plan
    except Exception as error:
        print(f"Model planning failed ({error}); using the built-in fallback.")
        return fallback_plan(workflow)


def normalize_plan(plan, workflow):
    name = slugify(plan.get("name", workflow))
    script = plan.get("script", "")
    if "--self-test" not in script or "def run(" not in script:
        script = fallback_script(name, workflow)
    return {
        "name": name,
        "tools": plan.get("tools", ["Python standard library"]),
        "workflow": plan.get("workflow", workflow),
        "script": script,
    }


def self_test(script_path):
    result = subprocess.run(
        [sys.executable, str(script_path), "--self-test"],
        capture_output=True,
        text=True,
        timeout=20,
        cwd=script_path.parent,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"self-test failed: {details}")
    return result.stdout.strip()


def build_agent(workflow):
    plan = normalize_plan(build_plan(workflow), workflow)
    AGENTS_DIR.mkdir(exist_ok=True)
    script_path = AGENTS_DIR / f"{plan['name']}.py"
    plan_path = AGENTS_DIR / f"{plan['name']}_plan.json"
    script_path.write_text(plan["script"].rstrip() + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    plan_path.write_text(json.dumps({k: plan[k] for k in plan if k != "script"}, indent=2) + "\n", encoding="utf-8")
    try:
        subprocess.run([sys.executable, "-m", "py_compile", str(script_path)], check=True)
        output = self_test(script_path)
    except (subprocess.CalledProcessError, RuntimeError):
        plan = fallback_plan(workflow)
        script_path = AGENTS_DIR / f"{plan['name']}.py"
        script_path.write_text(plan["script"].rstrip() + "\n", encoding="utf-8")
        script_path.chmod(0o755)
        plan_path = AGENTS_DIR / f"{plan['name']}_plan.json"
        plan_path.write_text(json.dumps({k: plan[k] for k in plan if k != "script"}, indent=2) + "\n", encoding="utf-8")
        output = self_test(script_path)
    print(f"Created agent: {script_path}")
    print(f"Saved plan: {plan_path}")
    print(f"Self-test passed: {output}")
    return script_path


def main():
    parser = argparse.ArgumentParser(description="Build and self-test local Python agents.")
    parser.add_argument("prompt", nargs="+", help="Description of the new agent workflow")
    args = parser.parse_args()
    build_agent(" ".join(args.prompt))


if __name__ == "__main__":
    main()