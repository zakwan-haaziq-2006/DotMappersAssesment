# Support Ticket AI Assistant
 
An AI-powered system for querying and analyzing a customer support tickets dataset using natural language, with automated anomaly detection.
 
Built for the DotMappers IT AI Engineer Assessment Sprint.
 
## What it does
 
- Loads a 500-row support tickets CSV into a queryable SQLite database
- Answers natural language questions about the data (e.g. "How many critical tickets are unresolved?") using an LLM that translates questions into SQL
- Detects anomalies using two rule-based checks (no ML training involved)
- Generates a structured, LLM-written summary of anomaly patterns
- Exposes everything through a REST API (4 endpoints) and a Streamlit UI
## Architecture
 
```
CSV --> SQLite (queryable store)
                |
                +--> Anomaly rules (pure Python/pandas logic)
                |         |
                |         +--> LLM structured summary (Groq + Pydantic schema)
                |
                +--> Natural language question
                          |
                          +--> Question router (anomaly keywords vs. general)
                                    |
                                    +--> Anomaly path: uses anomaly summary
                                    +--> SQL path: LLM generates SQL --> runs on SQLite --> LLM phrases answer
```
 
**Key design decisions:**
 
- **SQLite over a pandas agent.** Letting an LLM write SQL against a fixed schema is more predictable and auditable than letting it generate arbitrary pandas code. SQL is also easy to validate/sandbox (see safety checks below).
- **Rule-based anomaly detection, not ML.** With 500 rows and a 48-hour window, a trained model would be unjustifiable and hard to explain. Two clear, threshold-based rules cover the requirement and are fully explainable.
- **Percentile-based threshold instead of mean + 2×stddev.** Initial EDA showed resolution times have a std of 5.79 against a max of 19.9 hours — a mean+2×stddev threshold (21.7) would never trigger. Switched to a 90th-percentile cutoff per category instead, which reliably flags real outliers.
- **LangChain + Groq (openai/gpt-oss-120b).** Free, fast, reliable for SQL generation and short-answer phrasing.
- **Keyword-based question routing.** Questions containing anomaly-related terms ("anomaly," "unusual," "flagged," etc.) are routed to the anomaly-summary path instead of SQL generation, since "anomaly" isn't a real column the LLM could query.
## Anomaly rules
 
1. **Stale high-priority tickets** — status is Open or Escalated, priority is High or Critical, and the ticket has been open more than 24 hours (relative to the latest `created_at` in the dataset, since this is a static snapshot rather than a live system).
2. **Slow resolution** — resolved tickets whose `resolution_time_hrs` exceeds the 90th percentile for their category (Billing/General/Technical calculated separately, since categories have different typical resolution times).
## Tech stack
 
- **Backend:** FastAPI
- **UI:** Streamlit
- **LLM orchestration:** LangChain
- **LLM provider:** Groq (free tier) — `llama-3.1-8b-instant` for SQL generation/answers, `llama-3.3-70b-versatile` for structured output
- **Data:** pandas, SQLite
## Project structure
 
```
dotmappers-assessment/
├── data/
│   └── support_tickets.csv
├── app/
│   ├── database.py       # CSV -> SQLite loading
│   ├── anomalies.py      # rule-based anomaly detection
│   ├── llm_query.py      # LangChain + Groq: SQL generation, answers, anomaly routing
│   ├── main.py            # FastAPI app and endpoints
│   └── ui.py               # Streamlit frontend
├── server.py                # starts backend + frontend together
├── requirements.txt
├── .env.example
└── README.md
```
 
## Setup
 
1. Clone the repo and install dependencies:
```bash
pip install -r requirements.txt
```
 
2. Copy `.env.example` to `.env` and add your Groq API key:
```
GROQ_API_KEY=your-key-here
```
Get a free key at [console.groq.com](https://console.groq.com).
 
3. Place `support_tickets.csv` in the `data/` folder.
## Running it
 
Single command starts both the API and UI:
```bash
python server.py
```
 
- API: `http://127.0.0.1:8000` (docs at `/docs`)
- UI: `http://localhost:8501`
## API endpoints
 
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/query` | Ask a natural language question. Body: `{"question": "..."}` |
| GET | `/anomalies` | Returns the full list of flagged anomalies |
| GET | `/anomalies/summary` | Returns an LLM-generated structured summary of anomaly patterns |
 
## Example queries
 
**Q: How many critical tickets are unresolved?**
> There are 31 critical tickets that are still unresolved.
 
**Q: What is the average resolution time for Billing tickets?**
> The average resolution time for Billing tickets is approximately 16.3 hours.
 
**Q: Which category has the most escalated tickets?**
> The General category has the most escalated tickets.
 
**Q: Are there any anomalies in the tickets?**
> (Routed to the anomaly summary path — returns a natural-language summary built from the structured anomaly analysis rather than attempting to generate SQL, since "anomaly" has no corresponding column.)
 
## Edge cases handled
 
- **Unsafe SQL generation:** every generated query is checked to ensure it starts with `SELECT` and contains no destructive keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`) before execution.
- **Zero-result queries:** returns a clear "No matching tickets found" message instead of an empty/confusing response.
- **Off-topic questions:** tested with unrelated questions (e.g. general knowledge) — handled gracefully without crashing.
- **Empty anomaly list:** the structured summary function short-circuits and returns a hardcoded "no anomalies" response instead of calling the LLM unnecessarily.
- **Windows Application Control restrictions:** development environment blocked direct `.exe` execution of `uvicorn`/`streamlit`; resolved by invoking both via `python -m`.
## Known limitations
 
- **Stale-ticket reference date:** since the dataset is a static snapshot, "now" is approximated as the latest `created_at` timestamp in the data rather than the real current time. In a live system this would use the actual current timestamp, and the stale-ticket count would likely be smaller.
- **Question routing is keyword-based, not true intent classification.** A question about anomalies phrased without any of the matched keywords (e.g. "what's wrong with the tickets?") would fall through to the SQL path and likely fail, since there's no literal "anomaly" column to query.
- **No automated test suite.** Testing was done manually against sample questions and edge cases documented above, given the assessment's time constraints.
- **Single-file SQLite, no concurrent write handling** — fine for this read-heavy, single-user use case, not designed for concurrent multi-user production load.
## Author
 
Zakwan
 
