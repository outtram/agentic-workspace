---
id: OUT-363
title: Story Point Estimator — ML Model from Historical Data
type: task
status: todo
priority: high
created: 2026-03-23
updated: '2026-03-23'
assignee: Troy
branch: feature/OUT-363-story-point-estimator
source: manual
reminder_id: ""
reminder_list: ""
due_date: ""
eisenhower_quadrant: q2
eisenhower_urgent: false
eisenhower_important: true
category: tech
prd: OUT-363
tags: [ml, data, client, estimation]
enriched: true
---

# Story Point Estimator — ML Model from Historical Data

## Description
Build a data-backed story point estimator using historical Jira, Confluence, and GitHub delivery data so estimates can be generated with confidence scores instead of gut feel.

## Why
3 years of real delivery data across Confluence, Jira, and GitHub can train a model to predict story points based on evidence, not gut feel. Builds a catalogue of items with data-backed estimates.

## What
- Extract historical data from Jira, Confluence, GitHub (developer-driven)
- Feature engineering + text embeddings
- Train XGBoost model on tabular + embedding features
- Generate mock data for dev/testing
- Deploy to client environment
- Build catalogue with estimates + confidence

## Acceptance Criteria
- [ ] Data extraction scripts with developer instructions
- [ ] Mock data generator for development
- [ ] Model achieving <2 MAE on story points
- [ ] Catalogue output (CSV + report)
- [ ] Deployable to client environment (no external deps)
- [ ] Monthly retraining pipeline

## References
- PRD: `.claude/work/prd/OUT-363-story-point-estimator.md`
- Neural Networks From Scratch repo: `temp/downloads/Neural-Networks-From-Scratch.zip` (inspiration, not used directly)

## Progress Log
- 2026-03-23: Enriched in batch review. Preserved existing detail and replaced placeholders where needed.
