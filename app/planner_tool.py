
import json
from openai import OpenAI
import os
from dotenv import load_dotenv
from tool_registry import get_tool_by_name

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_user_intent(prompt: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You extract structured plans from user prompts as JSON with a 'steps' list."},
            {"role": "user", "content": f"Extract steps from this user prompt: '{prompt}'"}
        ],
        response_format="json"
    )
    message = response.choices[0].message
    return json.loads(message.content)

def execute_user_plan(steps: list) -> dict:
    log = []
    for step in steps:
        tool_name = step.get("tool")
        arguments = step.get("args", {})
        tool = get_tool_by_name(tool_name)
        if not tool:
            log.append(f"❌ Tool {tool_name} not found.")
            continue
        try:
            result = tool(arguments)
            log.append(f"✅ {tool_name} → {result}")
        except Exception as e:
            log.append(f"❌ Error in {tool_name}: {str(e)}")
    return {"response": "\n".join(log), "type": "plan"}
