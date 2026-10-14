import asyncio
import os
import re

# [ZENITH FILE DIRECTIVE]
# - File: graph_syncer.py
# - Role: Neural Syncer (Synchronizes Markdown Knowledge to FalkorDB Graph).
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0

async def sync_knowledge():
    print("--- [ ZENITH NEURAL SYNCER ] ---")
    if os.getenv("JKAI_ENABLE_FALKOR_SYNC", "0") != "1":
        from core.utils.repo_map import get_repo_map_index

        idx = get_repo_map_index()
        idx.refresh(force=True)
        edge_count = sum(len(v) for v in idx._reverse_imports.values())
        summary = {
            "status": "success",
            "mode": "local_ast_graph",
            "indexed_python_files": len(idx._file_cache),
            "excluded_third_party_files": idx._excluded_third_party_files,
            "total_workspace_py_files": idx._total_workspace_py_files,
            "total_symbols": len(idx._all_symbols),
            "dependency_edges": edge_count,
        }
        print(
            f"[LOCAL-FIRST AST SYNC] Indexed {summary['indexed_python_files']} Python files, "
            f"{summary['total_symbols']} symbols, {summary['dependency_edges']} dependency edges."
        )
        return summary

    from graphrag_sdk import GraphRAG, ConnectionConfig, LiteLLM, LiteLLMEmbedder
    from graphrag_sdk.models.openai import OpenAIModels  # noqa: F401

    # 1. Configuration (Bridging to JKAI Sovereign Engine)
    # Using LiteLLM to route through our local Ollama (ai-executor proxy pattern)
    connection = ConnectionConfig(host="localhost", port=6380, graph_name="zenith_brain")
    
    # We use local models via LiteLLM as per Master's Hardware Affinity
    llm = LiteLLM(model="ollama/qwen2.5-coder:3b", api_base="http://localhost:11434")
    embedder = LiteLLMEmbedder(model="ollama/nomic-embed-text", api_base="http://localhost:11434")

    from core.utils.project_workspace import get_jkai_workspace_root
    intelligence_dir = str(get_jkai_workspace_root() / "intelligence")
    
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
