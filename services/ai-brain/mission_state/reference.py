# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/reference.py
# - Role: Reference and Dependency Graph Manager
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import os
import re
import hashlib
import logging
from typing import Dict, List, Optional
from .schema import CitationItem, MissionReferences

logger = logging.getLogger("JKAI.ReferenceManager")

class ReferenceManager:
    """Manages source code references, checksums, and dependency chains."""
    @staticmethod
    def calculate_checksum(file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error("[CHECKSUM-ERR] Failed to read %s: %s", file_path, e)
            return None

    def add_reference(self, refs: MissionReferences, ref_id: str, file_path: str, line_range: str = None) -> CitationItem:
        checksum = self.calculate_checksum(file_path)
        item = CitationItem(
            source_path=file_path,
            line_range=line_range,
            checksum=checksum,
            confidence=1.0
        )
        refs.citations[ref_id] = item
        
        # Analyze imports to update dependency graph
        self.update_dependencies(refs, file_path)
        return item

    def verify_references(self, refs: MissionReferences) -> Dict[str, bool]:
        """Verifies if references are stale due to file modifications."""
        results = {}
        for ref_id, citation in refs.citations.items():
            current_checksum = self.calculate_checksum(citation.source_path)
            if not current_checksum:
                results[ref_id] = False # File deleted/unreadable
            else:
                results[ref_id] = (current_checksum == citation.checksum)
        return results

    def update_dependencies(self, refs: MissionReferences, file_path: str):
        """Analyzes simple imports in python file to build local dependency graph."""
        if not file_path.endswith(".py") or not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Simple regex search for local imports
            # matches: import core.utils or from services.ai-brain import dispatcher
            imports = re.findall(r"^(?:import|from)\s+([\w\.]+)", content, re.MULTILINE)
            
            for imp in imports:
                # Convert package import to potential file path
                parts = imp.split(".")
                potential_file = os.path.join(*parts) + ".py"
                # If local file exists, track downstream
                if os.path.exists(potential_file):
                    abs_potential = os.path.abspath(potential_file)
                    abs_source = os.path.abspath(file_path)
                    
                    if abs_potential not in refs.dependency_graph:
                        refs.dependency_graph[abs_potential] = []
                    if abs_source not in refs.dependency_graph[abs_potential]:
                        refs.dependency_graph[abs_potential].append(abs_source)
        except Exception as e:
            logger.warning("[DEP-ANALYZER-WARN] Failed dependency analysis for %s: %s", file_path, e)

    def get_cascading_impact(self, refs: MissionReferences, modified_file: str) -> List[str]:
        """Finds all downstream files impacted by a modification to modified_file."""
        abs_mod = os.path.abspath(modified_file)
        impacted = []
        visited = set()

        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            downstream = refs.dependency_graph.get(node, [])
            for child in downstream:
                impacted.append(child)
                dfs(child)

        dfs(abs_mod)
        return list(set(impacted))
