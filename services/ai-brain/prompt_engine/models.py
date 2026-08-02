import json
import logging
from typing import TypeVar, Type, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JKAI.PromptEngine.Models")

T = TypeVar("T", bound=BaseModel)


class LookupOutput(BaseModel):
    answer: str = Field(description="Câu trả lời chính xác cho câu hỏi")
    sources: list[str] = Field(default_factory=list, description="Danh sách nguồn tham khảo")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Độ tin cậy 0-1")


class PlanOutput(BaseModel):
    steps: list[dict[str, Any]] = Field(description="Danh sách các bước thực thi")
    reasoning: str = Field(default="", description="Giải thích logic của kế hoạch")


class CriticOutput(BaseModel):
    passed: bool = Field(description="Phản hồi có đạt chất lượng không")
    issues: list[str] = Field(default_factory=list, description="Các vấn đề phát hiện")
    suggestions: list[str] = Field(default_factory=list, description="Gợi ý cải thiện")


class ExecuteOutput(BaseModel):
    action: str = Field(description="Hành động cần thực thi")
    params: dict[str, Any] = Field(default_factory=dict, description="Tham số cho hành động")
    result: Optional[str] = Field(default=None, description="Kết quả sau khi thực thi")


class TaskClassification(BaseModel):
    category: str = Field(description="LOUKUP, CODING, ANALYSIS, hoặc CHAT")


SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "LOOKUP": LookupOutput,
    "PLANNER": PlanOutput,
    "CRITIC": CriticOutput,
    "EXECUTOR": ExecuteOutput,
}
