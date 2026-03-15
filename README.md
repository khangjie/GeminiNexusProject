# ExpenseHive Nexus

## Project Title (Creative Name)
**NexusHub**

An AI-driven expense operations hub that combines receipt intelligence, approval automation, proposal optimization, and analytics into a multi-agent swarm system.

---

## System Architecture Diagram (A2A Flow)

```text
+----------------------------------------------------------------------------------+
|                         Receipt Orchestrator Agent                               |
|----------------------------------------------------------------------------------|
| Model: gemini-2.5-flash                                                          |
| Role: Coordinates full receipt processing, optimization, and analytics           |
|----------------------------------------------------------------------------------|
| Tools:                                                                           |
| 1) call_receipt_intake_pipeline                                                  |
| 2) call_validation_swarm                                                         |
| 3) call_decision_agent                                                           |
| 4) call_proposal_optimization_pipeline                                           |
| 5) call_analytics_pipeline                                                       |
+----------------------------------------------------------------------------------+
         |                              |                               |
         v                              v                               v
+-------------------------------+  +-------------------------------+  +------------------------------+
| Tool: call_receipt_intake...  |  | Tool: call_validation_swarm  |  | Tool: call_decision_agent   |
| Calls: OCR -> Parser -> Type  |  | Calls: rule/pre/duplicate    |  | Calls: decision/categorize  |
+-------------------------------+  +-------------------------------+  +------------------------------+
         |                              |                               |
         v                              v                               v
+-------------------------------+  +-------------------------------+  +------------------------------+
| OCR Agent                     |  | Rule Checking Agent           |  | Decision Agent              |
+-------------------------------+  +-------------------------------+  +------------------------------+
| Receipt Parser Agent          |  | Pre-Approved Detection Agent  |  | Categorization Agent        |
+-------------------------------+  +-------------------------------+  +------------------------------+
| Receipt Type Classifier Agent |  | Duplicate Detection Agent     |  | Writes to Expense Database  |
+-------------------------------+  +-------------------------------+  +------------------------------+

                                        |
                                        v
                        +-----------------------------------------------+
                        | Tool: call_proposal_optimization_pipeline     |
                        | Trigger: Proposal receipts only               |
                        +-----------------------------------------------+
                                        |
                                        v
                    +-------------------------------------------------------+
                    | Proposal Optimization Pipeline                         |
                    |-------------------------------------------------------|
                    | Item Context Builder Agent                            |
                    | Search Query Optimizer Agent                          |
                    | Google Search Agent                                   |
                    | Review Retrieval Agent                                |
                    | RAG Receipt History Agent                             |
                    | Alternative Aggregation Agent                         |
                    | Recommendation Agent                                  |
                    +-------------------------------------------------------+
                                        |
                                        v
                    +-------------------------------------------------------+
                    | Owner Approval Queue                                  |
                    | - User can edit item search name before AI search     |
                    | - AI returns alternatives with product links           |
                    | - Owner can apply replacement                          |
                    +-------------------------------------------------------+

                                        |
                                        v
                        +-----------------------------------------------+
                        | Tool: call_analytics_pipeline                 |
                        +-----------------------------------------------+
                                        |
                                        v
                    +-------------------------------------------------------+
                    | Analytics Pipeline                                    |
                    |-------------------------------------------------------|
                    | Query Parser -> Metric Extraction -> Data Query       |
                    | -> Aggregation -> Trend Analysis                      |
                    | -> Insight Generation -> Chart Data Builder           |
                    +-------------------------------------------------------+
```

## Alternative / Replacement Agent Flow (Proposal Only)

+----------------------------------------------+
| Owner Approval UI (Proposal Receipt)         |
| - Select item                                |
| - Edit search name before AI search          |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Proposal Optimization Orchestrator           |
| Tool: call_proposal_optimization_pipeline    |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Item Context Builder Agent                   |
| - Normalizes product context                 |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Search Query Optimizer Agent                 |
| - Builds cleaner high-signal search query    |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Parallel Retrieval                           |
| - Google Search Agent                        |
| - Review Retrieval Agent                     |
| - RAG Receipt History Agent                  |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Alternative Aggregation Agent                |
| - Merge + deduplicate + rank                 |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Recommendation Agent                         |
| - Keep only link-backed/reachable options    |
| - Return shortlist to Approval UI            |
+----------------------------------------------+
                    |
                    v
+----------------------------------------------+
| Owner applies replacement                    |
| - Original item strikethrough                |
| - Replacement item added to receipt          |
+----------------------------------------------+
```
---

### A2A Notes
- Sequential orchestration is used for deterministic pipeline stages.
- Parallel orchestration is used for multi-signal validation and optimization.
- Failures can fall back to direct Gemini execution when ADK orchestration is unavailable.
- Proposal optimization requires link-backed alternatives before replacement is applied.


## Agent Profiles (Role Descriptions)

```text
+--------------------------------------------------------------------------------+
| 1) OCR Agent                                                                   |
| Role: Extract text from receipt image/PDF                                      |
+--------------------------------------------------------------------------------+
| 2) Receipt Parser Agent                                                        |
| Role: Convert OCR text into structured fields and line items                   |
+--------------------------------------------------------------------------------+
| 3) Receipt Type Classifier Agent                                               |
| Role: Classify receipt as proposal or paid_expense                             |
+--------------------------------------------------------------------------------+
| 4) Rule Checking Agent                                                         |
| Role: Evaluate owner auto-approval rules with pass/fail explanations           |
+--------------------------------------------------------------------------------+
| 5) Pre-Approved Detection Agent                                                |
| Role: Match extracted items against pre-approved item list                     |
+--------------------------------------------------------------------------------+
| 6) Duplicate Detection Agent                                                   |
| Role: Detect potential duplicate receipts from historical records               |
+--------------------------------------------------------------------------------+
| 7) Decision Agent                                                              |
| Role: Combine validation outputs and produce status/verdict/reason             |
+--------------------------------------------------------------------------------+
| 8) Categorization Agent                                                        |
| Role: Assign item categories for reporting and analytics                       |
+--------------------------------------------------------------------------------+
| 9) Proposal Optimization Orchestrator (proposal only)                          |
| Role: Find better alternatives before approval                                 |
| Sub-agents:                                                                    |
|   - Item Context Builder Agent                                                 |
|   - Search Query Optimizer Agent                                               |
|   - Google Search Agent                                                        |
|   - Review Retrieval Agent                                                     |
|   - RAG Receipt History Agent                                                  |
|   - Alternative Aggregation Agent                                              |
|   - Recommendation Agent                                                       |
+--------------------------------------------------------------------------------+
| 10) Analytics Agent                                                            |
| Role: Answer spending questions and return chart-ready insights                |
+--------------------------------------------------------------------------------+
```

---

## Setup Instructions

### Prerequisites
- Python 3.11+ (3.12 recommended)
- Node.js 18+
- npm
- Optional: Docker + gcloud CLI (for Cloud Run deployment)

### 1) Clone and open project
```bash
git clone <your-repo-url>
cd GeminiNexusProject
```

### 2) Backend setup (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create/update environment file:
```bash
copy .env.example .env
```

Important backend env values:
- `GOOGLE_API_KEY`
- `DATABASE_URL` (local SQLite or PostgreSQL)
- `ALLOWED_ORIGINS`
- `LOG_LEVEL=INFO`
- `GEMINI_MODEL`

Run backend:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:
- `http://localhost:8000/health`

API docs:
- `http://localhost:8000/docs`

### 3) Frontend setup (React + Vite)
```bash
cd ../app
npm install
```

Create/update frontend env file (`app/.env`):
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Run frontend:
```bash
npm run dev
```

Default local UI:
- `http://localhost:5173`

### 4) Proposal replacement feature usage
1. Login as owner.
2. Open Approvals.
3. Expand a **proposal** receipt.
4. Click **Find alternatives** on an item.
5. Edit search name if needed, then click **Search**.
6. Select an option with a product link and click **Apply replacement**.

### 5) Cloud Run deployment (Backend)
Use the documented flow in `backend/DEPLOY.md` or script:
```powershell
cd backend
.\deploy-cloudrun.ps1 -ProjectId <your-gcp-project-id> -Region us-central1 -AllowUnauthenticated
```

After deployment:
- Verify service: `gcloud run services list --platform managed --region us-central1 --project <project-id>`
- Check logs in Cloud Run Logs / Cloud Logging.

---

Built for Track C: Operations Hub Process Automation Swarm.
