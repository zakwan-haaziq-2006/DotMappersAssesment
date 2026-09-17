from fastapi import FastAPI
from pydantic import BaseModel
from app.anomalies import get_all_anomalies
from app.llm_query import answer_question
from app.llm_query import summarize_anomalies

app = FastAPI(title="Support Ticket AI Assistant")


class QuestionRequest(BaseModel):
    question: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/query")
def query(request: QuestionRequest):
    result = answer_question(request.question)
    return result


@app.get("/anomalies")
def anomalies():
    result = get_all_anomalies()
    return {"count": len(result), "anomalies": result}



@app.get("/anomalies/summary")
def anomalies_summary():
    result = get_all_anomalies()
    summary = summarize_anomalies(result)
    return summary