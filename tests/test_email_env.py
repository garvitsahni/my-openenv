import pytest
from env.email.environment import EmailTriageEnv
from env.email.models import EmailAction

def test_reset_deterministic():
    env1 = EmailTriageEnv()
    obs1 = env1.reset("email-triage-easy", seed=42)
    
    env2 = EmailTriageEnv()
    obs2 = env2.reset("email-triage-easy", seed=42)
    
    assert obs1.model_dump() == obs2.model_dump()

def test_episode_lifecycle():
    env = EmailTriageEnv()
    env.reset("email-triage-easy")
    
    # 5 arbitrary steps
    for idx in range(5):
        obs, rew, done, info = env.step(EmailAction(action_type="skip", args={"email_id": f"e{idx}"}, episode_id="ep1"))
        assert done is False
        
    obs, rew, done, info = env.step(EmailAction(action_type="done", args={}, episode_id="ep1"))
    assert done is True

def test_max_steps_termination():
    env = EmailTriageEnv()
    env.reset("email-triage-easy")
    
    for _ in range(29):
        obs, rew, done, info = env.step(EmailAction(action_type="skip", args={}, episode_id="ep1"))
        assert not done
        
    obs, rew, done, info = env.step(EmailAction(action_type="skip", args={}, episode_id="ep1"))
    assert done is True
