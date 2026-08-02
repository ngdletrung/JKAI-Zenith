import re

__all__ = ["SQL_SELECT", "SQL_INSERT", "SQL_UPDATE", "SQL_DELETE"]

SQL_SELECT = re.compile(r"SELECT\s+.+FROM", re.IGNORECASE | re.DOTALL)
SQL_INSERT = re.compile(r"INSERT\s+INTO", re.IGNORECASE)
SQL_UPDATE = re.compile(r"UPDATE\s+\w+", re.IGNORECASE)
SQL_DELETE = re.compile(r"DELETE\s+FROM", re.IGNORECASE)
