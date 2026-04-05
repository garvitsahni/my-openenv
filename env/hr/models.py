from pydantic import BaseModel
from typing import Literal

class Resume(BaseModel):
    id: str
    candidate_name: str
    years_experience: int
    education: str
    skills: list[str]
    previous_roles: list[str]
    summary: str

class JobDescription(BaseModel):
    id: str
    title: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_years_experience: int
    education_requirement: str
    responsibilities: list[str]

class HRAction(BaseModel):
    action_type: Literal['score_candidate','shortlist','flag_bias',
                         'rank_shortlist','recommend','done']
    args: dict
    episode_id: str

class HRObservation(BaseModel):
    job_description: JobDescription
    resumes: list[Resume]
    step_count: int
    remaining_steps: int
    available_actions: list[str]
    scores_given: dict
    shortlisted: list[str]

class HRGraderResult(BaseModel):
    score: float
    breakdown: dict
    criteria_met: list[str]
    max_possible: float
