---
id: OUT-348
title: LinkedIn Connection Scraper — Partner Network Database
type: task
status: todo
priority: medium
created: '2026-03-14'
updated: '2026-03-14'
tags: [side-quest, scraping, data, linkedin]
---

# LinkedIn Connection Scraper

## Summary
Build an agentic tool to scrape first-degree LinkedIn connections for ~30 partners, store in a structured database, export to spreadsheet, and run fuzzy matching against a target stakeholder list.

## Deliverables

1. **Connection Database** — SQLite with 3 tables:
   - `partners` (id, name, session, linkedin_url)
   - `connections` (id, partner_id, full_name, job_title, employer, linkedin_url, date_extracted)
   - `matches` (id, connection_id, stakeholder_name, stakeholder_title, stakeholder_employer, confidence_score, matched_by)

2. **Spreadsheet Export** — CLI command to dump connections to CSV/XLSX, filterable by partner and employer. Clean, no manual fixup needed.

3. **Fuzzy Match Engine** — Compare connections against a provided stakeholder list. Flag likely matches with confidence scores for human review.

## Technical Approach (TBD — needs research)

- **Scraping method:** Evaluate options — LinkedIn API (limited), browser automation (Playwright/Selenium), or existing tools (Clawbot, linkedin-scraper libs). Must respect rate limits.
- **Rate limiting:** Built-in delays, randomised timing, session rotation if needed.
- **Fuzzy matching:** `thefuzz` / `rapidfuzz` library for name+title+employer matching.
- **Storage:** SQLite for simplicity, with export to XLSX via `openpyxl`.

## Constraints

- Partners must consent before scraping begins
- Respect LinkedIn rate limits — delays to avoid account flagging
- Data access restricted (Troy + data team lead only)
- Data deleted after the session — deletion policy confirmed before build
- Must run unattended against all ~30 partner profiles

## Definition of Done

- [ ] Agentic script runs against all partner profiles without manual intervention
- [ ] All data stored correctly in the schema
- [ ] Spreadsheet export works and is clean
- [ ] Fuzzy match runs against a test stakeholder list and returns flagged results
- [ ] Dry run completed and reviewed

## Timeline

- **Blocked on:** Partner list + LinkedIn URLs from the client
- **Target:** Built and dry-run tested ~3 weeks before the session
- **Start:** As soon as partner list confirmed

## Open Questions

- Which scraping method is viable and least risky? (API vs browser automation vs third-party tool)
- What LinkedIn account will be used for scraping? (risk of flagging)
- What format will the target stakeholder list come in?
- What "session" means in the partners table — event name?
- Data retention/deletion — how long after the session?
