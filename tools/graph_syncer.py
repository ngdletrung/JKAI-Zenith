import asyncio
import os
import re
from graphrag_sdk import GraphRAG, ConnectionConfig, LiteLLM, LiteLLMEmbedder
from graphrag_sdk.models.openai import OpenAIModels

# [ZENITH FILE DIRECTIVE]
# - File: graph_syncer.py
# - Role: Neural Syncer (Synchronizes Markdown Knowledge to FalkorDB Graph).
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0

async def sync_knowledge():
    print("--- [ ZENITH NEURAL SYNCER ] ---")
    
    # 1. Configuration (Bridging to JKAI Sovereign Engine)
    # Using LiteLLM to route through our local Ollama (ai-executor proxy pattern)
    connection = ConnectionConfig(host="localhost", port=6380, graph_name="zenith_brain")
    
    # We use local models via LiteLLM as per Master's Hardware Affinity
    llm = LiteLLM(model="ollama/qwen2.5-coder:3b", api_base="http://localhost:11434")
    embedder = LiteLLMEmbedder(model="ollama/nomic-embed-text", api_base="http://localhost:11434")

    intelligence_dir = r"d:\Docker\JKAI\intelligence"
    
    async with GraphRAG(connection=connection, llm=llm, embedder=embedder) as rag:
        print(f"Connected to FalkorDB at localhost:6380")
        
        # 2. Ingestion (The Great Migration)
        files_to_sync = [f for f in os.listdir(intelligence_dir) if f.endswith(".md")]
        
        for file_name in files_to_sync:
            file_path = os.path.join(intelligence_dir, file_name)
            print(f"Synchronizing: {file_name}...")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Surgical cleaning of SDS headers before ingestion to reduce noise
                clean_content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
                
                await rag.ingest(text=clean_content, document_id=file_name)
        
        # 3. Finalization (Deduplication & Indexing)
        print("Finalizing Neural Graph (Deduplicating & Indexing)...")
        await rag.finalize()
        print("--- [ SYNC COMPLETE: ZENITH IS NOW GRAPH-AWARE ] ---")

if __name__ == "__main__":
    asyncio.run(sync_knowledge())
