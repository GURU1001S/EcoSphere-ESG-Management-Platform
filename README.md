<p align="center">
  <img src="https://raw.githubusercontent.com/GURU1001S/EcoSphere-ESG-Management-Platform/main/static/description/icon.png" width="120" />
</p>

# 🌱 EcoSphere — ESG Management Platform

> Enterprise ESG intelligence, built natively inside Odoo 17.
> Not a dashboard bolted on top. ESG as operational infrastructure.

---

## The Problem

Organizations are legally and socially pressured to report ESG performance.
Most respond by assigning someone to fill a spreadsheet every quarter.

The result:

- Carbon data lives in purchase orders nobody links to emissions
- Employee sustainability participation is tracked in Google Forms
- Governance compliance is a folder of PDFs nobody reads
- ESG reports are made up numbers dressed in professional formatting

**The data already exists inside your ERP. Nobody connects it.**

---

## What EcoSphere Does

EcoSphere is a native Odoo 17 module that transforms operational ERP data
into live ESG intelligence — without changing how anyone works.

A purchase order confirms → carbon emission is calculated automatically.
An employee completes a sustainability challenge → XP, badges, leaderboards update.
A compliance issue is raised → it is assigned, tracked, and flagged when overdue.
A CSR activity completes → AI synthesizes participant reports into an impact summary.

No manual ESG data entry. No separate dashboard. No integration middleware.
**ESG becomes a property of operations, not a report about operations.**

---

## Demo

[![Demo Video](https://img.shields.io/badge/Watch%20Demo-Loom-purple?style=for-the-badge)](YOUR_LOOM_LINK)

![ESG Dashboard](static/description/screenshots/dashboard.png)

---

## Core Modules

### 🌍 Environmental

Automatic carbon accounting from live ERP transactions.

- Emission factors configured per product category
- Carbon transactions auto-created on Purchase Order confirmation
- AI estimates emission factors for uncatalogued products
- Department-level carbon tracking against sustainability goals
- Environmental score feeds the weighted ESG index

### 👥 Social

Employee sustainability participation with behavioral intelligence.

- CSR activities with UN SDG mapping
- Quality-weighted points — AI scores participation proof, not just attendance
- Challenge engine with adaptive XP (completion rate adjusts reward value)
- Every employee builds a live sustainability behavioral fingerprint
- Sustainability archetypes: The Quiet Contributor, The Sprint Hero,
  The Category Specialist, The Department Anchor

### 🏛️ Governance

Policy compliance and audit tracking that enforces itself.

- ESG policies with employee acknowledgement tracking
- Audit lifecycle with compliance issue generation
- Overdue issues flagged automatically — impossible to miss
- Governance score computed from policy coverage and issue resolution rate

### 🎮 Gamification

Behavioral incentive system that adapts to each employee.

- Challenge kanban with full lifecycle management
- Multi-dimensional badge system with rarity tiers and progression families
- XP-based leaderboards at employee and department level
- Personalized reward catalog — adapts visibility based on engagement state
- AI generates targeted challenges per department based on ESG weakness

---

## AI Features

EcoSphere uses Groq (Llama 3.1) as an embedded intelligence layer.
Three features. Each independently useful. Together they form a system.

### Challenge Recommender

Analyzes each employee's participation history, sentiment tag, and their
department's weakest ESG pillar. Recommends 3 challenges most likely to
drive meaningful engagement for that specific employee.

### Challenge Auto-Generator

Takes a department's current ESG scores and generates 3 contextually
relevant sustainability challenges targeting the weakest pillar.
Challenges are created as Draft records, ready for manager review.

### Impact Synthesizer

When a CSR activity completes, the AI reads every participant's
self-reported impact, synthesizes them into a 3-sentence organizational
impact summary, and stores it on the activity record.
Management gets qualitative ESG intelligence from ground-level data.

---

## The Behavioral Fingerprint

Every employee in EcoSphere has a live behavioral profile:

| Signal                     | What It Captures                                          |
| -------------------------- | --------------------------------------------------------- |
| `sentiment_tag`            | inactive / struggling / consistent / motivated / champion |
| `sustainability_archetype` | participation pattern — computed by AI                    |
| `strongest_pillar`         | which ESG area they contribute most to                    |
| `engagement_score`         | quality × frequency × consistency                         |
| `recommended_challenges`   | AI-curated, refreshed on demand                           |

The reward catalog adapts to sentiment tag silently.
Struggling employees see low-cost motivational rewards.
Champions see exclusive high-value rewards.
No manual segmentation. No rules engine to configure.

---

## Scoring Engine

ESG performance is computed bottom-up from real operational data.

```
Carbon Transactions → Environmental Score  (weight: 40%)
Participation Data  → Social Score         (weight: 30%)
Compliance Issues   → Governance Score     (weight: 30%)
                                                   ↓
                             Department Total Score
                                                   ↓
                   Weighted Average → Organization ESG Score
```

Weights are configurable per organization in Settings.
Scores recompute via scheduled cron — no manual refresh needed.

---

## Data Model

```
eco.department               Organizational hierarchy + ESG ownership
eco.category                 Shared taxonomy (CSR / Challenge types)
eco.emission_factor          Carbon values per product/activity type
eco.environmental_goal       Sustainability targets with progress tracking
eco.carbon_transaction       Calculated emissions from ERP operations
eco.csr_activity             Social initiatives with SDG mapping
eco.employee_participation   CSR attendance with AI impact scoring
eco.challenge                Adaptive sustainability challenges
eco.challenge_participation  Employee progress with behavioral signals
eco.badge                    Multi-dimensional achievements with rarity
eco.reward                   Personalized incentive catalog
eco.policy                   Governance policies
eco.policy_acknowledgement   Employee acceptance tracking
eco.audit                    Governance audit lifecycle
eco.compliance_issue         Violations with overdue auto-flagging
eco.department_score         Aggregated ESG performance per department
```

---

## Installation

**Requirements:** Odoo 17 Community Edition, PostgreSQL 15

```bash
# 1. Clone the repository
git clone https://github.com/GURU1001S/EcoSphere-ESG-Management-Platform
cd EcoSphere-ESG-Management-Platform

# 2. Copy module to your Odoo addons path
cp -r ecosphere /path/to/odoo/addons/

# 3. Start Odoo with Docker (if not already running)
docker run -d --name db \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD=odoo \
  postgres:15

docker run -d --name odoo \
  -p 8069:8069 --link db:db \
  -v /path/to/addons:/mnt/extra-addons \
  odoo:17

# 4. Install the module
# Browser → localhost:8069
# Settings → Activate Developer Mode
# Apps → Update App List → Search "EcoSphere" → Install

# 5. Configure AI features
# Enable developer mode: Settings → Activate Developer Mode
# Go to Settings → Technical → System Parameters
# Add 'ecosphere.grok_api_key' and paste your Groq API key
# Enable: Auto Emission Calculation, Badge Auto-Award
```

**Or with Docker Compose (recommended):**

```bash
docker-compose up -d
# Odoo available at localhost:8069
```

---

## Configuration

| Setting                   | Description                               | Default  |
| ------------------------- | ----------------------------------------- | -------- |
| Auto Emission Calculation | Creates carbon records on PO confirm      | OFF      |
| Evidence Required         | Blocks approval without proof upload      | OFF      |
| Badge Auto-Award          | Awards badges on XP threshold cross       | ON       |
| Groq API Key            | Required for AI features                  | —        |
| ESG Weights               | Environmental / Social / Governance split | 40/30/30 |

---

## Screenshots

| ESG Dashboard                                              | Challenge Board                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------ |
| ![Dashboard](static/description/screenshots/dashboard.png) | ![Challenges](static/description/screenshots/challenges.png) |

| Employee Profile                                       | Compliance Tracker                                           |
| ------------------------------------------------------ | ------------------------------------------------------------ |
| ![Profile](static/description/screenshots/profile.png) | ![Compliance](static/description/screenshots/compliance.png) |

---

## Reports

EcoSphere generates four structured reports exportable as PDF, Excel, or CSV:

- **Environmental Report** — carbon transactions, emission trends, goal progress
- **Social Report** — CSR participation, impact scores, engagement rates
- **Governance Report** — policy coverage, audit findings, issue resolution
- **ESG Summary Report** — organization-wide score, department rankings
- **Custom Report Builder** — filter by department, date, module, employee, challenge

---

## Architecture

```text
Odoo 17
        │
        ├── PostgreSQL (via Odoo ORM)
        │
        ├── EcoSphere Models (Python)
        │       ├── Business Logic
        │       │     ├── ESG Scoring Engine (compute methods)
        │       │     ├── Workflow Engine (state transitions)
        │       │     └── Business Rules
        │       │
        │       └── AI Integration
        │             └── Groq / Llama 3.1 API
        │                 (challenge generation, feedback, ESG insights)
        │
        ├── Views (XML)
        │       ├── Dashboard
        │       ├── Form Views
        │       ├── List Views
        │       ├── Kanban
        │       ├── Leaderboard
        │       └── QWeb Reports (PDF)
        │
        └── Automation
                ├── Cron: Daily ESG score recompute
                ├── Cron: Overdue compliance flagging
                └── Cron: Badge auto-award
```

---

## What Makes This Different

| Feature            | Standard ESG Tool      | EcoSphere                              |
| ------------------ | ---------------------- | -------------------------------------- |
| Carbon tracking    | Manual entry form      | Auto from PO confirmation              |
| Gamification       | Flat XP + badges       | Adaptive XP, rarity tiers, archetypes  |
| Challenge creation | Manual by admin        | AI-generated from ESG weakness         |
| Points system      | Flat attendance points | Quality-weighted via AI impact scoring |
| Reward catalog     | Same for everyone      | Adapts to employee engagement state    |
| ESG reports        | Manual compilation     | Live from operational data             |
| Odoo integration   | External tool / iframe | Native module, same data layer         |

---

## Team

Built in 8 hours at Odoo Hackathon 2026 by the **EcoSphere Team**.

---

## License

LGPL-3 — same license as Odoo Community Edition.

---

_EcoSphere is a hackathon prototype exploring what ESG infrastructure
looks like when it is treated as an operational concern, not a reporting one._
