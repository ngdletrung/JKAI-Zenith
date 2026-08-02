import json
import os
import asyncio

class CalibrationEngine:
    """
    Confidence Calibration Engine
    Calculates actual confidence score based on historical reliability:
    Calibrated Confidence = LLM Confidence * Historical Reliability Score
    """
    def __init__(self, weights_path: str = "d:/Docker/JKAI/services/ai-brain/memory/calibration_weights.json"):
        self.weights_path = weights_path
        self.historical_weights = self._load_weights()

    def _load_weights(self) -> dict:
        """Initializes weights from file and populates Redis Cache if active."""
        weights = {}
        if os.path.exists(self.weights_path):
            try:
                with open(self.weights_path, 'r', encoding='utf-8') as f:
                    weights = json.load(f)
            except Exception as e:
                print(f"[CALIBRATION-ERR] Failed to load calibration weights from file: {e}")
        
        # Populate Redis Cache with initial values if available
        try:
            from redis_client import get_redis
            r_conn = get_redis()
            if r_conn:
                for intent, score in weights.items():
                    r_conn.set(f"calibration:weights:{intent}", str(score))
        except Exception as e:
            # Non-blocking, print warning
            print(f"[CALIBRATION-WARN] Redis connection unavailable during initialization: {e}")
            
        return weights

    def get_calibrated_confidence(self, intent: str, llm_confidence: float) -> float:
        """Applies historical reliability score to the LLM confidence rating."""
        # 1. Check RAM Cache
        reliability_score = self.historical_weights.get(intent)
        
        # 2. Check Redis Cache on Cache Miss
        if reliability_score is None:
            try:
                from redis_client import get_redis
                r_conn = get_redis()
                if r_conn:
                    val = r_conn.get(f"calibration:weights:{intent}")
                    if val is not None:
                        reliability_score = float(val)
                        # Sync back to RAM Cache
                        self.historical_weights[intent] = reliability_score
            except Exception as e:
                print(f"[CALIBRATION-WARN] Failed to retrieve score from Redis cache: {e}")

        # 3. Fallback to default full reliability
        if reliability_score is None:
            reliability_score = 1.0

        calibrated = llm_confidence * reliability_score

        if reliability_score < 0.6:
            print(f"[CALIBRATION] Intent '{intent}' has a high historical risk profile (Reliability: {reliability_score:.2f}). Calibrated confidence forced from {llm_confidence:.2f} down to {calibrated:.2f}!")

        return round(calibrated, 3)

    def update_reliability(self, intent: str, is_success: bool):
        """Updates the reliability score using Exponential Weighted Moving Average (EWMA)."""
        current_score = self.historical_weights.get(intent, 1.0)

        # Failure causes faster degradation than success recovery (asymmetry)
        alpha = 0.2 if is_success else 0.4
        target = 1.0 if is_success else 0.0

        new_score = (1 - alpha) * current_score + alpha * target
        new_score = round(new_score, 3)
        self.historical_weights[intent] = new_score

        # 1. Update Redis Cache
        try:
            from redis_client import get_redis
            r_conn = get_redis()
            if r_conn:
                r_conn.set(f"calibration:weights:{intent}", str(new_score))
        except Exception as e:
            print(f"[CALIBRATION-WARN] Failed to write score to Redis cache: {e}")

        # 2. Trigger Async Persistence (Non-blocking Out-of-band File Write)
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(self._save_weights_async())
            else:
                self._save_weights_sync_atomic()
        except RuntimeError:
            # Fallback to sync thread if no active event loop is found
            import threading
            threading.Thread(target=self._save_weights_sync_atomic, daemon=True).start()

    async def _save_weights_async(self):
        """Executes file save operation off the main thread to prevent Event Loop blocking."""
        await asyncio.to_thread(self._save_weights_sync_atomic)

    def _save_weights_sync_atomic(self):
        """Performs a safe, atomic, synchronous write using a temp file and OS-level replace."""
        try:
            dir_name = os.path.dirname(self.weights_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            import tempfile
            with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
                json.dump(self.historical_weights, tf, indent=4)
                temp_name = tf.name
            
            os.replace(temp_name, self.weights_path)
        except Exception as e:
            print(f"[CALIBRATION-ERR] Failed to persist calibration weights atomically: {e}")
