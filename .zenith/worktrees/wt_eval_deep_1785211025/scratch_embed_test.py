import httpx
import asyncio

async def test_embed():
    url = "http://host.docker.internal:11434/api/embeddings"
    # Create a large text (e.g. 5000 characters)
    large_text = "JKAI " * 1000
    payload = {
        "model": "nomic-embed-text:latest",
        "prompt": large_text
    }
    print(f"Sending request with {len(large_text)} chars...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Vector size: {len(resp.json().get('embedding', []))}")
            else:
                print(f"Error: {resp.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_embed())
