
import os
import json
from openai import OpenAI
from tool_registry import get_registered_function_specs, get_tool_by_name
from agent_planner import run_declarative_planner
import tools # need for tool discovery
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Decide if the prompt is multi-step (LLM classifier)
def is_multi_step_prompt(prompt: str) -> bool:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a classifier. Determine if this user prompt requires multiple steps "
                "like lookup + update, or if it can be handled by a single tool.\n"
                "Respond with JSON: {\"multi_step\": true} or {\"multi_step\": false}"
            )
        },
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
    )
    try:
        return json.loads(response.choices[0].message.content).get("multi_step", False)
    except Exception:
        return False

# Run using standard OpenAI tool calling
def run_simple_tool_agent(prompt: str):
    functions = get_registered_function_specs()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant who solves user-related requests using tools."},
            {"role": "user", "content": prompt}
        ],
        functions=functions,
        function_call="auto"
    )
    msg = response.choices[0].message
    if "function_call" not in msg:
        return {"response": msg.content or "🤷 I didn’t understand that."}
    func_call = msg.function_call
    tool_name = func_call.name
    args = json.loads(func_call.arguments)
    tool_fn = get_tool_by_name(tool_name)
    result = tool_fn(args)
    return {"response": result.get("message"), "type": "tool_call", "tool": tool_name, "args": args}

# Unified interface with routing logic
def run_agent(prompt: str):
    if is_multi_step_prompt(prompt):
        print("🧠 Using planner...")
        result = run_declarative_planner(prompt)
        return {"response": result, "type": "planner"}
    else:
        print("🔧 Using tool...")
        return run_simple_tool_agent(prompt)

# CLI loop
if __name__ == "__main__":
    while True:
        try:
            prompt = input("You: ")
            if prompt.lower() in {"exit", "quit"}:
                break
            result = run_agent(prompt)
            print(f"Agent: {result['response']}")
        except KeyboardInterrupt:
            break
