import json
from openai import OpenAI
from tool_registry import get_tool_by_name

client = OpenAI()

# Declarative Plans
DECLARATIVE_PLANS = {
    "update_salary_after_lookup": {
        "description": "Update a user's wage after looking them up by name.",
        "variables": ["name", "amount"],
        "plan": [
            {"tool": "find_user_by_name", "args": {"name": "{name}"}},
            {"tool": "update_user_salary", "args": {"user_id": "$.0._internal.user_id", "amount": "{amount}"}}
        ]
    },
    "create_then_update": {
        "description": "Create a user, then update their wage.",
        "variables": ["name", "amount"],
        "plan": [
            {"tool": "create_user", "args": {"name": "{name}", "salary": "{amount}"}},
            {"tool": "find_user_by_name", "args": {"name": "{name}"}},
            {"tool": "update_user_salary", "args": {"user_id": "$.1._internal.user_id", "amount": "{amount}"}}
        ]
    },
    "delete_user": {
        "description": "Delete user after looking them up by name.",
        "variables": ["name"],
        "plan": [
            {"tool": "find_user_by_name", "args": {"name": "{name}"}},
            {"tool": "update_user_salary", "args": {"user_id": "$.0._internal.user_id", "amount": "{amount}"}}
        ]
    }
}

# Select a plan based on user intent (using LLM)
def choose_plan_with_llm(prompt: str):
    plan_descriptions = "\n".join(
        f"{name}: {meta['description']}" for name, meta in DECLARATIVE_PLANS.items()
    )

    system_message = (
        "You are a strict planner.\n"
        "Your task is to choose **one** of the following plan names and extract any required variables from the user prompt.\n\n"
        f"Plans:\n{plan_descriptions}\n\n"
        "Respond ONLY in valid JSON with this structure:\n"
        "{ \"plan\": \"plan_name\", \"variables\": { ... } }\n\n"
        "Do not explain, comment, or ask follow-up questions. Only return the JSON plan."
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
    )

    return json.loads(response.choices[0].message.content.strip())

# Resolve step args, including user input vars and outputs from previous steps
def resolve_args(arg_dict, context):
    resolved = {}
    for key, val in arg_dict.items():
        if isinstance(val, str):
            if val.startswith("$."):
                step_idx, field = val[2:].split(".")
                resolved[key] = context[int(step_idx)].get(field)
            elif val.startswith("{") and val.endswith("}"):
                resolved[key] = context["input"].get(val.strip("{}"))
            else:
                resolved[key] = val
        else:
            resolved[key] = val
    return resolved

# Execute steps defined in the selected plan
def execute_plan(plan_steps, user_input_vars):
    results = []
    context = {"input": user_input_vars}
    for step in plan_steps:
        tool_name = step["tool"]
        raw_args = step["args"]
        args = resolve_args(raw_args, results + [context])
        tool_fn = get_tool_by_name(tool_name)
        output = tool_fn(args)
        if output & output.get("status", "fail") == "fail":
            return output.get("message")
        try:
            results.append(json.loads(output.get("message")))
        except Exception:
            results.append({"output": output})
    return results

# Main entry to use declarative planner
def run_declarative_planner(prompt: str):
    plan_info = choose_plan_with_llm(prompt)
    plan = DECLARATIVE_PLANS[plan_info["plan"]]
    steps = plan["plan"]
    variables = plan_info["variables"]
    result = execute_plan(steps, variables)
    return result[-1]
