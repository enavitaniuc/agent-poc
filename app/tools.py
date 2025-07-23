from typing import Dict, Optional, Union
from app.planner_tool import extract_user_intent
from tool_registry import register_tool

fake_db: Dict[int, Dict[str, Union[str, int]]] = {}
user_id_counter = 1

# @register_tool(
#     name="plan_user_actions",
#     description="Break down a high-level user request into a list of tool steps to execute.",
#     parameters={
#         "type": "object",
#         "properties": {
#             "prompt": {
#                 "type": "string",
#                 "description": "The full natural language request from the user."
#             }
#         },
#         "required": ["prompt"]
#     },
#     example="If user Bob exists add 500 to his salary, otherwise create him and set his salary to 500."
# )
# def plan_user_actions(input: dict) -> dict:
#     prompt = input.get("prompt", "")
#     return extract_user_intent(prompt)


# Simulated in-memory user database
fake_db = {
    1: {"name": "Alice", "salary": 50000},
    2: {"name": "Bob", "salary": 60000},
}
name_to_id = {user["name"]: uid for uid, user in fake_db.items()}

@register_tool(
    name="find_user_by_name",
    description="Find a user by name.",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    },
    example="Find user named Alice"
)
def find_user_by_name(args: dict) -> dict:
    name = args.get("name")
    if not name:
        return {**message("❌ Please provide a name. Try: 'Find user named Alice'"), **fail()}
    uid = name_to_id.get(name)
    if not uid:
        return {**message(f"👤 No user found with the name '{name}'."), **fail()}
    user = fake_db[uid]
    return {
        **ok(),
        **_internal(user_id=uid, name=user["name"], salary=user["salary"]),
        **message(f"✅ Found user {user['name']} with salary ${user['salary']}")
    }

def message(msg: str) -> dict:
    """Wrap a user-facing message."""
    return {"message": msg}

def ok() -> dict:
    """Wrap a user-facing message."""
    return {"status": "ok"}

def fail() -> dict:
    """Wrap a user-facing message."""
    return {"status": "fail"}


def _internal(**kwargs) -> dict:
    """Wrap internal-only fields (for planner use)."""
    return {"_internal": kwargs}

@register_tool(
    name="create_user",
    description="Create a new user. Requires name and salary.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "salary": {"type": "integer"}
        },
        "required": ["name", "salary"]
    },
    example="Create user Anna with $50000 salary"
)
def create_user(args: dict) -> dict:
    name = args.get("name")
    salary = args.get("salary")
    print(f">>>>inside the create_user {name} {salary}")
    if not name:
        return {**message("❌ Please provide a name. Example: 'Create user Alice with salary 50000'"), **fail()}
    if salary is None:
        return {**message("❌ Please provide a salary. Example: 'Create user Bob with salary 60000'"), **fail()}

    if name in name_to_id:
        return {**message(f"⚠️ User '{name}' already exists."), **fail()}

    print(f">>>>> before create {fake_db}")
    new_id = max(fake_db.keys()) + 1
    fake_db[new_id] = {"name": name, "salary": salary}
    print(f">>>>> after create {fake_db}")
    name_to_id[name] = new_id
    return {
        **ok(),
        **_internal(user_id=new_id, name=fake_db[new_id]["name"], salary=fake_db[new_id]["salary"]),
        **message(f"✅ Created user '{name}' with salary ${salary}")
    }

@register_tool(
    name="update_user_salary",
    description="Update a user's salary by user ID. Provide amount to add or subtract.",
    parameters={
        "type": "object",
        "properties": {
            "user_id": {"type": "integer"},
            "amount": {"type": "integer"}
        },
        "required": ["user_id", "amount"]
    },
    example="Increase salary of user with ID 1 by 1000"
)
def update_user_salary(args: dict) -> dict:
    uid = args.get("user_id")
    amount = args.get("amount")

    if uid is None:
        return {**message("❌ Please provide a user ID. Example: 'Update salary for user 2 by 500'"), **fail()}
    if amount is None:
        return {**message("❌ Please provide an amount. Example: 'Increase user 1 salary by 500'"), **fail()}

    if uid not in fake_db:
        return {**message(f"❌ User with ID {uid} not found."), **fail()}

    fake_db[uid]["salary"] += amount

    return {**message(f"💰 Updated salary for user {uid}. New salary: ${fake_db[uid]['salary']}"), **ok()}

@register_tool(
    name="delete_user",
    description="Delete a user by ID.",
    parameters={
        "type": "object",
        "properties": {
            "user_id": {"type": "integer"}
        },
        "required": ["user_id"]
    },
    example="Delete user with Id"
)
def delete_user(args: dict) -> dict:
    uid = args.get("user_id")

    if uid is not None:
        if uid in fake_db:
            name_to_id.pop(fake_db[uid]["name"], None)
            fake_db.pop(uid)
            return {**message(f"🗑️ Deleted user with ID {uid}"), **ok()}
        return {**message(f"❌ No user found with ID {uid}"), **fail()}

    return {**message("❌ Please provide an ID for user. Example: 'Delete user  1234'"), **fail()}
