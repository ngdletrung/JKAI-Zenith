import asyncio
import os
import json
from runtime.calibration_engine import CalibrationEngine

class OutcomeLearner:
    """
    Outcome Learning Engine
    Subscribes to Redis Pub/Sub channels to learn and calibrate weights dynamically.
    """
    def __init__(self, calibration_engine: CalibrationEngine, channel: str = "zenith:cognitive_events"):
        self.calibration_engine = calibration_engine
        self.channel = channel
        self._running = False
        self._task = None

    def start(self):
        """Launches the background async event subscriber."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        print("[OUTCOME-LEARNER] Real-time event subscriber initiated.")

    def stop(self):
        """Stops the background subscriber gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        print("[OUTCOME-LEARNER] Real-time event subscriber terminated.")

    async def _listen_loop(self):
        """Asynchronous listening loop that handles automatic reconnection."""
        import redis.asyncio as aioredis
        
        while self._running:
            try:
                redis_host = os.getenv("REDIS_HOST")
                if not redis_host:
                    print("[OUTCOME-LEARNER-ERR] REDIS_HOST env variable is not set. Retrying in 5s.")
                    await asyncio.sleep(5)
                    continue

                from core.config import IS_DOCKER
                if not IS_DOCKER and redis_host in ["redis-ai", "redis-queue"]:
                    redis_host = "127.0.0.1"

                redis_port = int(os.getenv("REDIS_PORT", 6379))
                redis_pass = os.getenv("REDIS_PASSWORD")

                async_client = aioredis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_pass,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_keepalive=True,
                    retry_on_timeout=True
                )

                async with async_client.pubsub() as pubsub:
                    await pubsub.subscribe(self.channel)
                    print(f"[OUTCOME-LEARNER] Subscribed to Redis channel: {self.channel}")

                    while self._running:
                        try:
                            # Retrieve message with a short timeout to allow cancellation check
                            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                            if message:
                                data_str = message.get("data")
                                if data_str:
                                    await self._process_event(data_str)
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            print(f"[OUTCOME-LEARNER-WARN] Issue while reading message: {e}")
                            await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[OUTCOME-LEARNER-ERR] Redis subscriber connection failed: {e}. Reconnecting in 5s.")
                await asyncio.sleep(5)

    async def _process_event(self, data_str: str):
        """Extracts cognitive outcome metrics and triggers the calibration engine."""
        try:
            event = json.loads(data_str)
            intent = event.get("intent")
            is_success = event.get("is_success")

            if intent is not None and is_success is not None:
                print(f"[OUTCOME-LEARNER] Processing cognitive event -> Intent: {intent}, Success: {is_success}")
                self.calibration_engine.update_reliability(intent, is_success)
        except Exception as e:
            print(f"[OUTCOME-LEARNER-ERR] Error processing event payload: {e}")
