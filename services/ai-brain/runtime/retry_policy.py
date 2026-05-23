from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class RetryPolicy:
    """
    🔁 Khế Ước Tái Thử
    """
    max_attempts: int
    backoff_type: str # "exponential", "linear", "fixed"
    retry_on: Tuple[str, ...] # vd: ("timeout", "network_error")
    
    def calculate_delay(self, attempt: int) -> float:
        if self.backoff_type == "exponential":
            return 2 ** attempt
        elif self.backoff_type == "linear":
            return 2 * attempt
        return 1.0
