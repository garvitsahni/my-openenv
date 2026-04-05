from pydantic import BaseModel
from typing import Literal

class ContractClause(BaseModel):
    id: str
    title: str
    body: str

class Contract(BaseModel):
    id: str
    type: str
    parties: list[str]
    date: str
    clauses: list[ContractClause]

class LegalAction(BaseModel):
    action_type: Literal['identify_type','assess_risk','flag_clause','identify_missing','recommend','done']
    args: dict
    episode_id: str

class LegalObservation(BaseModel):
    contracts: list[Contract]
    step_count: int
    remaining_steps: int
    available_actions: list[str]
    flags_raised: list[dict]

class LegalGraderResult(BaseModel):
    score: float
    breakdown: dict
    criteria_met: list[str]
    max_possible: float
