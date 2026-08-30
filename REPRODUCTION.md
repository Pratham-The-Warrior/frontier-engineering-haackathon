# Prism — Reproduction & Verification Guide

Step-by-step instructions to reproduce all benchmarks, run tests, and launch the interactive web dashboard from a clean environment.

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|:---|:---|:---|
| **Python** | `3.11+` | Tested on 3.11, 3.12, 3.14 |
| **pip** | Latest | Package manager |
| **OpenAI API Key** | — | GPT-4o access (mock fallback included for offline runs) |

---

## ⚡ Setup (< 2 minutes)

### 1. Clone the repository
```bash
git clone <repo-url>
cd micro1-hackathon
```

### 2. Create and activate a virtual environment
```bash
# Create venv
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Activate (Linux/macOS)
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Key (Live LLM or Zero-Cost Offline Mode)
```bash
cp .env.example .env
```
Edit `.env` and set your preferred provider:
```env
# Option A: Google Gemini (gemini-3.6-flash)
GEMINI_API_KEY=your-gemini-api-key-here

# Option B: OpenAI (gpt-4o)
OPENAI_API_KEY=sk-your-openai-api-key-here
```
*(Note: If no API key is provided, the platform automatically utilizes its built-in realistic mock LLM fallback, allowing judges and automated CI pipelines 100% offline evaluation for $0.00 cost).*

### 5. Generate synthetic incident datasets
```bash
# Generate core 10 incidents
python data/generate_incidents.py

# Generate Mega Outage scenario (INC-011: 1,000+ logs, Kafka partition starvation)
python data/generate_mega_incident.py
```

---

## 🚀 Running the Multi-Agent Solution

### Run on a single incident
```bash
python run_agent.py --incident 1
# or run the mega outage scenario:
python run_agent.py --incident 11
```

**Expected output:**
- Progresses through 4 phases (Source Analysis $\to$ Shared Memory & Timeline $\to$ Agentic RCA $\to$ Report Synthesis).
- Generated report saved to: `output/agent/incident_01_db_connection_pool_postmortem.md`
- Execution trajectory saved to: `output/agent/incident_01_db_connection_pool_trajectory.json`
- Runtime: ~30-60 seconds per incident
- Token usage: ~3,000-6,000 tokens per incident

### Run on all 11 incidents in batch
```bash
python run_agent.py --incident all
```

---

## 📊 Running the Baseline & Evaluation

### 1. Run single-prompt baseline on all incidents
```bash
python run_baseline.py --incident all
```

### 2. Run evaluation benchmark comparison
```bash
python run_evaluation.py
```

**Expected output:**
- Comparison table printed to console.
- Detailed results saved to `evaluation/results/evaluation_results.json`.
- Formatted markdown table saved to `evaluation/results/comparison_table.md`.

---

## 🌐 Launching the Interactive Web Dashboard (Port 8000)

Start the production FastAPI server:
```bash
python server.py
```

Open your browser at:
* **Interactive Dashboard:** `http://localhost:8000`
* **Swagger API Explorer:** `http://localhost:8000/docs`
* **Incidents REST API:** `http://localhost:8000/api/incidents`

---

## 🧪 Running Automated Tests

Run the complete regression test suite:
```bash
python -m unittest discover tests
```
**Expected output:**
```
Ran 75 tests in ~0.15s
OK
```

---

## 🔌 Running Enterprise Integrations

### Export Slack Block Kit payload
```bash
python -m integrations.enterprise_integrations --incident-dir data/incidents/incident_01_db_connection_pool --export-slack
```

### Export Jira Action Item tickets
```bash
python -m integrations.enterprise_integrations --incident-dir data/incidents/incident_01_db_connection_pool --export-jira
```

---

## 💰 Cost & Resource Estimate

| Operation | Approx. Cost (GPT-4o) | Offline Fallback |
|:---|:---:|:---:|
| Single incident (agent) | ~$0.05-0.10 | $0.00 |
| All 11 incidents (agent) | ~$0.60-1.10 | $0.00 |
| All 11 incidents (baseline) | ~$0.25-0.45 | $0.00 |
| Full benchmark evaluation | ~$0.35-0.60 | $0.00 |
| **Total reproduction run** | **~$1.20-2.15** | **$0.00** |
