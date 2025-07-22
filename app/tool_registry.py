TOOL_REGISTRY = {}
FUNCTION_SPECS = []


def register_tool(name: str, description: str, parameters: dict, example: str = None):
    print(f"register invoked for: {name}, {description} {parameters}, {example}")
    if example:
        description = f"{description} Example: {example}"
    def decorator(func):
        TOOL_REGISTRY[name] = func
        FUNCTION_SPECS.append({
            "name": name,
            "description": description,
            "parameters": parameters
        })
        return func
    return decorator

def get_registered_function_specs():
    return FUNCTION_SPECS

def get_tool_by_name(name: str):
    return TOOL_REGISTRY.get(name)
