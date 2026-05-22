import os
import asyncpg
import json
from asyncpg.pool import Pool

class PostgresClient:
    def __init__(self):
        self.host = os.getenv("DB_POSTGRESDB_HOST", "postgres")
        self.port = int(os.getenv("DB_POSTGRESDB_PORT", "5432"))
        self.user = os.getenv("POSTGRES_USER", "n8n")
        self.password = os.getenv("POSTGRES_PASSWORD", "")
        self.database = os.getenv("POSTGRES_DB", "n8n")
        self.pool: Pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )
        # Tự động tạo bảng nếu chưa có
        async with self.pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id          BIGSERIAL PRIMARY KEY,
                event_id    UUID NOT NULL UNIQUE,
                trace_id    VARCHAR(128) NOT NULL,
                task_id     VARCHAR(128),
                step_id     VARCHAR(128),
                event_type  VARCHAR(64) NOT NULL,
                actor       VARCHAR(64) NOT NULL,
                payload     JSONB,
                created_at  TIMESTAMPTZ DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id     VARCHAR(128) PRIMARY KEY,
                trace_id    VARCHAR(128) NOT NULL,
                goal        TEXT NOT NULL,
                status      VARCHAR(64) NOT NULL,
                autonomy_tier INT DEFAULT 4,
                context     JSONB,
                created_at  TIMESTAMPTZ DEFAULT now(),
                updated_at  TIMESTAMPTZ DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_events (trace_id);
            CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_events (task_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
            """)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def insert_audit_event(self, event_id, trace_id, task_id, step_id, event_type, actor, payload):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events (event_id, trace_id, task_id, step_id, event_type, actor, payload)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event_id, trace_id, task_id, step_id, event_type, actor, json.dumps(payload)
            )

    async def upsert_task(self, task):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (task_id, trace_id, goal, status, autonomy_tier, context, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, now())
                ON CONFLICT (task_id) DO UPDATE SET 
                    status = EXCLUDED.status,
                    updated_at = now()
                """,
                task.task_id, task.trace_id, task.goal, task.status.value, task.autonomy_tier, json.dumps(task.context or {})
            )

postgres_client = PostgresClient()
