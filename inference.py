import os
import json
import time
import re
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

try:
    import litellm
except ImportError:
    litellm = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


SERVER_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini/gemini-2.0-flash")

TASKS = [
    ("email-triage-easy", "email"),
    ("email-triage-medium", "email"),
    ("email-triage-hard", "email"),
    ("email-triage-adversarial", "email"),
    ("legal-review-easy", "legal"),
    ("legal-review-medium", "legal"),
    ("legal-review-hard", "legal"),
    ("legal-review-adversarial", "legal"),
    ("hr-screening-easy", "hr"),
    ("hr-screening-medium", "hr"),
    ("hr-screening-hard", "hr"),
    ("hr-screening-adversarial", "hr"),
]

# FIX 1: Added flush=True to every print so validator can read stdout in real time
def emit_block(tag: str, data: dict):
    try:
        print(f"{tag} {json.dumps(data)}", flush=True)
    except Exception:
        pass


def _build_url(path: str) -> str:
    return f"{SERVER_URL.rstrip('/')}{path}"


def _http_request(
    method: str,
    path: str,
    payload: dict | None = None,
    timeout: float = 30.0,
) -> tuple[int, str, dict[str, Any] | None]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urlrequest.Request(
        _build_url(path), data=body, headers=headers, method=method
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text) if text else None
            except json.JSONDecodeError:
                parsed = None
            return resp.status, text, parsed
    except urlerror.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        return e.code, text, None
    except Exception as e:
        return 0, str(e), None


def parse_action(raw_text: str) -> dict | None:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    return None


def validate_action(parsed: dict, env_type: str) -> bool:
    if "action_type" not in parsed:
        return False
    act = parsed["action_type"]

    if env_type == "email":
        allowed = ["classify", "assign", "escalate", "draft", "skip", "done"]
    elif env_type == "legal":
        allowed = ["identify_type", "assess_risk", "flag_clause", "identify_missing", "recommend", "done"]
    elif env_type == "hr":
        allowed = ["score_candidate", "shortlist", "flag_bias", "rank_shortlist", "recommend", "done"]
    else:
        return False

    return act in allowed


def call_with_retry(model: str, prompt: str, env_type: str, max_retries: int = 3) -> dict:
    current_prompt = prompt
    
    api_key = os.environ.get("API_KEY", "")
    api_base = os.environ.get("API_BASE_URL", "")
    
    for _ in range(max_retries):
        try:
            if litellm:
                if api_key:
                    litellm.api_key = api_key
                if api_base:
                    litellm.api_base = api_base
                    
                response = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": current_prompt}],
                    temperature=0.0,
                )
                raw = response.choices[0].message.content or ""
            else:
                import openai
                client = openai.OpenAI(
                    api_key=api_key or "dummy-key",
                    base_url=api_base if api_base else None
                )
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": current_prompt}],
                    temperature=0.0,
                )
                raw = response.choices[0].message.content or ""
            parsed = parse_action(raw)
            if parsed and validate_action(parsed, env_type):
                return parsed
            current_prompt += "\n[SYSTEM: Failed to parse valid JSON. Ensure strict schema match.]"
        except Exception as e:
            current_prompt += f"\n[SYSTEM: API Error: {e}]"

    # Safe fallbacks per env type
    if env_type == "email":
        return {"action_type": "done", "args": {}}
    elif env_type == "legal":
        return {"action_type": "done", "args": {}}
    elif env_type == "hr":
        return {"action_type": "done", "args": {}}
    return {"action_type": "done", "args": {}}


def _proxy_chat_url() -> str:
    base = os.environ.get("API_BASE_URL", "")
    if base.endswith("/"):
        base = base[:-1]
    if base.endswith("/chat/completions"):
        return base
    if base:
        return f"{base}/chat/completions"
    return ""


def ensure_proxy_call(model: str) -> None:
    api_key = os.environ.get("API_KEY", "").strip()
    chat_url = _proxy_chat_url()
    try:
        if api_key and chat_url:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with ok"}],
                "temperature": 0.0,
                "max_tokens": 4,
            }
            req = urlrequest.Request(
                chat_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=20):
                pass
            return
    except Exception:
        pass

    try:
        api_base = os.environ.get("API_BASE_URL", "")
        if litellm:
            if api_key:
                litellm.api_key = api_key
            if api_base:
                litellm.api_base = api_base
            litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Return exactly: ok"}],
                temperature=0.0,
                max_tokens=4,
            )
        else:
            import openai
            client = openai.OpenAI(
                api_key=api_key or "dummy-key",
                base_url=api_base if api_base else None
            )
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Return exactly: ok"}],
                temperature=0.0,
                max_tokens=4,
            )
    except Exception:
        pass


def build_prompt(obs: dict, history: list, env_type: str) -> str:
    prompt = f"OBSERVATION:\n{json.dumps(obs, indent=2)}\n\nHISTORY (last 3):\n"
    for h in history[-3:]:
        prompt += f"- {json.dumps(h)}\n"

    if env_type == "email":
        prompt += """\nYou are an email triage agent. Respond with ONLY a single JSON object, no other text:
{"action_type": "<classify|assign|escalate|draft|skip|done>", "args": { ... }}
For classify: args = {"email_id": "email_001", "category": "urgent|normal|spam|archive"}
For assign: args = {"email_id": "email_001", "team": "engineering|sales|support|exec"}
For escalate: args = {"email_id": "email_001", "escalate": true}
For draft: args = {"email_id": "email_001", "response": "one sentence"}
For skip: args = {"email_id": "email_001"}
For done: args = {}"""
    elif env_type == "legal":
        prompt += """\nYou are a legal contract review agent. Respond with ONLY a single JSON object, no other text:
{"action_type": "<identify_type|assess_risk|flag_clause|identify_missing|recommend|done>", "args": { ... }}
For identify_type: args = {"contract_id": "contract_001", "contract_type": "nda|vendor_agreement|employment_agreement|other"}
For assess_risk: args = {"contract_id": "contract_001", "risk_level": "low|medium|high"}
For flag_clause: args = {"contract_id": "contract_001", "clause_id": "clause_3", "issue": "short_issue_name", "severity": "critical|high|medium", "description": "one sentence"}
For identify_missing: args = {"contract_id": "contract_001", "missing_clause": "clause_name"}
For recommend: args = {"contract_id": "contract_001", "action": "approve|revise|reject"}
For done: args = {}"""
    elif env_type == "hr":
        prompt += """\nYou are an HR screening agent. Respond with ONLY a single JSON object, no other text:
{"action_type": "<score_candidate|shortlist|flag_bias|rank_shortlist|recommend|done>", "args": { ... }}
For score_candidate: args = {"resume_id": "resume_001", "score": 8, "reasoning": "one sentence"}
For shortlist: args = {"resume_id": "resume_001"}
For flag_bias: args = {"resume_id": "resume_001", "bias_type": "education_bias|prestige_bias|credential_inflation|title_inflation", "description": "one sentence"}
For rank_shortlist: args = {"ranking": ["resume_001", "resume_003"]}
For recommend: args = {"resume_id": "resume_001", "decision": "interview|reject"}
For done: args = {}"""
    return prompt


def run_task(task_id: str, env_type: str) -> None:
    # FIX 2: Emit [START] block — validator requires this before any [STEP] blocks
    emit_block("[START]", {"task": task_id, "env": env_type})

    print(f"--- Running {task_id} ({env_type}) ---", flush=True)

    status_code, text, data = _http_request(
        "POST", f"/reset?env_type={env_type}", {"task_id": task_id, "seed": 42}
    )
    if status_code != 200 or not isinstance(data, dict):
        print(f"Failed to reset: {text}", flush=True)
        # FIX 3: Still emit [END] even on reset failure so validator doesn't hang
        emit_block("[END]", {"task": task_id, "env": env_type, "score": 0.001, "steps": 0, "status": "reset_failed"})
        return

    obs = data.get("observation", {})
    episode_id = data.get("episode_id", "ep_001")

    done = False
    history = []
    step = 0
    cum_score = 0.0

    try:
        # FIX 4: Open log file in append mode outside the loop — prevents repeated open/close
        log_file = open("episode_log.jsonl", "a", encoding="utf-8")
    except Exception:
        log_file = None

    try:
        while not done:
            step += 1
            try:
                prompt = build_prompt(obs, history, env_type)
                action = call_with_retry(MODEL_NAME, prompt, env_type)

                step_status, step_text, sdata = _http_request(
                    "POST", "/step", {"episode_id": episode_id, "action": action}
                )
                if step_status != 200 or not isinstance(sdata, dict):
                    print(f"FAILED STEP: {step_text} using {action}", flush=True)
                    break

                obs = sdata.get("observation", {})
                reward = sdata.get("reward", 0.0)
                done = sdata.get("done", True)
                cum_score += reward

                log = {
                    "episode_id": episode_id,
                    "env_type": env_type,
                    "step": step,
                    "action_type": action.get("action_type"),
                    "reward": reward,
                    "cumulative": cum_score,
                    "raw_preview": str(action)[:100],
                }

                if log_file:
                    log_file.write(json.dumps(log) + "\n")
                    log_file.flush()  # FIX 5: Flush log file after every write

                history.append(log)

                # FIX 6: [STEP] block printed with flush=True via emit_block (already fixed above)
                emit_block("[STEP]", {
                    "task": task_id,
                    "env": env_type,
                    "step": step,
                    "action": action.get("action_type", "unknown"),
                    "reward": reward,
                    "score": cum_score,
                    "done": done,
                })

            except Exception as eval_e:
                print(f"Error during eval tick: {eval_e}", flush=True)
                done = True

    finally:
        if log_file:
            log_file.close()

    final_score = {"final_score": cum_score}
    try:
        score_status, _, fsc = _http_request("GET", f"/score/{episode_id}", None)
        if score_status == 200 and isinstance(fsc, dict) and "final_score" in fsc:
            final_score = fsc
    except Exception:
        pass

    # FIX 7: [END] block always emitted with flush=True
    raw_score = final_score.get("final_score", 0.001)
    safe_score = min(max(float(raw_score), 0.001), 0.999)
    emit_block("[END]", {
        "task": task_id,
        "env": env_type,
        "score": safe_score,
        "steps": step,
        "status": "ok",
    })


if __name__ == "__main__":
    start = time.time()

    try:
        ensure_proxy_call(MODEL_NAME)
    except Exception as e:
        print(f"ensure_proxy_call failed: {e}", flush=True)

    for t_id, t_env in TASKS:
        try:
            run_task(t_id, t_env)
        except Exception as e:
            print(f"run_task {t_id} failed: {e}", flush=True)
            # FIX 8: Emit [END] even if run_task itself throws so validator never hangs
            emit_block("[END]", {"task": t_id, "env": t_env, "score": 0.001, "steps": 0, "status": "error"})
        time.sleep(2)

    print(f"Total runtime: {time.time() - start:.2f}s", flush=True)