from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.orchestrator import generate_report
from mining_agent_shared.models import ReportRequest, ReportResponse

app = FastAPI(title="Mining Rights Daily Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/reports", response_model=ReportResponse)
def create_report(request: ReportRequest) -> ReportResponse:
    return generate_report(request.query, days=request.days)
