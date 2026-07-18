from pydantic import BaseModel
from typing import List, Optional


class UserInput(BaseModel):
    prompt: str
    model_name: str = "meta/llama-3.1-70b-instruct"


class AgentAssignment(BaseModel):
    agent: str
    task: str


class ClaudiaDecision(BaseModel):
    status: str  # "accepted" or "rejected"
    assignments: Optional[List[AgentAssignment]] = None
    reason: Optional[str] = None


class AgentResult(BaseModel):
    agent: str
    task: str
    result: str
    speed: str
    artifacts: Optional[List[dict]] = None


class ExecuteResponse(BaseModel):
    status: str
    results: Optional[List[AgentResult]] = None
    total_speed: Optional[str] = None
    model: str
    message: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class ExecutionRequest(BaseModel):
    """Request body for the CrewAI-backed /api/executions endpoint (OpenAI-only
    MVP) — see docs/architecture/ai-execution-crewai.md §6. Distinct from
    UserInput (legacy /api/execute) since `model` here must be an OpenAI model id,
    not one of the NVIDIA-hosted MODEL_OPTIONS."""

    prompt: str
    model: str = "gpt-4o-mini"

