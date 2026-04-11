import json
import logging
import os
from fastapi import Body, FastAPI, HTTPException, Request
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
APP_VERSION = "2026-04-08-reset-optional-v2"

# Keep browser console clean by sending a modern Permissions-Policy.
# Deprecated/unknown directives can trigger noisy warnings in Chromium.
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Permissions-Policy"] = PERMISSIONS_POLICY
    return response


@app.get("/")
def root():
    return {
        "name": "WorkBench OpenEnv API",
        "status": "running",
        "version": APP_VERSION,
        "endpoints": ["/health", "/tasks", "/reset", "/step", "/state", "/score/{episode_id}", "/dashboard"]
    }


# In-memory episode tracking for the dashboard
# Format: {"ep_id": {"env_type": "email", "difficulty": "easy", "step_count": 0, "max_steps": 30, "cumulative_score": 0.0, "passing_score": 0.5, "recent_actions": [], "done": False, "final_score": 0.0}}
episodes_db = {}
active_episode_id = None

@app.get("/version")
def version():
    return {"version": APP_VERSION}

def get_env_instance(env_type):
    if env_type == "email": return EmailTriageEnv()
    if env_type == "legal": return LegalContractEnv()
    if env_type == "hr": return HRScreeningEnv()
    raise HTTPException(status_code=400, detail="Invalid env_type")

@app.post("/reset")
def reset_env(
    env_type: str = "email",
    task_id: str | None = None,
    seed: int = 42,
    body: dict | None = Body(default=None),
):
    global active_episode_id
    try:
        if body:
            task_id = body.get("task_id", task_id)
            seed = body.get("seed", seed)

        default_task_by_env = {
            "email": "email-triage-easy",
            "legal": "legal-review-easy",
            "hr": "hr-screening-easy",
        }
        task_id = task_id or default_task_by_env.get(env_type)
        if not task_id:
            raise HTTPException(status_code=400, detail="Missing task_id or invalid env_type")

        env = get_env_instance(env_type)
        obs = env.reset(task_id, seed)
        
        episode_id = "ep_" + task_id
        active_episode_id = episode_id
        
        difficulty = task_id.split("-")[-1]
        passing_score = 0.5 # default
        if difficulty == "easy": passing_score = 0.7
        elif difficulty == "medium": passing_score = 0.65
        elif difficulty == "hard": passing_score = 0.60
            
        episodes_db[episode_id] = {
            "episode_id": episode_id,
            "env_type": env_type,
            "difficulty": difficulty,
            "task_id": task_id,
            "step_count": 0,
            "max_steps": env.max_steps,
            "cumulative_score": 0.0,
            "passing_score": passing_score,
            "recent_actions": [],
            "done": False,
            "final_score": 0.0,
            "env_instance": env
        }
        
        return {"observation": obs.model_dump(), "episode_id": episode_id, "task": {"id": task_id}}
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
                final_score = max(0.001, min(0.999, ep_data["cumulative_score"] / 0.85))
            elif env_type == "legal":
                final_score = max(0.001, min(0.999, ep_data["cumulative_score"] / 0.70))
            elif env_type == "hr":
                final_score = max(0.001, min(0.999, ep_data["cumulative_score"] / 0.90))
            else:
                final_score = max(0.001, min(0.999, ep_data["cumulative_score"]))
            
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
        raw_score = episodes_db[episode_id]["final_score"] if episodes_db[episode_id]["done"] else episodes_db[episode_id]["cumulative_score"]
        score = max(0.001, min(0.999, raw_score))
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
            "avg_score": round(avg_score, 2),
            "best_score": round(best_score, 2),
            "pass_rate": round(pass_rate, 1)
        }
    }
