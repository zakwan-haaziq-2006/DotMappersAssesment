# app/llm_query.py

import os
from collections import Counter
import pandas as pd
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from app.database import get_connection
from app.anomalies import get_all_anomalies
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# main model - used for sql generation, answer generation, and routing
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="openai/gpt-oss-120b",
    temperature=0,
)

# bigger model - only used for structured output, 8b isn't reliable at tool calling
structured_llm_model = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="openai/gpt-oss-120b",
    temperature=0,
)

TABLE_SCHEMA = """
Table: tickets
Columns:
- ticket_id (text)
- created_at (datetime)
- category (text) - values: Billing, General, Technical
- priority (text) - values: Low, Medium, High, Critical
- status (text) - values: Open, Resolved, Escalated
- response_time_hrs (float)
- resolution_time_hrs (float, null if not resolved)
- agent_id (text)
- customer_rating (float 1-5, null if not rated)
- issue_summary (text)
"""

sql_prompt = PromptTemplate.from_template("""You are a SQL expert. Given this table schema:

{schema}

Write a SQLite SELECT query to answer this question:
"{question}"

Rules:
- Only write SELECT statements, nothing else
- Return ONLY the SQL query, no explanation, no markdown

SQL query:""")

sql_chain = sql_prompt | llm | StrOutputParser()

answer_prompt = PromptTemplate.from_template("""The user asked: "{question}"

The SQL query returned this data:
{result}

Give a short, natural-language answer to their question based on this data.

Rules:
- Always mention the correct unit (hours for response_time_hrs and resolution_time_hrs, a 1-5 scale for customer_rating)
- Round numbers to 1-2 decimal places, don't dump raw floats
- Write it as a complete, clear sentence
- Don't say things like "as recorded in your data" or "based on the data provided" - just answer directly
""")

answer_chain = answer_prompt | llm | StrOutputParser()

# keywords that trigger the anomaly path instead of sql generation
ANOMALY_KEYWORDS = ["anomaly", "anomalies", "unusual", "flagged", "suspicious", "outlier", "stale", "weird tickets"]


def is_anomaly_question(question):
    q_lower = question.lower()
    return any(word in q_lower for word in ANOMALY_KEYWORDS)


def question_to_sql(question):
    sql = sql_chain.invoke({"schema": TABLE_SCHEMA, "question": question})
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def is_safe_query(sql):
    sql_lower = sql.lower().strip()
    if not sql_lower.startswith("select"):
        return False

    bad_words = ["drop", "delete", "update", "insert", "alter", "truncate"]
    for word in bad_words:
        if word in sql_lower:
            return False

    return True


def answer_anomaly_question(question):
    anomalies = get_all_anomalies()
    summary = summarize_anomalies(anomalies)

    natural_prompt = f"""The user asked: "{question}"

Here is the anomaly analysis:
{summary}

Answer their question in a short, natural, conversational way using this info."""

    natural_answer = llm.invoke(natural_prompt).content

    return {"question": question, "sql": None, "answer": natural_answer}


def answer_question(question):
    # route anomaly-related questions to the anomaly path, skip sql entirely
    if is_anomaly_question(question):
        return answer_anomaly_question(question)

    sql = question_to_sql(question)

    if not is_safe_query(sql):
        return {"question": question, "sql": sql, "answer": "Couldn't generate a safe query for that."}

    conn = get_connection()
    try:
        result = pd.read_sql_query(sql, conn)
    except Exception as e:
        conn.close()
        return {"question": question, "sql": sql, "answer": f"Query failed: {e}"}
    conn.close()

    if len(result) == 0:
        return {"question": question, "sql": sql, "answer": "No matching tickets found."}

    answer = answer_chain.invoke({"question": question, "result": result.to_string()})
    return {"question": question, "sql": sql, "answer": answer}


# --- structured anomaly summary stuff below ---

class AnomalySummary(BaseModel):
    total_anomalies: int = Field(description="total number of anomalies found")
    most_common_reason: str = Field(description="the anomaly reason that shows up the most")
    most_affected_category: str = Field(description="which category has the most anomalies")
    risk_level: str = Field(description="overall risk level: Low, Medium, or High")
    summary: str = Field(description="a 2-3 sentence plain english summary of the situation")
    recommended_action: str = Field(description="one concrete suggestion to fix the biggest issue")


def summarize_anomalies(anomalies):
    if len(anomalies) == 0:
        return {
            "total_anomalies": 0,
            "most_common_reason": "none",
            "most_affected_category": "none",
            "risk_level": "Low",
            "summary": "No anomalies found in the current data.",
            "recommended_action": "No action needed.",
        }

    reasons = Counter(a["reason"] for a in anomalies)
    categories = Counter(a["category"] for a in anomalies)
    priorities = Counter(a["priority"] for a in anomalies)

    stats_text = f"""
Total anomalies: {len(anomalies)}
Breakdown by reason: {dict(reasons)}
Breakdown by category: {dict(categories)}
Breakdown by priority: {dict(priorities)}
"""

    structured_llm = structured_llm_model.with_structured_output(AnomalySummary)

    prompt = f"""Here is aggregated anomaly data from a support ticket system:

{stats_text}

Analyze this and summarize the key findings."""

    result = structured_llm.invoke(prompt)
    return result.dict()


if __name__ == "__main__":
    # run this file directly to test it: python -m app.llm_query
    test_questions = [
        "How many critical tickets are unresolved?",
        "What is the average resolution time for Billing tickets?",
        "Are there any anomalies in the tickets?",
        "What kind of unusual tickets do we have?",
    ]

    for q in test_questions:
        result = answer_question(q)
        print("Q:", result["question"])
        print("SQL:", result["sql"])
        print("A:", result["answer"])
        print("---")