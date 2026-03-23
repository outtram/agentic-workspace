---
id: OUT-363
title: Story Point Estimator — ML Model from Historical Data
type: prd
status: draft
priority: high
created: 2026-03-23
updated: 2026-03-23
assignee: Troy
branch: feature/OUT-363-story-point-estimator
---

# Story Point Estimator — ML Model from Historical Data

## Problem

Estimating story points for catalogue items is subjective and inconsistent. With 3 years of real-world delivery data sitting across Confluence, Jira, and GitHub, we can build a model that predicts story points based on historical patterns — grounding estimates in evidence, not gut feel.

## Goals

1. Extract and normalise 3 years of delivery data from Confluence, Jira, and GitHub
2. Train a model that predicts story points from ticket/catalogue item features
3. Build a catalogue of items with evidence-based effort estimates
4. Deploy to client environment for ongoing refinement
5. Enable developers to generate estimates during planning sessions

## Non-Goals

- Replacing human judgement entirely — this augments, not replaces
- Real-time prediction during ticket creation (future phase)
- Cross-organisation model — this is trained on YOUR data only

---

## Phase 1: Data Extraction

### Developer Instructions

Each system needs a data export. Developers should extract the following:

#### Jira Export
```
Fields needed per ticket:
- Key, Summary, Description, Story Points (actual)
- Issue Type, Priority, Labels, Components
- Sprint, Epic Link
- Created Date, Resolved Date
- Status transitions (time in each status)
- Subtask count and their story points
- Assignee (anonymised to team/role)
- Comment count, attachment count
```

**Method:** Jira REST API or CSV export. Script should paginate through all projects.

```bash
# Example: Jira API extraction (developers to adapt)
curl -u user:token "https://yourinstance.atlassian.net/rest/api/3/search?jql=project=PROJ&maxResults=100&startAt=0" \
  --header "Accept: application/json"
```

#### Confluence Export
```
Fields needed per page:
- Page ID, Title, Space Key
- Content length (words/characters)
- Number of child pages
- Labels/tags
- Created Date, Last Modified Date
- Number of versions (revision count)
- Linked Jira tickets (via Jira macro references)
```

**Method:** Confluence REST API. Parse page bodies for Jira macros to link documentation to tickets.

#### GitHub Export
```
Fields needed per PR:
- PR number, Title, Description length
- Files changed count, Lines added, Lines deleted
- Number of commits
- Number of review comments
- Time to merge (created → merged)
- Linked Jira ticket (from branch name or PR title)
- CI/CD pass/fail count before merge
```

**Method:** GitHub GraphQL API or `gh` CLI.

```bash
# Example: GitHub PR extraction
gh pr list --repo org/repo --state merged --limit 1000 --json number,title,additions,deletions,changedFiles,commits,createdAt,mergedAt
```

### Output Format

All exports should produce **CSV or JSONL** files with consistent date formats (ISO 8601). One file per system:

```
data/raw/jira_export.csv
data/raw/confluence_export.csv
data/raw/github_export.csv
```

---

## Phase 2: Feature Engineering

### Derived Features

| Feature | Source | Description |
|---------|--------|-------------|
| description_length | Jira | Word count of description |
| description_embedding | Jira | Vector embedding of summary + description |
| component_category | Jira | Encoded component/label |
| has_subtasks | Jira | Boolean + count |
| epic_avg_points | Jira | Historical avg points for that epic |
| team_velocity | Jira | Avg points/sprint for assignee's team |
| doc_pages_linked | Confluence | Count of linked Confluence pages |
| doc_complexity | Confluence | Total word count of linked docs |
| similar_ticket_avg | Jira | Avg points of semantically similar past tickets |
| historical_pr_size | GitHub | Avg lines changed for similar past work |
| cycle_time_category | Jira | Binned historical cycle time |

### Text Embeddings

Use Claude API or a local embedding model to generate embeddings from Jira ticket descriptions. These become the most powerful features for finding "similar past work."

---

## Phase 3: Model Training

### Approach

Start simple, add complexity only if needed:

1. **Baseline:** XGBoost on tabular features (no text) — establish floor
2. **+ Embeddings:** Add description embeddings as features — likely biggest lift
3. **+ Ensemble:** If needed, blend with a fine-tuned text model

### Target Variable

- Story points (as reported in Jira)
- Consider binning into categories (XS/S/M/L/XL) if point scales are inconsistent

### Validation

- Train on first 2.5 years, validate on last 6 months
- Metrics: MAE, RMSE, and accuracy-within-1-point
- Compare against team average as baseline

---

## Phase 4: Mock Data

For development and testing before real data arrives:

### Mock Data Generator

Build a script that generates realistic synthetic data:

```python
# mock_data_generator.py
# Generates synthetic Jira/Confluence/GitHub data
# with realistic correlations:
# - longer descriptions → more points
# - more components → more points
# - larger PRs → more points
# - add noise to prevent overfitting to fake patterns
```

This lets us:
- Build and test the full pipeline before client data access
- Demo the system to stakeholders
- Test edge cases (missing fields, outliers, zero-point tickets)

---

## Phase 5: Client Deployment

### Requirements

- Package as a standalone Python project (venv + requirements.txt)
- No external API calls from client environment (embeddings pre-computed or local model)
- CLI interface for batch predictions and single-ticket estimates
- Export catalogue to CSV/Excel for stakeholder review

### Catalogue Output

```
catalogue/
├── estimates.csv          # All items with predicted points + confidence
├── model_report.html      # Model performance metrics + charts
└── similar_items.json     # For each item, top-5 similar historical tickets
```

---

## Phase 6: Refinement Loop

- Retrain monthly as new tickets are completed
- Track prediction accuracy over time
- Flag tickets where actual ≠ predicted by >3 points for retrospective review

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Data extraction | Python scripts + Jira/Confluence/GitHub APIs |
| Feature engineering | pandas, scikit-learn |
| Embeddings | Claude API (or sentence-transformers for offline) |
| Model | XGBoost (primary), scikit-learn (baselines) |
| Evaluation | matplotlib, scikit-learn metrics |
| Deployment | Python CLI, pip-installable package |
| Mock data | Faker + custom generators |

---

## Acceptance Criteria

- [ ] Data extraction scripts for all 3 systems with clear developer instructions
- [ ] Mock data generator that produces realistic synthetic data
- [ ] Trained model achieving <2 MAE on story point prediction
- [ ] Catalogue output with estimates + confidence intervals
- [ ] Deployable to client environment with no external dependencies
- [ ] Documentation for developers on how to run extraction scripts
- [ ] Refinement pipeline for monthly retraining

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Inconsistent story pointing across teams | Normalise by team, or train per-team models |
| Too little data for some categories | Fall back to team/component averages |
| Client environment restrictions | Pre-compute embeddings, bundle all deps |
| Data privacy | All processing on client infra, no data leaves environment |
