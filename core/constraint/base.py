import abc
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ConstraintResult(Generic[T]):
    data: T
    raw: str
    engine: str
    cached: bool = False


class ConstraintEngine(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        schema: type[T],
        system: str | None = None,
        **kwargs,
    ) -> ConstraintResult[T]:
        ...

    def generate_or_fallback(
        self,
        prompt: str,
        schema: type[T],
        system: str | None = None,
        max_retries: int = 2,
        **kwargs,
    ) -> ConstraintResult[T]:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self.generate(prompt, schema, system=system, **kwargs)
            except Exception as e:
                last_error = e
        raise last_error
