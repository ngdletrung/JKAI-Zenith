import os
import time
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Zenith File Warden")

@app.get("/")
def home():
    return {"status": "online", "service": "Zenith File Warden", "master": "LeeTrung"}

@app.get("/search")
def search_files(query: str, path: str = os.getenv("INTELLIGENCE_DIR", "/intelligence")):
    """
    Tìm kiếm tệp tin theo từ khóa.
    """
    results = []
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                if query.lower() in file.lower():
                    results.append({
                        "name": file,
                        "path": os.path.join(root, file),
                        "size": os.path.getsize(os.path.join(root, file)),
                        "last_modified": time.ctime(os.path.getmtime(os.path.join(root, file)))
                    })
    except Exception as e:
        return {"error": str(e)}
    
    return {"query": query, "count": len(results), "results": results[:50]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
