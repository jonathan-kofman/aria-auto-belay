# McKinsey/QuantumBlack Agentic AI Patterns — Applied to MillForge & ARIA-OS

> Extracted from McKinsey's "One Year of Agentic AI: Six Lessons" (Sep 2025), "Seizing the Agentic AI Advantage" (2025), and QuantumBlack's "Agentic Workflows for Software Development" (Medium, 2025).

---

## 1. The Six Lessons

### Lesson 1: Focus on Workflow Redesign, Not Just the Agent

**McKinsey says:** Organizations focus too much on the agent/tool, building "great-looking agents that don't actually improve the overall workflow." Success requires fundamentally reimagining entire workflows — people, processes, and technology together.

**MillForge mapping:** This is exactly MillForge's thesis. We're not bolting AI onto existing job shop workflows — we're redesigning the entire flow from quoting through scheduling to production. The 28-agent architecture exists to serve the workflow, not the other way around.

**ARIA-OS mapping:** The 5-phase pipeline (research -> synthesis -> geometry -> manufacturing -> finalize) is workflow-first. Each phase has clear inputs/outputs. The agents serve the pipeline, not vice versa.

### Lesson 2: Keep People Central to Operations

**McKinsey says:** People remain central. Start by mapping processes and identifying user pain points. Design agentic systems that reduce unnecessary work, not replace humans.

**MillForge mapping:** Customer discovery confirms this — shop owners want AI that handles the tedious parts (quoting, scheduling optimization) while keeping them in control of critical decisions (accepting jobs, quality approval). The human-in-the-loop pattern is core to MillForge's design.

**ARIA-OS mapping:** The pipeline has interactive confirmation points (y/N prompts for drawings, preview before export, auto-confirm flag for batch). Safety-critical parts (CEM SF checks) always report to the operator.

### Lesson 3: Create Learning Loops and Feedback Mechanisms

**McKinsey says:** Build self-reinforcing systems where the more agents are used, the smarter and more aligned they become. Collaboration through learning loops and feedback mechanisms.

**MillForge mapping:** Each completed job becomes training data for better quoting estimates and scheduling predictions. The feedback loop from production floor back to planning is a core differentiator.

**ARIA-OS mapping:** `cad_learner.py` records every attempt outcome. `previous_failures` injection gives the LLM context on what went wrong. The validation loop (up to 10 retries) is a tight feedback mechanism. Template extraction from successful LLM generations is on the Q3 roadmap.

### Lesson 4: Use Agents Selectively (implied from 50+ builds analysis)

**McKinsey says:** Not every task benefits from an agent. Some tasks are better served by deterministic automation, rules engines, or simple scripts. Agent overhead (token cost, latency, hallucination risk) must be justified by the task's complexity.

**MillForge mapping:** The 28 agents are specialized — each handles a domain where LLM reasoning adds value. Simple lookups and calculations don't need agents.

**ARIA-OS mapping:** This is why we have the template-first fallback chain. 59 templates handle known parts deterministically (zero tokens, instant). LLM is only invoked for genuinely novel geometry. CEM physics is fully deterministic — no LLM in that path.

### Lesson 5: Invest in Governance and Evaluation

**McKinsey says:** Agent-specific governance mechanisms are needed. Organizations must deploy evaluation frameworks that measure agent output quality, not just activity.

**MillForge mapping:** Quality gates at each production stage. Automated inspection integration on the roadmap.

**ARIA-OS mapping:** Post-gen validation loop, CEM SF thresholds, machinability checks, output contracts (JSON Schema), and the `--validate` flag for re-checking all outputs. The visual verification system (vision AI PASS/FAIL) is an evaluation framework.

### Lesson 6: The CEO Must Drive the Pivot

**McKinsey says:** "The moment has come to bring the gen AI experimentation chapter to a close — a pivot only the CEO can make." Companies must move from pilots to production, from horizontal to vertical.

**MillForge mapping:** This is the YC pitch: manufacturers have experimented with horizontal AI tools (copilots, chatbots) and seen no material impact. MillForge is the vertical solution that actually transforms their workflow. The CEO/owner of a job shop needs to commit to workflow transformation, not just add another tool.

---

## 2. Spec-Driven Development (SDD) Pattern

From QuantumBlack's Medium article on agentic workflows:

### Two-Layer Architecture

| Layer | Role | Implementation |
|---|---|---|
| **Orchestration (Deterministic)** | Controls sequencing, phase transitions, dependency management | Rule-based engine, not an LLM |
| **Execution (Agent + Evaluation)** | Specialized agents handle distinct tasks, outputs pass deterministic checks | LLM agents with iteration caps (3-5 attempts) |

**Key principles:**
- Structured specifications drive agent outputs — no ad hoc prompts
- Agents operate within explicit, machine-readable guidelines
- Iteration loops capped; failures escalate to humans
- Git as state store, commits mark phase completion
- Repository structure encodes workflow logic

### Comparison with MillForge/ARIA-OS

**ARIA-OS already implements SDD:**
- Orchestrator (`orchestrator.py`) is the deterministic layer — it sequences plan -> route -> generate -> validate -> CEM -> export
- Generators are the execution layer — specialized per backend (CadQuery, Grasshopper, Fusion, Blender)
- Validation loop caps at 3-10 attempts with failure context injection
- Output contracts (`contracts/`) enforce JSON Schema on all structured outputs
- `spec_extractor.py` converts natural language to machine-readable specs before any generator

**Gaps to address:**
- MillForge doesn't yet have a formal SDD structure (`.sdlc/` folder pattern)
- Knowledge agent pattern (centralized source of truth for agent queries) — not implemented
- Logged assumptions tracking — not implemented

---

## 3. The Gen AI Paradox (Horizontal vs Vertical)

**McKinsey data:**
- ~80% of companies have deployed gen AI in some form
- ~80% report **no material impact on earnings**
- ~90% of vertical (function-specific) use cases remain stuck in pilot
- Horizontal use cases (copilots, chatbots) deliver diffuse, hard-to-measure benefits
- Vertical use cases deliver 20-60% productivity gains but rarely escape pilot

**Why this matters for MillForge:**
Manufacturing is the quintessential vertical domain. Horizontal AI tools don't understand job shop scheduling constraints, material costs, machine capabilities, or tolerance stackups. MillForge is purpose-built for this vertical — and McKinsey's data shows that's where the real value is.

---

## 4. Architecture Comparison Table

| Pattern | McKinsey Recommendation | MillForge/ARIA-OS Current | Gap/Action |
|---|---|---|---|
| Workflow-first design | Redesign entire workflow, not just add agents | Yes — MillForge redesigns quoting→production; ARIA-OS has 5-phase pipeline | Aligned |
| Deterministic orchestration | Rule-based sequencing, not LLM-decided | Yes — `orchestrator.py` is deterministic | Aligned |
| Bounded agent execution | Cap iterations, escalate failures | Yes — validation loop 3-10 attempts, fallback chain | Aligned |
| Spec-driven inputs | Machine-readable specs, no ad hoc prompts | Partial — `spec_extractor.py` exists but not all agents use structured specs | Extend SDD to MillForge agents |
| Learning loops | Self-reinforcing improvement from usage | Partial — `cad_learner.py` + failure injection; no formal feedback loop in MillForge yet | Build feedback pipeline from production → quoting |
| Output contracts | Schema-validated structured outputs | Yes — JSON Schema contracts for CAM setup, ECAD BOM | Extend to all MillForge outputs |
| Knowledge agent | Central truth store for agent queries | No — agents load context files but no queryable knowledge agent | Implement with QMD as backend |
| Evaluation framework | Measure output quality, not activity | Partial — visual verification, CEM SF, machinability checks | Add dimensional verification (Q2 roadmap) |
| Vertical focus | Function-specific > horizontal | Yes — manufacturing-specific domain expertise is core | Aligned — this IS the pitch |
| Human-in-the-loop | People central, reduce unnecessary work | Yes — interactive confirmations, operator setup sheets | Aligned |

---

## 5. YC-Relevant Insights

### Quote 1: The Paradox of Deployment Without Impact
> "Nearly 80% of companies have deployed gen AI, but roughly the same percentage report no material impact on earnings." — McKinsey, "Seizing the Agentic AI Advantage"

**YC angle:** The market is spending but not seeing returns. MillForge solves this for manufacturing — a vertical solution that delivers measurable productivity gains (faster quoting, optimized scheduling, reduced scrap).

### Quote 2: Vertical Beats Horizontal
> "90% of vertical use cases remain stuck in pilot... higher-impact vertical use cases seldom make it out of pilot because of technical, organizational, data, and cultural barriers." — McKinsey

**YC angle:** MillForge is the team that can navigate those barriers for manufacturing. Deep domain expertise (mechanical engineering + manufacturing + AI) is the moat. Horizontal AI companies can't do this.

### Quote 3: Workflow Redesign is the Differentiator
> "Agentic AI efforts that focus on fundamentally reimagining entire workflows — involving people, processes, and technology — are more likely to deliver a positive outcome." — McKinsey, "Six Lessons"

**YC angle:** MillForge isn't adding AI to existing workflows. We're redesigning the entire job shop operation. This is what McKinsey says works, and it's what most companies fail to do.

### Quote 4: The Agent Quality Problem
> "Some companies are rehiring people where agents have failed." — McKinsey, "Six Lessons"

**YC angle:** Quality control is non-negotiable in manufacturing. MillForge's multi-layer validation (CEM physics, FEA, DFM scoring, visual verification) ensures agent outputs meet engineering standards. This is why vertical expertise matters.

### Quote 5: Deterministic + Agent Hybrid
> "Structured specifications drive what agents produce and ad hoc prompts are eliminated... Orchestration through rule-based engines, not LLM-decided sequencing." — QuantumBlack, "Agentic Workflows"

**YC angle:** ARIA-OS already implements this pattern — deterministic orchestration with bounded agent execution. The template-first fallback chain (59 templates → Zoo.dev → Claude → Gemini → Gemma → deterministic) means known parts never touch an LLM. This is the architecture McKinsey recommends, and we built it independently.

---

## Sources

- [One Year of Agentic AI: Six Lessons](https://www.mckinsey.com/capabilities/quantumblack/our-insights/one-year-of-agentic-ai-six-lessons-from-the-people-doing-the-work) — McKinsey/QuantumBlack, Sep 2025
- [Seizing the Agentic AI Advantage](https://www.mckinsey.com/capabilities/quantumblack/our-insights/seizing-the-agentic-ai-advantage) — McKinsey/QuantumBlack, 2025
- [Agentic Workflows for Software Development](https://medium.com/quantumblack/agentic-workflows-for-software-development-dc8e64f4a79d) — QuantumBlack/Medium, 2025
- [CEO Strategies for Agentic AI](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-change-agent-goals-decisions-and-implications-for-ceos-in-the-agentic-age) — McKinsey, 2025

---

*Created: 2026-04-06 | For: YC S26 application (deadline 2026-05-04)*
