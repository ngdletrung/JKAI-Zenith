---
type: python_file
file: postgres_client.py
tags: []
---

# postgres_client

import os
import asyncpg
import json
from asyncpg.pool import Pool

class PostgresClient:
    def __init__(self):
        self.host = os.getenv("DB_POSTGRESDB_HOST", "postgres")
        self.port = int(os.getenv("DB_POSTGRESDB_PORT", "5432"))
        self.user = os.getenv("POSTGRES_USER", "n8n")
   

## Links to
- [[os]]
- [[asyncpg]]
- [[json]]
- [[asyncpg.pool]]
