from pydantic import BaseModel
from typing import Literal

class Email(BaseModel):
    id: str
    subject: str
    sender: str
    body: str
    timestamp: str
    thread_id: str
    attachments: list

class EmailAction(BaseModel):
    action_type: Literal['classify','assign','escalate','draft','skip','done']
    args: dict
    episode_id: str

class EmailObservation(BaseModel):
    emails: list[Email]
    step_count: int
    remaining_steps: int
    available_actions: list[str]
    context: dict

class EmailGraderResult(BaseModel):
    score: float
    breakdown: dict
    criteria_met: list[str]
    max_possible: float
