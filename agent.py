import re
import sys
from datetime import datetime

from langchain_ollama import OllamaLLM

DEFAULT_TASK = "Write a python script using Playwright to open Instagram and login."
OUTPUT_FILE = "agent_responses.txt"
llm = OllamaLLM(model="qwen:0.5b", temperature=0.1, num_predict=256)


def extract_python_code(response_text):
    text = str(response_text).strip()

    fence_pattern = re.compile(r"```\s*(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()

    lines = text.splitlines()
    code_lines = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("python") and stripped.endswith(":"):
            in_code = True
            continue
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
    if code_lines:
        return "\n".join(code_lines).strip()

    return ""


def save_generated_code(code_text):
    if not code_text:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_code_{timestamp}.py"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(code_text)
    print(f"\nPython code saved to: {filename}")
    return filename


def save_response(task_prompt, response_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}]\n")
        file.write(f"Task: {task_prompt}\n")
        file.write("Response:\n")
        file.write(response_text)
        file.write("\n\n---\n\n")


def run_agent(task_prompt):
    prompt = (
        "You are a concise coding assistant. "
        "Answer in plain English or Python code only when the task asks for code. "
        "Keep each response short, clear, and useful. "
        f"Task: {task_prompt}"
    )
    print(f"टास्क शुरू हो रहा है: {task_prompt}")
    response = llm.invoke(prompt)
    response_text = str(response)
    print("\nएजेंट का जवाब:")
    print(response_text)

    save_response(task_prompt, response_text)
    print(f"\nResponse saved to {OUTPUT_FILE}")

    code = extract_python_code(response_text)
    if code:
        save_generated_code(code)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        run_agent(task)
    else:
        print("Interactive Ollama Agent")
        print("Type your task and press Enter. Type 'exit' to quit.")
        while True:
            task = input("\nYour task: ").strip()
            if not task:
                print("Please enter a task.")
                continue
            if task.lower() in {"exit", "quit", "q"}:
                print("Goodbye!")
                break
            run_agent(task)
