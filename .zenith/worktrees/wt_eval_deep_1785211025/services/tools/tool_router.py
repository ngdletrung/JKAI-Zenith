from registry import registry

def route_tool(name, **kwargs):
    tool = registry.get_tool(name)
    if tool:
        return tool(**kwargs)
    return {"error": "Tool not found"}

