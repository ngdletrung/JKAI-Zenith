import os
import json

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, func):
        self.tools[name] = func

    def get_tool(self, name):
        return self.tools.get(name)

registry = ToolRegistry()

