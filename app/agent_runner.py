
import os
import json
from openai import OpenAI
from tool_registry import get_registered_function_specs, get_tool_by_name
from agent_planner import run_declarative_planner
from openai.types.chat import ChatCompletionMessage
import tools # need for tool discovery
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


_prompt_cache: dict[str, bool] = {}  # Cache cleared - delete operations are multi-step

# Decide if the prompt is multi-step (LLM classifier)
def is_multi_step_prompt(prompt: str) -> bool:
    # Check cache first
    if prompt in _prompt_cache:
        print(f"🔍 Cache hit for: {prompt} → {_prompt_cache[prompt]}")
        return _prompt_cache[prompt]
        
    # Use LLM for all classification - it's better at intent recognition
    system_message = (
        "Classify user intent. Return ONLY valid JSON in this exact format.\n\n"
        "Multi-step (true): Intent to CHANGE or REMOVE an existing user\n"
        "Single-step (false): Intent to FIND or CREATE users\n\n"
        "REQUIRED FORMAT:\n"
        '{"multi_step": true} or {"multi_step": false}\n\n'
        "Examples:\n"
        '"update Bob salary" → {"multi_step": true}\n'
        '"nuke user Alice" → {"multi_step": true}\n'
        '"find John" → {"multi_step": false}\n'
        '"create Mary" → {"multi_step": false}\n\n'
        "CRITICAL: No explanations, no other text, only the JSON object above."
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    
    print(f"🔍 Classifier prompt: {prompt}")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
        )
        raw_response = response.choices[0].message.content
        print(f"🤖 Classifier raw response: {raw_response}")
        result = json.loads(raw_response).get("multi_step", False)
        print(f"🤖 LLM classifier decision for '{prompt}': {result}")
        _prompt_cache[prompt] = result
        return result
    except Exception as e:
        print(f"⚠️ LLM classifier error: {e}")
        # Default to false if LLM fails
        _prompt_cache[prompt] = False
        return False

# Run using standard OpenAI tool calling
def run_simple_tool_agent(prompt: str):
    functions = get_registered_function_specs()
    print("Registered tools: >>>>>>", [f["name"] for f in get_registered_function_specs()])
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You must use the available tools to fulfill user requests. Always make a function call - do not ask for more information. If salary is not specified, use 0 as the default salary value."},
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
