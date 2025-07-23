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
            {"tool": "create_user", "args": {"name": "{name}", "salary": 0}},
            {"tool": "find_user_by_name", "args": {"name": "{name}"}},
            {"tool": "update_user_salary", "args": {"user_id": "$.1._internal.user_id", "amount": "{amount}"}}
        ]
    },
    "delete_user": {
        "description": "Delete user after looking them up by name.",
        "variables": ["name"],
        "plan": [
            {"tool": "find_user_by_name", "args": {"name": "{name}"}},
            {"tool": "delete_user", "args": {"user_id": "$.0._internal.user_id"}}
        ]
    }
}

# Select a plan based on user intent (using LLM)
def choose_plan_with_llm(prompt: str):
    plan_descriptions = "\n".join(
        f"{name}: {meta['description']} (variables: {meta['variables']})" 
        for name, meta in DECLARATIVE_PLANS.items()
    )

    system_message = (
        "You are a strict planner.\n"
        "Your task is to choose **one** of the following plan names and extract the required variables from the user prompt.\n\n"
        f"Plans:\n{plan_descriptions}\n\n"
        "IMPORTANT: Use the exact variable names shown in parentheses for each plan.\n"
        "For example, if a plan shows (variables: ['name', 'amount']), use 'name' and 'amount' as keys.\n\n"
        "Respond ONLY in valid JSON with this structure:\n"
        "{ \"plan\": \"plan_name\", \"variables\": { \"exact_var_name1\": value1, \"exact_var_name2\": value2 } }\n\n"
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
    
    raw_response = response.choices[0].message.content.strip()
    print(f"🤖 LLM plan selection response: {raw_response}")
    
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse plan JSON: {e}")
        raise

# Resolve step args, including user input vars and outputs from previous steps
def resolve_args(arg_dict, results, input_vars):
    resolved = {}
    for key, val in arg_dict.items():
        if isinstance(val, str):
            if val.startswith("$."):
                try:
                    parts = val[2:].split(".")
                    step_idx = int(parts[0])
                    if 0 <= step_idx < len(results):
                        result = results[step_idx]
                        # Traverse nested fields like "_internal.user_id"
                        for field_part in parts[1:]:
                            if isinstance(result, dict) and field_part in result:
                                result = result[field_part]
                            else:
                                result = None
                                break
                        resolved[key] = result
                    else:
                        resolved[key] = None
                except (ValueError, IndexError):
                    resolved[key] = None
            elif val.startswith("{") and val.endswith("}"):
                var_name = val.strip("{}")
                resolved[key] = input_vars.get(var_name)
            else:
                resolved[key] = val
        else:
            resolved[key] = val
    return resolved

# Execute steps defined in the selected plan
def execute_plan(plan_steps, user_input_vars):
    results = []
    print(f"🚀 Starting plan execution with {len(plan_steps)} steps")
    for i, step in enumerate(plan_steps):
        print(f"🔧 Step {i+1}: {step}")
        tool_name = step["tool"]
        raw_args = step["args"]
        args = resolve_args(raw_args, results, user_input_vars)
        print(f"📋 Resolved args for {tool_name}: {args}")
        tool_fn = get_tool_by_name(tool_name)
        output = tool_fn(args)
        print(f"✅ Step {i+1} result: {output}")
        if output and output.get("status", "fail") == "fail":
            print(f"❌ Step {i+1} failed, stopping execution")
            return output.get("message")
        results.append(output)
    print(f"🎉 Plan execution completed with {len(results)} results")
    return results

# Main entry to use declarative planner
def run_declarative_planner(prompt: str):
    try:
        plan_info = choose_plan_with_llm(prompt)
        print(f">>>>>>>>>>🧠 Planner chose plan: {plan_info}")
        
        plan_name = plan_info.get("plan")
        if plan_name not in DECLARATIVE_PLANS:
            print(f"❌ Plan '{plan_name}' not found in available plans: {list(DECLARATIVE_PLANS.keys())}")
            return {"message": f"❌ Plan '{plan_name}' not available"}
        
        plan = DECLARATIVE_PLANS[plan_name]
        print(f">>>>>>>>>>🧠 Planner accessing plan: {plan}")
        steps = plan["plan"]
        print(f">>>>>>>>>>🧠 steps: {steps}")
        variables = plan_info["variables"]
        print(f">>>>>>>>>>🧠 variables: {variables}")
        result = execute_plan(steps, variables)
        return result[-1]
    except Exception as e:
        print(f"❌ Planner error: {e}")
        return {"message": f"❌ Planner failed: {e}"}
