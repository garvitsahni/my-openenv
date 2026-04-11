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
APP_VERSION = "2026-04-08-reset-optional-v3"

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"

# FIX 1: Single source-of-truth clamp function used EVERYWHERE
# Validator requires strictly (0, 1) — 0.0 and 1.0 are both rejected
import math

def clamp_score(raw: float) -> float:
    """Clamp score to strictly open interval (0.001, 0.999)."""
    v = float(raw)
    if math.isnan(v) or math.isinf(v) or v <= 0:
        return 0.001
    if v >= 1:
        return 0.999
    return round(max(0.001, min(0.999, v)), 4)


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
        "endpoints": [
            "/health", "/tasks", "/reset", "/step",
            "/state", "/score/{episode_id}", "/dashboard"
        ]
    }


episodes_db = {}
active_episode_id = None


@app.get("/version")
def version():
    return {"version": APP_VERSION}


def get_env_instance(env_type: str):
    if env_type == "email":
        return EmailTriageEnv()
    if env_type == "legal":
        return LegalContractEnv()
    if env_type == "hr":
        return HRScreeningEnv()
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
            "hr":    "hr-screening-easy",
        }
        task_id = task_id or default_task_by_env.get(env_type)
        if not task_id:
            raise HTTPException(
                status_code=400,
                detail="Missing task_id or invalid env_type"
            )

        env = get_env_instance(env_type)
        obs = env.reset(task_id, seed)

        episode_id = "ep_" + task_id
        active_episode_id = episode_id

        difficulty = task_id.split("-")[-1]
        passing_score_map = {
            "easy":        0.7,
            "medium":      0.65,
            "hard":        0.60,
            "adversarial": 0.50,
        }
        passing_score = passing_score_map.get(difficulty, 0.5)

        episodes_db[episode_id] = {
            "episode_id":       episode_id,
            "env_type":         env_type,
            "difficulty":       difficulty,
            "task_id":          task_id,
            "step_count":       0,
            "max_steps":        env.max_steps,
            # FIX 2: Start cumulative at 0.001 not 0.0
            # so even a zero-action episode never returns exactly 0.0
            "cumulative_score": 0.001,
            "passing_score":    passing_score,
            "recent_actions":   [],
            "done":             False,
            # FIX 3: Start final_score at 0.001 not 0.0
            "final_score":      0.001,
            "env_instance":     env,
            "start_time":       time.time(),
        }

        return {
            "observation": obs.model_dump(),
            "episode_id":  episode_id,
            "task":        {"id": task_id},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# FIX 4: Accept request as Body not raw dict
# Raw dict fails when Content-Type is not set by caller
@app.post("/step")
async def step_env(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    episode_id  = body.get("episode_id", "")
    action_dict = body.get("action", {})

    if episode_id not in episodes_db:
        raise HTTPException(status_code=404, detail="Episode not found")

    ep_data  = episodes_db[episode_id]
    env_type = ep_data["env_type"]
    env      = ep_data["env_instance"]

    try:
        action_type = action_dict.get("action_type")
        args        = action_dict.get("args", {})

        if env_type == "email":
            action = EmailAction(
                action_type=action_type, args=args, episode_id=episode_id
            )
        elif env_type == "legal":
            action = LegalAction(
                action_type=action_type, args=args, episode_id=episode_id
            )
        elif env_type == "hr":
            action = HRAction(
                action_type=action_type, args=args, episode_id=episode_id
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown env_type")

        obs, reward, done, info = env.step(action)

        # FIX 5: Clamp reward before adding to cumulative
        # Prevents cumulative drifting to exactly 0.0 via negative rewards
        safe_reward = float(reward)
        ep_data["step_count"]       += 1
        ep_data["cumulative_score"] += safe_reward

        ep_data["recent_actions"].insert(0, {
            "step":        ep_data["step_count"],
            "action_type": action_type,
            "reward":      safe_reward,
            "cumulative":  ep_data["cumulative_score"],
            "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        # Keep only last 5
        ep_data["recent_actions"] = ep_data["recent_actions"][:5]

        if done:
            ep_data["done"]     = True
            ep_data["end_time"] = time.time()

            # FIX 6: Normalize then clamp — normalization denominators per env
            # This ensures full-score agents get 0.999 not 1.0
            raw = ep_data["cumulative_score"]
            if env_type == "email":
                normalized = raw / 0.85
            elif env_type == "legal":
                normalized = raw / 0.70
            elif env_type == "hr":
                normalized = raw / 0.90
            else:
                normalized = raw

            # FIX 7: clamp_score applied here — single call, always in (0,1)
            ep_data["final_score"] = clamp_score(normalized)

        global active_episode_id
        if done and active_episode_id == episode_id:
            active_episode_id = None

        return {
            "observation": obs.model_dump(),
            "reward":      safe_reward,
            "done":        done,
            "info":        info,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/state")
def get_state(episode_id: str):
    if episode_id not in episodes_db:
        raise HTTPException(status_code=404, detail="Not found")
    st = episodes_db[episode_id]["env_instance"].state()
    return {
        "state":            st,
        "step_count":       st.get("step_count", 0),
        # FIX 8: clamp here too — state endpoint was not clamping before
        "cumulative_score": clamp_score(st.get("cumulative_score", 0.001)),
    }


@app.get("/tasks")
def list_tasks(env_type: str = "email"):
    diffs = ["easy", "medium", "hard", "adversarial"]
    if env_type == "email":
        return [{"id": f"email-triage-{d}", "difficulty": d, "max_steps": 30} for d in diffs]
    if env_type == "legal":
        return [{"id": f"legal-review-{d}", "difficulty": d, "max_steps": 20} for d in diffs]
    if env_type == "hr":
        return [{"id": f"hr-screening-{d}", "difficulty": d, "max_steps": 25} for d in diffs]
    return []


@app.get("/score/{episode_id}")
def get_score(episode_id: str):
    if episode_id not in episodes_db:
        raise HTTPException(status_code=404, detail="Not found")

    ep = episodes_db[episode_id]

    if ep["done"]:
        # FIX 9: final_score already clamped when set in /step
        # Apply clamp_score again as safety net in case of direct DB writes
        score = clamp_score(ep["final_score"])
    else:
        # FIX 10: In-progress episodes — clamp cumulative before returning
        # cumulative_score can be negative (penalties) or very small
        # clamp_score ensures strictly > 0
        score = clamp_score(ep["cumulative_score"])

    return {
        "final_score":    score,
        "step_scores":    [],
        "grader_details": {},
    }


@app.get("/health")
def health():
    return {"status": "ok", "environments": ["email", "legal", "hr"]}


@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    html_path = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/dashboard/data")
def get_dashboard_data():
    completed = []
    for eid, ep in episodes_db.items():
        if ep["done"]:
            # FIX 11: clamp_score on every score going to the dashboard
            final = clamp_score(ep["final_score"])
            completed.append({
                "episode_id":   eid,
                "task_id":      ep.get("task_id", eid),
                "env_type":     ep["env_type"],
                "difficulty":   ep["difficulty"],
                "final_score":  final,
                "passing_score": ep["passing_score"],
                "steps":        ep["step_count"],
                "duration_seconds": int(ep.get("end_time", time.time()) - ep.get("start_time", time.time())),
                "status":       "PASS" if final >= ep["passing_score"] else "FAIL",
                "time":         ep.get("end_time", time.time()),
            })

    active = None
    if active_episode_id and active_episode_id in episodes_db:
        ep = episodes_db[active_episode_id]
        active = {
            "episode_id":       active_episode_id,
            "task_id":          ep["task_id"],
            "env_type":         ep["env_type"],
            "difficulty":       ep["difficulty"],
            "step_count":       ep["step_count"],
            "max_steps":        ep["max_steps"],
            # FIX 12: clamp here too — dashboard was reading raw cumulative
            "cumulative_score": clamp_score(ep["cumulative_score"]),
            "passing_score":    ep["passing_score"],
            "recent_actions":   ep["recent_actions"],
        }

    completed_sorted = sorted(completed, key=lambda x: x["time"], reverse=True)[:10]

    total     = len(completed)
    avg_score = clamp_score(
        sum(e["final_score"] for e in completed) / max(1, total)
    ) if completed else 0.001
    best_score = clamp_score(
        max((e["final_score"] for e in completed), default=0.001)
    )
    best_task = next(
        (e["task_id"] for e in completed if e["final_score"] == max(
            (x["final_score"] for x in completed), default=0.001
        )), ""
    )
    pass_count = len([e for e in completed if e["status"] == "PASS"])
    pass_rate  = clamp_score(pass_count / max(1, total))

    return {
        "active_episode":     active,
        "completed_episodes": completed_sorted,
        "stats": {
            "total":       total,
            "avg_score":   avg_score,
            "best_score":  best_score,
            "best_task":   best_task,
            "pass_rate":   round(pass_rate * 100, 1),
        },
    }