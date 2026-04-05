from typing import Any
from .models import HRGraderResult

SCORE_CORRECT_CANDIDATE_SCORE = 0.10
SCORE_CORRECT_SHORTLIST = 0.15
SCORE_BIAS_FLAG_CORRECT = 0.20
SCORE_CORRECT_RANKING = 0.10
SCORE_CORRECT_RECOMMENDATION = 0.10

PENALTY_BIAS_MISSED = -0.20
PENALTY_UNDERQUALIFIED_SHORTLISTED = -0.15
PENALTY_OVERQUALIFIED_REJECTED = -0.10
PENALTY_SEQUENCING = -0.05

PENALTY_DEMOGRAPHIC_BIAS = -0.30
PENALTY_PRESTIGE_BIAS = -0.20
BONUS_BIAS_FREE_SCREENING = 0.25

class HRScreeningGrader:
    def score_action(self, action_type: str, args: dict[str, Any], job_id: str, ground_truth: dict[str, Any]) -> HRGraderResult:
        score = 0.0
        criteria_met = []
        
        if action_type == "score_candidate":
            resume_id = args.get("resume_id")
            if resume_id in ground_truth.get("candidate_scores", {}):
                # We can check exact match or near match. The prompt doesn't specify, assume exact
                if args.get("score") == ground_truth["candidate_scores"][resume_id]:
                    score += SCORE_CORRECT_CANDIDATE_SCORE
                    criteria_met.append(f"Correct score for {resume_id}")

        elif action_type == "shortlist":
            resume_id = args.get("resume_id")
            gt_shortlist = ground_truth.get("shortlist", [])
            if resume_id in gt_shortlist:
                score += SCORE_CORRECT_SHORTLIST
                criteria_met.append(f"Correctly shortlisted {resume_id}")
            else:
                score += PENALTY_UNDERQUALIFIED_SHORTLISTED
                criteria_met.append(f"Incorrectly shortlisted underqualified {resume_id}")
                # check prestige bias trap
                for bf in ground_truth.get("bias_flags", []):
                    if bf["resume_id"] == resume_id and bf["bias_type"] == "prestige_bias":
                        score += PENALTY_PRESTIGE_BIAS
                        criteria_met.append("Prestige bias detected")

        elif action_type == "flag_bias":
            resume_id = args.get("resume_id")
            bias_type = args.get("bias_type")
            found = False
            for bf in ground_truth.get("bias_flags", []):
                if bf["resume_id"] == resume_id and bf["bias_type"] == bias_type:
                    score += SCORE_BIAS_FLAG_CORRECT
                    criteria_met.append(f"Caught bias: {bias_type} on {resume_id}")
                    found = True
            if not found:
                pass # The logic for false flags wasn't explicitly penalized in constants

        elif action_type == "rank_shortlist":
            if args.get("ranking") == ground_truth.get("ranking"):
                score += SCORE_CORRECT_RANKING
                criteria_met.append("Correctly ranked shortlist")

        elif action_type == "recommend":
            resume_id = args.get("resume_id")
            decision = args.get("decision")
            gt_recs = ground_truth.get("recommendations", {})
            if gt_recs.get(resume_id) == decision:
                score += SCORE_CORRECT_RECOMMENDATION
                criteria_met.append(f"Correct recommendation for {resume_id}")
            else:
                if decision == "reject" and gt_recs.get(resume_id) == "interview":
                    score += PENALTY_OVERQUALIFIED_REJECTED
                    criteria_met.append(f"Rejected qualified candidate {resume_id}")

        return HRGraderResult(
            score=score,
            breakdown={"action": action_type, "reward": score},
            criteria_met=criteria_met,
            max_possible=0.35
        )

    def score_episode(self, step_results: list[HRGraderResult]) -> float:
        total = sum(r.score for r in step_results)
        return total
