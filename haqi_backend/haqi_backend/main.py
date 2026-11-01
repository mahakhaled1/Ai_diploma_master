"""
HAQI | حقي — المساعد الذكي للخدمات والحقوق العامة
FastAPI Backend Application, Database Integration, Evidence Validation & Evaluation API
Lead Developer: Maha — Backend, Database & Evaluation
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager
from app.evaluation.evaluator import evaluator
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ContradictionResolveRequest,
    CreateDocumentRequest,
    DocumentMetadataSchema,
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    EvaluationMetricsSummary,
    FeedbackRequest,
    SourceCitation,
    StandaloneValidationRequest,
)
from app.services.evidence_validator import evidence_validator
from app.services.nlp_integration import nlp_service, normalize_arabic_text
from app.services.rag_service import rag_service
from app.services.retrieval_integration import retrieval_service

app = FastAPI(
    title="Haqi Egypt Service Guide - Backend API",
    description=(
        "حقي (HAQI) — المساعد الذكي للخدمات والحقوق العامة. "
        "FastAPI Backend, PostgreSQL Metadata Registry, Hybrid RAG Integration, "
        "Evidence Validation, Safe Abstention & Benchmark Evaluation."
    ),
    version=settings.app_version,
)

# Enable CORS for Heba's Arabic RTL Frontend & Mobile Interface (Slide 14 & 20)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 1. Health & System Status Endpoints
# ============================================================================
@app.get("/", tags=["Health & System Status"])
def read_root():
    """Root health-check endpoint preserving backward compatibility with initial contract."""
    return {
        "status": "online",
        "developer": "Maha",
        "project": "HAQI | حقي — المساعد الذكي للخدمات والحقوق العامة",
        "version": settings.app_version,
        "database_engine": db_manager.engine_type,
    }


@app.get("/api/v1/health", tags=["Health & System Status"])
def health_check():
    docs = db_manager.list_documents()
    chunks = db_manager.get_all_chunks_with_docs()
    return {
        "status": "healthy",
        "developer": "Maha",
        "database_engine": db_manager.engine_type,
        "official_documents_count": len(docs),
        "indexed_chunks_count": len(chunks),
        "modules": {
            "arabic_nlp": "active",
            "hybrid_retrieval": "active",
            "evidence_validation": "active",
            "safe_abstention": "active",
            "evaluation_engine": "active",
        },
    }


# ============================================================================
# 2. Core Citizen Chat & Multi-Turn RAG Endpoint (Slide 7, 10, 12, 16)
# ============================================================================
@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Citizen Chat & RAG"])
def process_chat_query(request: ChatRequest):
    """
    Executes the full 9-step citizen user journey:
    Arabic NLP & Dialect Mapping -> Clarification Check -> Hybrid Retrieval & Reranking ->
    Evidence Validation & Safe Abstention -> Structured Grounded Answer with Official Citations.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Invalid question: السؤال فارغ")

    return rag_service.process_citizen_query(request)


# ============================================================================
# 3. User & Session Management Endpoints (Slide 19: Privacy & Data Minimization)
# ============================================================================
@app.post("/api/v1/sessions", tags=["Users & Sessions"])
def create_or_get_session(user_id: str = "guest_user", session_id: Optional[str] = None):
    session = db_manager.get_or_create_session(user_id=user_id, session_id=session_id)
    return {"status": "success", "session": session}


@app.get("/api/v1/sessions/{session_id}", tags=["Users & Sessions"])
def get_session_details(session_id: str):
    history = db_manager.get_session_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "session": history}


@app.delete("/api/v1/sessions/{session_id}", tags=["Users & Sessions"])
def delete_user_session(session_id: str):
    """Deletes session history in compliance with Data Minimization & Privacy (Slide 19)."""
    deleted = db_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "status": "deleted",
        "session_id": session_id,
        "message": "تم حذف الجلسة وبيانات المحادثة بنجاح التزاماً بضوابط الخصوصية وتقليل البيانات.",
    }


# ============================================================================
# 4. Government Services Navigator & Eligibility Checker (Slide 8 & 20)
# ============================================================================
@app.get("/api/v1/services", tags=["Government Services Explorer"])
def list_government_services(
    category: Optional[str] = Query(default=None, description="تصفية حسب فئة الخدمة")
):
    """Lists all structured government procedures for the Frontend Procedure Navigator."""
    chunks = db_manager.get_all_chunks_with_docs(service_category=category)
    return {
        "status": "success",
        "count": len(chunks),
        "services": [
            {
                "chunk_id": c["chunk_id"],
                "service_slug": c["service_slug"],
                "service_name_ar": c["service_name_ar"],
                "sub_type": c["sub_type"],
                "service_category": c["service_category"],
                "authority": c["authority"],
                "steps": c["steps"],
                "required_documents": c["required_documents"],
                "eligibility_criteria": c["eligibility_criteria"],
                "fees_text": c["fees_text"],
                "processing_time": c["processing_time"],
                "source_url": c["original_url"],
                "last_updated": c["last_updated"],
                "verification_date": c["verification_date"],
            }
            for c in chunks
        ],
    }


@app.get("/api/v1/services/{service_slug}", tags=["Government Services Explorer"])
def get_service_procedure(
    service_slug: str,
    sub_type: Optional[str] = Query(default=None, description="first_time | renewal | replacement | general"),
):
    matches = db_manager.get_service_by_slug(service_slug=service_slug, sub_type=sub_type)
    if not matches:
        raise HTTPException(status_code=404, detail=f"Service '{service_slug}' not found")
    return {"status": "success", "service_slug": service_slug, "procedures": matches}


@app.post(
    "/api/v1/services/{service_slug}/check-eligibility",
    response_model=EligibilityCheckResponse,
    tags=["Government Services Explorer"],
)
def check_service_eligibility_and_documents(
    service_slug: str, request: EligibilityCheckRequest
):
    """Interactive Eligibility & Missing Documents Checker (Slide 8 Item 7)."""
    matches = db_manager.get_service_by_slug(
        service_slug=service_slug, sub_type=request.sub_type
    )
    if not matches:
        raise HTTPException(status_code=404, detail=f"Service '{service_slug}' not found")

    target = matches[0]
    req_docs: List[str] = target["required_documents"]
    user_docs_norm = [normalize_arabic_text(d) for d in request.available_documents]

    matched_docs: List[str] = []
    missing_docs: List[str] = []
    for req_doc in req_docs:
        req_norm = normalize_arabic_text(req_doc)
        req_tokens = [t for t in req_norm.split() if len(t) > 2]
        is_present = any(
            any(tok in u_doc for tok in req_tokens[:3]) for u_doc in user_docs_norm
        )
        if is_present:
            matched_docs.append(req_doc)
        else:
            missing_docs.append(req_doc)

    is_eligible = True
    eligibility_notes = list(target["eligibility_criteria"])
    if request.age is not None:
        if service_slug == "national-id" and request.age < 15:
            is_eligible = False
            eligibility_notes.append(
                f"تنبيه أهلية: السن المدخل ({request.age} سنة) أقل من السن القانوني لاستخراج بطاقة الرقم القومي (15 عاماً)."
            )
        elif service_slug == "notary-power-of-attorney" and request.age < 21:
            is_eligible = False
            eligibility_notes.append(
                f"تنبيه أهلية: السن المدخل ({request.age} سنة) أقل من سن الرشد القانوني لتحرير توكيل (21 عاماً)."
            )

    readiness = round((len(matched_docs) / max(len(req_docs), 1)) * 100.0, 1)

    return EligibilityCheckResponse(
        service_slug=service_slug,
        service_name_ar=target["service_name_ar"],
        sub_type=target["sub_type"],
        is_eligible=is_eligible,
        eligibility_notes=eligibility_notes,
        required_documents=req_docs,
        matched_documents=matched_docs,
        missing_documents=missing_docs,
        readiness_percentage=readiness,
        official_reference=SourceCitation(
            doc_code=target["doc_code"],
            title=target["doc_title"],
            authority=target["authority"],
            original_url=target["original_url"],
            last_updated=target["last_updated"],
            verification_date=target["verification_date"],
            version=target["version"],
            relevance_score=1.0,
        ),
    )


# ============================================================================
# 5. Official Documents & Metadata Registry Endpoints (Slide 13)
# ============================================================================
@app.get(
    "/api/v1/documents",
    response_model=List[DocumentMetadataSchema],
    tags=["Knowledge Base & Metadata Registry"],
)
def list_official_documents(category: Optional[str] = None):
    """Returns all official government documents with the 8 Metadata Schema fields (Slide 13)."""
    return db_manager.list_documents(service_category=category)


@app.post(
    "/api/v1/documents",
    response_model=DocumentMetadataSchema,
    tags=["Knowledge Base & Metadata Registry"],
)
def register_official_document(doc: CreateDocumentRequest):
    """Registers or updates an official document in the Metadata Registry."""
    return db_manager.create_document(doc.model_dump())


# ============================================================================
# 6. Evidence Validation, Safe Abstention & Contradiction Review (Slide 12 & 19)
# ============================================================================
@app.post("/api/v1/validate", tags=["Evidence Validation & Safety"])
def validate_evidence_endpoint(request: StandaloneValidationRequest):
    """Standalone endpoint to test Evidence Validation & Safe Abstention on any query/answer pair."""
    nlp_res = nlp_service.analyze_query(request.question)
    if request.candidate_chunk_ids:
        all_chunks = db_manager.get_all_chunks_with_docs()
        selected = [
            c for c in all_chunks if c["chunk_id"] in request.candidate_chunk_ids
        ]
        chunks = retrieval_service.retrieve_and_rerank(
            nlp_result=nlp_res, custom_chunks=selected, top_k=len(selected) or 1
        )
    else:
        chunks = retrieval_service.retrieve_and_rerank(nlp_result=nlp_res, top_k=3)

    report = evidence_validator.validate_evidence(
        nlp_result=nlp_res,
        retrieved_chunks=chunks,
        proposed_answer=request.proposed_answer,
    )
    return {
        "status": "success",
        "nlp_analysis": nlp_res,
        "evidence_validation": report,
        "top_candidate_chunks": [
            {
                "chunk_id": c["chunk_id"],
                "doc_code": c["doc_code"],
                "service_name_ar": c["service_name_ar"],
                "rerank_score": c["rerank_score"],
            }
            for c in chunks
        ],
    }


@app.get("/api/v1/contradictions", tags=["Evidence Validation & Safety"])
def list_contradictions():
    """Lists source contradictions flagged for human review (Slide 8 Item 10, Slide 12, Slide 19)."""
    flags = db_manager.list_contradiction_flags()
    return {"status": "success", "count": len(flags), "contradiction_flags": flags}


@app.post("/api/v1/contradictions/{flag_id}/resolve", tags=["Evidence Validation & Safety"])
def resolve_contradiction(flag_id: int, request: ContradictionResolveRequest):
    resolved = db_manager.resolve_contradiction_flag(
        flag_id=flag_id,
        resolution_notes=request.resolution_notes,
        preferred_doc_code=request.preferred_doc_code,
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Contradiction flag not found")
    return {"status": "resolved", "flag": resolved}


# ============================================================================
# 7. User Feedback & Benchmark Evaluation Endpoints (Slide 14 & 18)
# ============================================================================
@app.post("/api/v1/feedback", tags=["Evaluation & Monitoring"])
def submit_user_feedback(request: FeedbackRequest):
    saved = db_manager.save_feedback(request.model_dump())
    return {"status": "success", "feedback": saved}


@app.post(
    "/api/v1/evaluation/run",
    response_model=EvaluationMetricsSummary,
    tags=["Evaluation & Monitoring"],
)
def run_benchmark_evaluation():
    """Runs the HAQI Benchmark Dataset and computes Retrieval, Quality, Safety & Latency metrics."""
    return evaluator.run_benchmark(top_k=3)


@app.get(
    "/api/v1/evaluation/report",
    response_model=EvaluationMetricsSummary,
    tags=["Evaluation & Monitoring"],
)
def get_latest_evaluation_report():
    """Returns the most recent benchmark evaluation report (runs benchmark if none exists yet)."""
    latest = db_manager.get_latest_evaluation_run()
    if latest:
        return EvaluationMetricsSummary(**latest)
    return evaluator.run_benchmark(top_k=3)
