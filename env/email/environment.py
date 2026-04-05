import json
import os
from typing import Any
from .models import EmailAction, EmailObservation, Email
from .grader import EmailTriageGrader

class EmailTriageEnv:
    def __init__(self):
        self.grader = EmailTriageGrader()
        self.emails: list[dict[str, Any]] = []
        self.ground_truth: dict[str, dict[str, Any]] = {}
        self.step_count = 0
        self.max_steps = 30
        self.cumulative_score = 0.0
        self.task_id = ""
        self.available_actions = ["classify", "assign", "escalate", "draft", "skip", "done"]

    def reset(self, task_id: str, seed: int = 42) -> EmailObservation:
        self.task_id = task_id
        self.step_count = 0
        self.cumulative_score = 0.0
        
        # Load from tasks directory
        difficulty = task_id.split("-")[-1]
        task_path = os.path.join(os.path.dirname(__file__), "..", "..", "tasks", f"email_{difficulty}.json")
        if not os.path.exists(task_path):
            raise FileNotFoundError(f"Task file not found: {task_path}")
            
        with open(task_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.emails = data["emails"]
        self.ground_truth = data["ground_truth"]
        self.max_steps = data["metadata"]["max_steps"]
        
        return self._get_obs()

    def _get_obs(self) -> EmailObservation:
        return EmailObservation(
            emails=[Email(**e) for e in self.emails],
            step_count=self.step_count,
            remaining_steps=self.max_steps - self.step_count,
            available_actions=self.available_actions,
            context={}
        )

    def step(self, action: EmailAction) -> tuple[EmailObservation, float, bool, dict]:
        self.step_count += 1
        
        if action.action_type == "done" or self.step_count >= self.max_steps:
            return self._get_obs(), 0.0, True, {"msg": "Max steps reached" if self.step_count >= self.max_steps else "Agent finished"}

        reward = 0.0
        if 'email_id' in action.args:
            email_id = action.args["email_id"]
            if email_id in self.ground_truth:
                gt = self.ground_truth[email_id]
                grader_res = self.grader.score_action(action.action_type, action.args, email_id, gt)
                reward = grader_res.score
                self.cumulative_score += reward

        # Remove email if skip is called just so we simulate processing
        if action.action_type == "skip" and 'email_id' in action.args:
             self.emails = [e for e in self.emails if e["id"] != action.args["email_id"]]

        return self._get_obs(), reward, False, {"action": action.action_type}

    def state(self) -> dict:
        return {
            "task": self.task_id,
            "step_count": self.step_count,
            "cumulative_score": self.cumulative_score,
            "emails_remaining": len(self.emails)
        }
