from typing import Any
from .models import LegalGraderResult

SCORE_CORRECT_CONTRACT_TYPE = 0.10
SCORE_CORRECT_RISK_LEVEL = 0.15
SCORE_CRITICAL_FLAG_FOUND = 0.20
SCORE_HIGH_FLAG_FOUND = 0.10
SCORE_MISSING_CLAUSE_FOUND = 0.05
SCORE_CORRECT_RECOMMENDATION = 0.15
PENALTY_MISSED_CRITICAL_FLAG = -0.15
PENALTY_FALSE_CRITICAL_FLAG = -0.10
PENALTY_WRONG_RECOMMENDATION = -0.10
PENALTY_SEQUENCING = -0.05

PENALTY_FALSE_POSITIVE_CRITICAL = -0.20
BONUS_CLEAN_CONTRACT_APPROVED = 0.20

class LegalContractGrader:
    def score_action(self, action_type: str, args: dict[str, Any], contract_id: str, ground_truth: dict[str, Any]) -> LegalGraderResult:
        score = 0.0
        criteria_met = []
        trap = ground_truth.get("adversarial_trap")

        if action_type == "identify_type":
            if args.get("contract_type") == ground_truth.get("contract_type"):
                score += SCORE_CORRECT_CONTRACT_TYPE
                criteria_met.append("Correct contract type")
        elif action_type == "assess_risk":
            if args.get("risk_level") == ground_truth.get("risk_level"):
                score += SCORE_CORRECT_RISK_LEVEL
                criteria_met.append("Correct risk level")
        elif action_type == "flag_clause":
            found = False
            for flag in ground_truth.get("critical_flags", []):
                if args.get("clause_id") == flag["clause_id"]:
                    score += SCORE_CRITICAL_FLAG_FOUND
                    criteria_met.append(f"Found critical flag: {flag['issue']}")
                    found = True
                    break
            if not found:
                for flag in ground_truth.get("high_flags", []):
                    if args.get("clause_id") == flag["clause_id"]:
                        score += SCORE_HIGH_FLAG_FOUND
                        criteria_met.append(f"Found high flag: {flag['issue']}")
                        found = True
                        break
            if not found and args.get("severity") == "critical":
                score += PENALTY_FALSE_CRITICAL_FLAG
                criteria_met.append("False critical flag")
                if trap is not None:
                    score += PENALTY_FALSE_POSITIVE_CRITICAL
                    criteria_met.append("Adversarial false positive on critical")
                
        elif action_type == "identify_missing":
            if args.get("missing_clause") in ground_truth.get("missing_clauses", []):
                score += SCORE_MISSING_CLAUSE_FOUND
                criteria_met.append("Found missing clause")
                
        elif action_type == "recommend":
            if args.get("action") == ground_truth.get("recommend_action"):
                score += SCORE_CORRECT_RECOMMENDATION
                criteria_met.append("Correct recommendation")
                if trap is not None and ground_truth.get("recommend_action") == "approve":
                     score += BONUS_CLEAN_CONTRACT_APPROVED
                     criteria_met.append("Bonus: Clean contract approved")
            else:
                score += PENALTY_WRONG_RECOMMENDATION
                criteria_met.append("Wrong recommendation")

        return LegalGraderResult(
            score=score,
            breakdown={"action": action_type, "reward": score},
            criteria_met=criteria_met,
            max_possible=0.60
        )

    def score_episode(self, step_results: list[LegalGraderResult]) -> float:
        total = sum(r.score for r in step_results)
        return max(0.001, min(0.999, total))
