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


class ExecuteResponse(BaseModel):
    status: str
    results: Optional[List[AgentResult]] = None
    total_speed: Optional[str] = None
    model: str
    message: Optional[str] = None
