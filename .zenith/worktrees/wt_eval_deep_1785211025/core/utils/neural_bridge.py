import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger("NeuralBridge")

class NeuralBridge:
    """
    🏛️ JKAI ZENITH: NEURAL BRIDGE (RUFLO V3 AMALGAMATION)
    Cầu nối toán học thượng tầng, mang sức mạnh của Tô-pô đại số và
    Năng lượng Sheaf Laplacian vào lõi JKAI.
    """
    
    def __init__(self):
        self.coherence_threshold = 0.3
        self.contradiction_threshold = 0.7

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Tính toán độ tương đồng Cosine."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

    def compute_coherence_energy(self, vectors: List[np.ndarray]) -> Dict[str, Any]:
        """
        🧬 [SHEAF-LAPLACIAN]: Tính toán năng lượng mâu thuẫn logic.
        Energy 0 = Hoàn toàn nhất quán.
        Energy 1 = Mâu thuẫn cực hạn.
        """
        n = len(vectors)
        if n < 2:
            return {"energy": 0.0, "coherent": True, "level": "stable"}

        # Xây dựng ma trận tương đồng (Similarity Matrix)
        sim_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                sim = self.cosine_similarity(vectors[i], vectors[j])
                sim_matrix[i, j] = sim_matrix[j, i] = sim

        # Tính toán năng lượng (Simplified Sheaf Laplacian Energy)
        # Energy = sum( (1 - sim_ij) * ||v_i - v_j||^2 )
        energy = 0.0
        total_weight = 0.0
        
        for i in range(n):
            for j in range(i + 1, n):
                weight = max(0, 1 - sim_matrix[i, j]) # Trọng số dựa trên sự khác biệt
                diff = vectors[i] - vectors[j]
                diff_norm_sq = np.sum(diff**2)
                
                energy += weight * diff_norm_sq
                total_weight += weight

        if total_weight == 0:
            normalized_energy = 0.0
        else:
            normalized_energy = energy / total_weight

        # Ánh xạ về khoảng [0, 1] bằng hàm Sigmoid
        final_energy = 1.0 / (1.0 + np.exp(-normalized_energy + 2.0))
        
        level = "stable"
        if final_energy > self.contradiction_threshold:
            level = "contradictory"
        elif final_energy > self.coherence_threshold:
            level = "warning"

        return {
            "energy": float(final_energy),
            "coherent": final_energy < self.coherence_threshold,
            "level": level,
            "confidence": 1.0 - float(final_energy)
        }

    def detect_structural_gaps(self, vectors: List[np.ndarray]) -> Dict[str, Any]:
        """
        ⚛️ [TOPOLOGY-GNN]: Phát hiện lỗ hổng cấu trúc trong tri thức (Betti Numbers approximation).
        Tìm kiếm các 'vòng lặp vô định' hoặc các cụm tri thức bị cô lập.
        """
        n = len(vectors)
        if n < 2:
            return {"gaps": 0, "connected": True}

        # Đếm số lượng thành phần liên thông (Connected Components) - Betti 0
        # Sử dụng ngưỡng tương đồng để xác định 'kết nối'
        threshold = 0.8
        adj = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                if self.cosine_similarity(vectors[i], vectors[j]) > threshold:
                    adj[i, j] = adj[j, i] = 1

        # Thuật toán BFS để đếm các thành phần liên thông
        visited = [False] * n
        components = 0
        for i in range(n):
            if not visited[i]:
                components += 1
                queue = [i]
                visited[i] = True
                while queue:
                    u = queue.pop(0)
                    for v in range(n):
                        if adj[u, v] == 1 and not visited[v]:
                            visited[v] = True
                            queue.append(v)

        return {
            "betti_0": components, # Số lượng đảo tri thức
            "connected": components == 1,
            "structural_integrity": 1.0 / components
        }

# Singleton instance
neural_bridge = NeuralBridge()
