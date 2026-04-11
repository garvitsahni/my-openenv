---
title: "WorkBench OpenEnv"
emoji: "🚀"
colorFrom: "blue"
colorTo: "indigo"
sdk: "docker"
sdk_version: "0.0.1"
python_version: "3.11"
app_file: "app.py"
pinned: false
---
# WorkBench Multi-Environment Platform

WorkBench is the missing infrastructure layer for AI agent research â€” a community-curated, OpenEnv-compliant library of real-world training environments, each deployable in one click to Hugging Face Spaces.

This repository features THREE highly detailed, real-world simulating endpoints:
- Email Triage
- Legal Contract Review
- HR Resume Screening

It also features **adversarial stress test tasks** across all domains to evaluate LLM overconfidence, bias, and prompt injection vulnerabilities.

## 1. Environment: Email Triage
Navigate a 10-email inbox processing task where the agent must successfully triage standard, urgent, and spam inputs.

### Observation Space
| Field | Type | Description |
|-------|------|-------------|
| `emails` | list[dict] | Array of current email state including id, sender, thread_id, subject, attachments, and body. |
| `step_count` | int | Current steps taken. |
| `available_actions` | list[str] | Actions permitted by the agent in this environment. |

### Action Space
| Action | Required Args | Description |
|--------|---------------|-------------|
| `classify` | `email_id`, `category` | Assess if the email is urgent, normal, spam, or archive. |
| `assign` | `email_id`, `team` | Route the email to a relevant internal team. |
| `escalate` | `email_id`, `escalate` | Raise a critical flag if human intervention is needed. |
| `draft` | `email_id`, `response` | Write a one-sentence reply. |
| `skip` | `email_id` | Skip an email explicitly (fallbacks default to this if unable to parse action). |
| `done` | N/A | Submit the inbox processing as concluded. |


## 2. Environment: Legal Contract Review
Assess complex MSAs, NDAs, and Employee Agreements for harmful clauses, invalid clauses, and broad overreaches.

### Observation Space
| Field | Type | Description |
|-------|------|-------------|
| `contracts` | list[dict] | Array of active contract dictionaries with title, clauses, signature_status, and bodies. |
| `step_count` | int | Current steps taken. |
| `flags_raised` | list[dict] | Array tracking the flags the agent has already successfully identified. |
| `available_actions` | list[str] | Actions permitted by the agent in this environment. |

### Action Space
| Action | Required Args | Description |
|--------|---------------|-------------|
| `identify_type` | `contract_id`, `contract_type` | Identify the formal type of the contract. |
| `assess_risk` | `contract_id`, `risk_level` | Gauge overall high, medium, or low risk explicitly. |
| `flag_clause` | `contract_id`, `clause_id`, `issue`, `severity`, `description`| Call out bad lines. |
| `identify_missing`| `contract_id`, `missing_clause` | Suggest standardized clauses that shouldn't be missing. |
| `recommend`| `contract_id`, `action` | Decide whether to approve, revise, or reject based on flags. |
| `done` | N/A | Submit the review as completed. |


## 3. Environment: HR Resume Screening
Score and filter candidates according to required job listings, penalizing demographic and prestige bias.

### Observation Space
| Field | Type | Description |
|-------|------|-------------|
| `job_description` | dict | Target job parameters required and preferred skills, plus minimum history. |
| `resumes` | list[dict] | Array of current resume dictionaries (applicant logic, experience, skills). |
| `step_count` | int | Current steps taken. |
| `scores_given` | dict | Current applicant grading metrics. |
| `shortlisted` | list[str] | Applicants flagged for moving forward. |
| `available_actions` | list[str] | Actions permitted by the agent in this environment. |

### Action Space
| Action | Required Args | Description |
|--------|---------------|-------------|
| `score_candidate` | `resume_id`, `score`, `reasoning` | Grade applicant visually based on matching text arrays to job desc. |
| `shortlist` | `resume_id` | Admit an applicant to the next round. |
| `flag_bias` | `resume_id`, `bias_type`, `description`| Identify resume bloat, prestige traps, and over/under scaling bias correctly. |
| `rank_shortlist`| `ranking` | Array representing order of top picks. |
| `recommend`| `resume_id`, `decision` | Request to actively interview or decisively reject an applicant. |
| `done` | N/A | Finish screening. |

## Feature: Live Live Score Dashboard
View `/dashboard` natively in your browser to watch the agent reason through real-time grading, complete with Action tables, cumulative score progression, pie bar charts, and passing percentage heuristics across all domains seamlessly hosted on one page logic. No external CSS. No NPM dependencies. Fully OpenEnv specific!

## Adversarial Evaluation 
Provides `.json` tests capable of catching LLM over-syllogisms, blind obedience against prompt-injection (Ex: Fake systemic override), fake AI titles, and missing implicit details.

## Setup Instructions
```bash
docker build -t workbench .
docker run -p 7860:7860 workbench
```

## Python Client (Requests)
```python
import requests
obs = requests.post("http://localhost:7860/reset?env_type=hr", json={"task_id": "hr-screening-adversarial"}).json()
print("Observation: ", obs)
```



