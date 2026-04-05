import pytest
from env.hr.environment import HRScreeningEnv
from env.hr.models import HRAction

def test_reset_deterministic():
    env1 = HRScreeningEnv()
    obs1 = env1.reset("hr-screening-easy", seed=42)
    env2 = HRScreeningEnv()
    obs2 = env2.reset("hr-screening-easy", seed=42)
    assert obs1.model_dump() == obs2.model_dump()

def test_episode_lifecycle():
    env = HRScreeningEnv()
    env.reset("hr-screening-easy")
    
    env.step(HRAction(action_type="score_candidate", args={"resume_id": "resume_001", "score": 9}, episode_id="ep1"))
    env.step(HRAction(action_type="score_candidate", args={"resume_id": "resume_002", "score": 2}, episode_id="ep1"))
    env.step(HRAction(action_type="score_candidate", args={"resume_id": "resume_003", "score": 8}, episode_id="ep1"))
    
    env.step(HRAction(action_type="shortlist", args={"resume_id": "resume_001"}, episode_id="ep1"))
    
    obs, rew, done, info = env.step(HRAction(action_type="done", args={}, episode_id="ep1"))
    assert done is True

def test_sequencing_enforced():
    env = HRScreeningEnv()
    env.reset("hr-screening-easy")
    # Shortlisting before scoring all candidates (0 < 3 resumes)
    obs, rew, done, info = env.step(HRAction(action_type="shortlist", args={"resume_id": "resume_001"}, episode_id="ep1"))
    # The penalty PENALTY_SEQUENCING (-0.05) is applied plus the native reward for shortlisting (+0.15)
    # Total = 0.10
    assert abs(rew - 0.10) < 0.001
