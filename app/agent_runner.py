
import os
import json
from openai import OpenAI
from tool_registry import get_registered_function_specs, get_tool_by_name
from agent_planner import run_declarative_planner
import tools # need for tool discovery
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


_prompt_cache: dict[str, bool] = {}

# Decide if the prompt is multi-step (LLM classifier)
def is_multi_step_prompt(prompt: str) -> bool:
    if prompt in _prompt_cache:
        return _prompt_cache[prompt]

    tool_summaries = ", ".join([tool["name"] for tool in FUNCTION_SPECS])  # short version

    examples = """
        Examples:
        "Find user Alice" → {"multi_step": false}
        "Create Bob then increase salary" → {"multi_step": true}
        "If Ana exists, update salary" → {"multi_step": true}
        "Delete user Andrea" → {"multi_step": false}
     """

    system_message = (
        "You are a classifier. Decide whether a user's request requires multiple tool calls "
        "(e.g., find + update) or just one.\n\n"
        f"Tools available: {tool_summaries}\n\n"
        "Reply only with JSON: {\"multi_step\": true} or {\"multi_step\": false}.\n"
        f"{examples}"
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content).get("multi_step", False)
    except Exception:
        result = False

    _prompt_cache[prompt] = result
    return result

# Run using standard OpenAI tool calling
def run_simple_tool_agent(prompt: str):
    functions = get_registered_function_specs()
    print("Registered tools: >>>>>>", [f["name"] for f in get_registered_function_specs()])
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant who solves user-related requests using tools."},
            {"role": "user", "content": prompt}
        ],
        functions=functions,
        function_call="auto"
    )
    msg: ChatCompletionMessage = response.choices[0].message
    print(f"got from LLM: >>>>>>{msg}")
    if not msg.function_call:
        return {"response": msg.content or "🤷 I didn't understand that."}
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
