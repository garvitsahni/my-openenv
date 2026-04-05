import json
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any
import time

from env.email.environment import EmailTriageEnv
from env.email.models import EmailAction
from env.legal.environment import LegalContractEnv
from env.legal.models import LegalAction
from env.hr.environment import HRScreeningEnv
from env.hr.models import HRAction

app = FastAPI(title="WorkBench OpenEnv API")

# In-memory episode tracking for the dashboard
# Format: {"ep_id": {"env_type": "email", "difficulty": "easy", "step_count": 0, "max_steps": 30, "cumulative_score": 0.0, "passing_score": 0.5, "recent_actions": [], "done": False, "final_score": 0.0}}
episodes_db = {}
active_episode_id = None

class ResetRequest(BaseModel):
    task_id: str
    seed: int = 42

def get_env_instance(env_type):
    if env_type == "email": return EmailTriageEnv()
    if env_type == "legal": return LegalContractEnv()
    if env_type == "hr": return HRScreeningEnv()
    raise HTTPException(status_code=400, detail="Invalid env_type")

@app.post("/reset")
def reset_env(req: ResetRequest, env_type: str = "email"):
    global active_episode_id
    try:
        env = get_env_instance(env_type)
        obs = env.reset(req.task_id, req.seed)
        
        episode_id = "ep_" + req.task_id
        active_episode_id = episode_id
        
        difficulty = req.task_id.split("-")[-1]
        passing_score = 0.5 # default
        if difficulty == "easy": passing_score = 0.7
        elif difficulty == "medium": passing_score = 0.65
        elif difficulty == "hard": passing_score = 0.60
            
        episodes_db[episode_id] = {
            "episode_id": episode_id,
            "env_type": env_type,
            "difficulty": difficulty,
            "task_id": req.task_id,
            "step_count": 0,
            "max_steps": env.max_steps,
            "cumulative_score": 0.0,
            "passing_score": passing_score,
            "recent_actions": [],
            "done": False,
            "final_score": 0.0,
            "env_instance": env
        }
        
        return {"observation": obs.model_dump(), "episode_id": episode_id, "task": {"id": req.task_id}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
async def step_env(request: dict):
    episode_id = request.get("episode_id", "")
    action_dict = request.get("action", {})
    
    if episode_id not in episodes_db:
        raise HTTPException(status_code=404, detail="Episode not found")
        
    ep_data = episodes_db[episode_id]
    env_type = ep_data["env_type"]
    env = ep_data["env_instance"]
    
    try:
        if env_type == "email":
            action = EmailAction(action_type=action_dict.get("action_type"), args=action_dict.get("args", {}), episode_id=episode_id)
        elif env_type == "legal":
            action = LegalAction(action_type=action_dict.get("action_type"), args=action_dict.get("args", {}), episode_id=episode_id)
        elif env_type == "hr":
            action = HRAction(action_type=action_dict.get("action_type"), args=action_dict.get("args", {}), episode_id=episode_id)
            
        obs, reward, done, info = env.step(action)
        
        # update tracking
        ep_data["step_count"] += 1
        ep_data["cumulative_score"] += reward
        ep_data["recent_actions"].insert(0, {"step": ep_data["step_count"], "action_type": action_dict.get("action_type"), "reward": reward})
        if len(ep_data["recent_actions"]) > 5:
            ep_data["recent_actions"].pop()
            
        if done:
            ep_data["done"] = True
            # Real Environment Normalization
            if env_type == "email":
                final_score = max(0.0, min(1.0, ep_data["cumulative_score"] / 0.85))
            elif env_type == "legal":
                final_score = max(0.0, min(1.0, ep_data["cumulative_score"] / 0.70))
            elif env_type == "hr":
                final_score = max(0.0, min(1.0, ep_data["cumulative_score"] / 0.90))
            else:
                final_score = ep_data["cumulative_score"]
                
            ep_data["final_score"] = final_score
            
            global active_episode_id
            if active_episode_id == episode_id:
                active_episode_id = None
                
        return {"observation": obs.model_dump(), "reward": reward, "done": done, "info": info}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/state")
def get_state(episode_id: str):
    if episode_id in episodes_db:
        st = episodes_db[episode_id]["env_instance"].state()
        return {"state": st, "step_count": st["step_count"], "cumulative_score": st["cumulative_score"]}
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/tasks")
def list_tasks(env_type: str = "email"):
    diffs = ["easy", "medium", "hard", "adversarial"]
    if env_type == "email": return [f"email-triage-{d}" for d in diffs]
    if env_type == "legal": return [f"legal-review-{d}" for d in diffs]
    if env_type == "hr": return [f"hr-screening-{d}" for d in diffs]
    return []

@app.get("/score/{episode_id}")
def get_score(episode_id: str):
    if episode_id in episodes_db:
        score = max(0.0, episodes_db[episode_id]["final_score"] if episodes_db[episode_id]["done"] else episodes_db[episode_id]["cumulative_score"])
        return {"final_score": score, "step_scores": [], "grader_details": {}}
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/health")
def health():
    return {"status": "ok", "environments": ["email", "legal", "hr"]}

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    # Serving the new High-Performance Cyberpunk HUD
    with open(os.path.join(os.path.dirname(__file__), "dashboard", "index.html"), "r") as f:
        return f.read()

@app.get("/dashboard/data")
def get_dashboard_data():
    completed = []
    for eid, ep in episodes_db.items():
        if ep["done"]:
            completed.append({
                "episode_id": eid,
                "env_type": ep["env_type"],
                "difficulty": ep["task_id"].split("-")[-1],
                "final_score": ep["final_score"],
                "passing_score": ep["passing_score"],
                "steps": ep["step_count"],
                "status": "PASS" if ep["final_score"] >= ep["passing_score"] else "FAIL",
                "time": ep.get("end_time", time.time())
            })

    active = None
    if active_episode_id and active_episode_id in episodes_db:
        ep = episodes_db[active_episode_id]
        active = {
            "episode_id": active_episode_id,
            "task_id": ep["task_id"],
            "step_count": ep["step_count"],
            "max_steps": ep["max_steps"],
            "cumulative_score": ep["cumulative_score"],
            "recent_actions": ep["recent_actions"]
        }

    total_episodes = len(completed)
    avg_score = sum(e["final_score"] for e in completed) / max(1, total_episodes)
    best_score = max([e["final_score"] for e in completed] if completed else [0])
    pass_rate = (len([e for e in completed if e["status"] == "PASS"]) / max(1, total_episodes)) * 100

    return {
        "active_episode": active,
        "completed_episodes": sorted(completed, key=lambda x: x["time"], reverse=True)[:10],
        "stats": {
            "total": total_episodes,
            "avg_score": avg_score,
            "best_score": best_score,
            "pass_rate": round(pass_rate, 1)
        }
    }
    completed = []
    total_score = 0
    best_score = -999
    passed = 0
    
    for ep in episodes_db.values():
        if ep["done"]:
            sc = max(0.0, ep["final_score"])
            total_score += sc
            best_score = max(best_score, sc)
            if sc >= ep["passing_score"]:
                passed += 1
            completed.append({
                "episode_id": ep["episode_id"],
                "env_type": ep["env_type"],
                "difficulty": ep["difficulty"],
                "final_score": sc,
                "passing_score": ep["passing_score"],
                "steps": ep["step_count"]
            })
            
    completed = completed[-10:]
    stats = {
        "total": len(completed),
        "avg_score": total_score / len(completed) if completed else 0.0,
        "best_score": best_score if completed else 0.0,
        "pass_rate": round(passed / len(completed) * 100) if completed else 0
    }
    
    active_payload = None
    if active_episode_id and active_episode_id in episodes_db:
        aep = episodes_db[active_episode_id]
        active_payload = {
            "episode_id": aep["episode_id"],
            "env_type": aep["env_type"],
            "difficulty": aep["difficulty"],
            "task_id": aep["task_id"],
            "step_count": aep["step_count"],
            "max_steps": aep["max_steps"],
            "cumulative_score": aep["cumulative_score"],
            "passing_score": aep["passing_score"],
            "recent_actions": aep["recent_actions"]
        }
        
    return {
        "active_episode": active_payload,
        "completed_episodes": completed,
        "stats": stats
    }
