import asyncio
import sys
import os

# Mocking the environment
os.environ["OLLAMA_EMBED_URL"] = "http://host.docker.internal:11434/api/embeddings"

# Add the project root to sys.path
sys.path.append(os.getcwd())

from core.utils.embed import embed

async def test():
    print("Type of embed: " + str(type(embed)))
    
    print("\n--- Testing Sync Call (embed(text)) ---")
    try:
        # This calls __call__ -> get_embedding
        result = embed("test sync query")
        if result:
            print("[SUCCESS] Sync Embedding size: " + str(len(result)))
        else:
            print("[WARNING] Success call but returned None (Ollama might be offline or model not found)")
    except Exception as e:
        print("[ERROR] Calling embed(query): " + str(e))

    print("\n--- Testing Async Call (await embed.get_embedding_async(text)) ---")
    try:
        result_async = await embed.get_embedding_async("test async query")
        if result_async:
            print("[SUCCESS] Async Embedding size: " + str(len(result_async)))
        else:
            print("[WARNING] Success call but returned None")
    except Exception as e:
        print("[ERROR] Calling embed.get_embedding_async: " + str(e))

if __name__ == "__main__":
    asyncio.run(test())
