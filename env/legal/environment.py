import json
import os
from typing import Any
from .models import LegalAction, LegalObservation, Contract
from .grader import LegalContractGrader, PENALTY_SEQUENCING, PENALTY_MISSED_CRITICAL_FLAG

class LegalContractEnv:
    def __init__(self):
        self.grader = LegalContractGrader()
        self.contracts: list[dict[str, Any]] = []
        self.ground_truth: dict[str, dict[str, Any]] = {}
        self.step_count = 0
        self.max_steps = 20
        self.cumulative_score = 0.0
        self.task_id = ""
        self.available_actions = ["identify_type", "assess_risk", "flag_clause", "identify_missing", "recommend", "done"]
        
        self.flags_raised = []
        self._seq_identify = False
        self._seq_assess = False

    def reset(self, task_id: str, seed: int = 42) -> LegalObservation:
        self.task_id = task_id
        self.step_count = 0
        self.cumulative_score = 0.0
        self.flags_raised = []
        self._seq_identify = False
        self._seq_assess = False
        
        # Load from tasks directory
        difficulty = task_id.split("-")[-1]
        task_path = os.path.join(os.path.dirname(__file__), "..", "..", "tasks", f"legal_{difficulty}.json")
        if not os.path.exists(task_path):
            raise FileNotFoundError(f"Task file not found: {task_path}")
            
        with open(task_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.contracts = data["contracts"]
        self.ground_truth = data["ground_truth"]
        self.max_steps = data["metadata"]["max_steps"]
        
        return self._get_obs()

    def _get_obs(self) -> LegalObservation:
        return LegalObservation(
            contracts=[Contract(**c) for c in self.contracts],
            step_count=self.step_count,
            remaining_steps=self.max_steps - self.step_count,
            available_actions=self.available_actions,
            flags_raised=self.flags_raised
        )

    def step(self, action: LegalAction) -> tuple[LegalObservation, float, bool, dict]:
        self.step_count += 1
        
        if action.action_type == "done" or self.step_count >= self.max_steps:
            return self._get_obs(), 0.0, True, {"msg": "Max steps reached" if self.step_count >= self.max_steps else "Agent finished"}

        reward = 0.0
        
        # Sequencing penalty checks
        if action.action_type == "identify_type":
            self._seq_identify = True
        elif action.action_type == "assess_risk":
            if not self._seq_identify:
                reward += PENALTY_SEQUENCING
            self._seq_assess = True
        elif action.action_type == "recommend":
            if not self._seq_assess:
                reward += PENALTY_SEQUENCING
            
            # Check for missed critical flags upon recommendation
            if "contract_id" in action.args:
                cid = action.args["contract_id"]
                gt = self.ground_truth.get(cid, {})
                for cflag in gt.get("critical_flags", []):
                    found = any(f.get("clause_id") == cflag["clause_id"] for f in self.flags_raised)
                    if not found:
                        reward += PENALTY_MISSED_CRITICAL_FLAG

        if 'contract_id' in action.args:
            contract_id = action.args["contract_id"]
            if contract_id in self.ground_truth:
                gt = self.ground_truth[contract_id]
                grader_res = self.grader.score_action(action.action_type, action.args, contract_id, gt)
                reward += grader_res.score
                self.cumulative_score += reward
                
                if action.action_type == "flag_clause":
                    self.flags_raised.append(action.args)

        return self._get_obs(), reward, False, {"action": action.action_type}

    def state(self) -> dict:
        return {
            "task": self.task_id,
            "step_count": self.step_count,
            "cumulative_score": self.cumulative_score,
            "flags_raised": len(self.flags_raised)
        }
