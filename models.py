from pydantic import BaseModel
from typing import Optional

class EvalRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = "general"

class ModelResult(BaseModel):
    model_name: str
    response: str
    latency_ms: float
    tokens_used: int
    cost_per_1k_tokens: float
    quality_score: float
    winner: bool = False

class EvalResponse(BaseModel):
    prompt: str
    results: list[ModelResult]
    recommended_model: str
    reasoning: str
