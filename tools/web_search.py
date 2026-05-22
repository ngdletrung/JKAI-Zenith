def run(data):
    query = data.get("query", "")
    return {
        "output": f"Fake search result for: {query}",
        "error": None
    }