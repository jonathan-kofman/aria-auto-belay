# 12. Competitive Landscape

## Direct Competitors & Validators

### Backflip AI — Scan-to-CAD ($30M, NEA + a16z)
Founded by Markforged founders. Converts 3D scans and photos into parametric CAD for manufacturing. Trained on 100M+ synthetic geometries. SolidWorks plugin + web app.

**ARIA-OS differentiation:** They focus on spare parts/reverse engineering. We focus on new part generation from design intent + full manufacturing pipeline (DFM → quote → scheduling). They're closed-source; we're open-source.

**YC angle:** Their $30M raise validates the market. Same problem space, different approach.

### Zoo.dev (formerly KittyCAD) — Text-to-CAD API
AI-native CAD platform generating editable B-Rep models from text. Outputs real STEP files with feature trees (not meshes). Python SDK, free tier ($10/mo).

**Integration:** Added as alternative geometry engine in ARIA-OS. Template → Zoo.dev → Cloud LLM fallback chain.

### MecAgent — AI CAD Copilot ($3M raise)
SolidWorks/Fusion 360 plugin that creates features inside existing CAD. Their approach: drive native CAD software directly.

**ARIA-OS differentiation:** We generate headless (CadQuery → STEP), they need the user's CAD software running. We have the full manufacturing pipeline; they stop at geometry.

## Manufacturing Tools

### Lambda Function — AI CNC Programming (Free)
AI-recommended machining strategies, tools, toolpaths. Plugs into Siemens NX, Mastercam, Fusion 360, GibbsCAM. Closed-loop learning from shop floor data. **Free for machinists.**

**Integration path:** ARIA-OS geometry → Lambda Function CAM → MillForge scheduling with accurate cycle times.

### CloudNC CAM Assist — AI CAM + Instant Quoting
Physics-based AI for feeds/speeds, instant cycle time estimation, auto fixture generation. 3-axis and 3+2 support.

**Integration path:** Same as Lambda Function — their cycle time estimates feed MillForge scheduling.

### Toolpath.com — AI CAM for Job Shops ($35/mo)
DFM analysis + toolpath generation. Potential complement to ARIA-OS's geometry validation.

## Scheduling Competitors

### Smart Shop Floor (SSF) — Traditional APS
Production scheduling for small/medium shops. G2 reviews praise ERP integration.

**MillForge edge:** AI-powered SA optimization (96.4%) vs traditional APS. Plus supplier directory (1,137 distributors) and ARIA-OS CAD integration.

### DigiFabster — Instant CNC Quoting
Customer uploads CAD → gets instant quote → orders online. Subscription-based.

**MillForge edge:** We optimize the schedule behind the quote, not just the price.

## Monitoring & Data

### JITbase — CNC Machine Monitoring
Predicts completion times, operator workload, labor allocation from real-time CNC data. Addresses machinist shortage.

**Integration opportunity:** JITbase data collection → MillForge live schedule re-optimization.

## Open-Source Model Landscape (April 2026)

| Model | Params | License | Our Use |
|-------|--------|---------|---------|
| Gemma 4 31B | 31B dense | Apache 2.0 | Local agents, visual verification |
| DeepSeek-R1 | Various | MIT | CAD code generation (Seek-CAD approach) |
| Qwen 3.6 Plus | Preview | Apache 2.0 | Strong coding, backup |
| Llama 4 Maverick | 400B MoE | Meta (700M cap) | Raw scale when needed |

**Strategy:** Gemma 4 31B local for 80% of agent tasks, Gemini Flash for vision, Claude API for hardest reasoning. ~80% cost reduction on API calls.
