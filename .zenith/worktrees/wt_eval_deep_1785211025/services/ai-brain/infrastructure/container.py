import os
import redis
import httpx
from core.utils.engine import engine

class ServiceContainer:
    """
    🏢 TẬP ĐOÀN JKAI ZENITH - KHO LƯU TRỮ DEPENDENCY (IoC)
    Quản lý vòng đời của tất cả các service và tài nguyên hệ thống.
    """
    def __init__(self):
        # 1. Khởi tạo kết nối Redis (Shared State)
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_conn = redis.Redis(
            host=self.redis_host, 
            port=6379, 
            db=0, 
            password=self.redis_password,
            decode_responses=True
        )
        
        # 2. Khởi tạo HTTP Client (Shared Network Context)
        self.http_client = httpx.AsyncClient(timeout=600.0)
        
        # 3. Khởi tạo các Core Engines
        # self.policy_engine = PolicyEngine() # Hiện đang dùng classmethod nên không cần init ở đây, nhưng tương lai có thể
        
        # 4. Gateway Layer
        from receptionist.auth_interceptor import AuthInterceptor
        from receptionist.command_router import CommandRouter
        from receptionist.memory_gateway import MemoryGateway
        from receptionist.planner_gateway import PlannerGateway
        from receptionist.executor_gateway import ExecutorGateway
        
        self.auth_interceptor = AuthInterceptor(self.redis_conn)
        self.command_router = CommandRouter(self.redis_conn, self.http_client)
        self.memory_gateway = MemoryGateway(self.redis_conn)
        self.planner_gateway = PlannerGateway(self.http_client)
        self.executor_gateway = ExecutorGateway(self.http_client)

    async def close(self):
        await self.http_client.aclose()
        self.redis_conn.close()

# Singleton instance
container = ServiceContainer()
