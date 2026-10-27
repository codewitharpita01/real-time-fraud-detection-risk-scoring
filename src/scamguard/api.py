from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .analyzer import analyze
from .config import CATEGORIES, MAX_TEXT_CHARS
from .model import load_model, load_thresholds

app = FastAPI(title="ScamShield Screening API", version="1.0.0", description="Local explainable screening prototype; results are not verified fraud findings.")
load_model()
load_thresholds()


class AnalyzeRequest(BaseModel):
    category: str = "auto"
    text: str = Field(default="", max_length=MAX_TEXT_CHARS)
    url: str = Field(default="", max_length=2048)


@app.get("/health")
def health():
    return {"status": "ok", "categories": list(CATEGORIES)}


@app.post("/analyze")
def analyze_endpoint(request: AnalyzeRequest):
    try:
        return analyze(request.text, request.category, request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
