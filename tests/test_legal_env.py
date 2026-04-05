import pytest
from env.legal.environment import LegalContractEnv
from env.legal.models import LegalAction

def test_reset_deterministic():
    env1 = LegalContractEnv()
    obs1 = env1.reset("legal-review-easy", seed=42)
    
    env2 = LegalContractEnv()
    obs2 = env2.reset("legal-review-easy", seed=42)
    
    assert obs1.model_dump() == obs2.model_dump()

def test_episode_lifecycle():
    env = LegalContractEnv()
    env.reset("legal-review-easy")
    
    # identify_type → assess_risk → recommend → done
    env.step(LegalAction(action_type="identify_type", args={}, episode_id="ep1"))
    env.step(LegalAction(action_type="assess_risk", args={}, episode_id="ep1"))
    obs, rew, done, info = env.step(LegalAction(action_type="recommend", args={}, episode_id="ep1"))
    assert not done
    
    obs, rew, done, info = env.step(LegalAction(action_type="done", args={}, episode_id="ep1"))
    assert done is True

def test_sequencing_enforced():
    env = LegalContractEnv()
    env.reset("legal-review-easy")
    
    # Assess risk before identify type
    obs, rew, done, info = env.step(LegalAction(action_type="assess_risk", args={}, episode_id="ep1"))
    assert rew == -0.05 # Penalty for skipping sequence

def test_max_steps_termination():
    env = LegalContractEnv()
    env.reset("legal-review-easy")
    
    for _ in range(19):
        obs, rew, done, info = env.step(LegalAction(action_type="identify_type", args={}, episode_id="ep1"))
        assert not done
        
    obs, rew, done, info = env.step(LegalAction(action_type="identify_type", args={}, episode_id="ep1"))
    assert done is True
