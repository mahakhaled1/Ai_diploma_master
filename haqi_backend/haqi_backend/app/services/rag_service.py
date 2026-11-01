"""
End-to-End RAG Orchestrator & User Journey Service (Slide 7, 10, 16).
Coordinates:
Step 1: User Query (إدخال السؤال بالعربية)
Step 2: Query Understanding (فهم القصد وتحديد المعلومات الناقصة - Ahmed Rabie's module)
Step 3: Document Retrieval (البحث الهجين في المصادر الرسمية - Anas's module)
Step 4: Context Selection & Reranking (ترتيب وتدقيق الأدلة)
Step 5: Evidence Validation & Safe Abstention (التحقق والامتناع الآمن - Maha & Hassan)
Step 6: Grounded Answer Generation (توليد إجابة مهيكلة مبسطة)
Step 7: Source Citation & Session Logging (إرفاق المصادر والخطوات وحفظ الجلسة)
"""

import time
from typing import Any, Dict, List, Optional

from app.database import db_manager
from app.schemas import (
    ChatRequest,
    ChatResponse,
    SourceCitation,
    StructuredGuidance,
)
from app.services.evidence_validator import evidence_validator
from app.services.nlp_integration import nlp_service
from app.services.retrieval_integration import retrieval_service


class RAGOrchestratorService:
    """Orchestrates the 7-stage RAG pipeline and 9-step citizen user journey."""

    def process_citizen_query(self, request: ChatRequest) -> ChatResponse:
        start_total = time.perf_counter()

        # 1. User & Multi-turn Session Resolution
        session = db_manager.get_or_create_session(
            user_id=request.user_id, session_id=request.session_id
        )
        session_id = session["session_id"]

        # Log incoming citizen message
        db_manager.log_chat_message(
            session_id=session_id,
            role="user",
            message_text=request.question,
        )

        # 2. Arabic NLP & Query Understanding (Slide 9)
        nlp_result = nlp_service.analyze_query(
            user_query=request.question,
            pending_intent=session.get("pending_intent"),
            awaiting_clarification=session.get("awaiting_clarification", False),
        )

        # 3 & 4. Hybrid Retrieval & Cross-Encoder Reranking (Slide 11)
        t_ret_start = time.perf_counter()
        retrieved_chunks = retrieval_service.retrieve_and_rerank(
            nlp_result=nlp_result,
            service_category_filter=request.service_category,
            top_k=3,
        )
        retrieval_time_ms = round((time.perf_counter() - t_ret_start) * 1000.0, 3)

        # 5. Evidence Validation & Safe Abstention (Slide 12)
        validation_report = evidence_validator.validate_evidence(
            nlp_result=nlp_result,
            retrieved_chunks=retrieved_chunks,
        )

        # Handle Path 2a: Clarification Needed (Slide 7 Step 4 & Slide 16)
        if validation_report.decision_path == "path_2_clarification":
            db_manager.update_session_clarification(
                session_id=session_id,
                awaiting=True,
                pending_intent=nlp_result.extracted_intent,
                pending_service_slug="national-id",
                options=nlp_result.clarification_options,
            )
            total_latency_ms = round((time.perf_counter() - start_total) * 1000.0, 3)
            answer_text = nlp_result.clarification_question or "يرجى توضيح نوع الإجراء المطلوب."

            db_manager.log_chat_message(
                session_id=session_id,
                role="assistant",
                message_text=answer_text,
                detected_intent=nlp_result.extracted_intent,
                rewritten_query=nlp_result.structured_search_query,
                decision_type="clarification_needed",
                confidence_score=validation_report.max_relevance_score,
                citations=[],
                retrieval_time_ms=retrieval_time_ms,
                total_latency_ms=total_latency_ms,
            )

            return ChatResponse(
                status="success",
                session_id=session_id,
                user_id=request.user_id,
                received_question=request.question,
                decision_type="clarification_needed",
                answer=answer_text,
                structured_guidance=None,
                clarification_question=nlp_result.clarification_question,
                clarification_options=nlp_result.clarification_options,
                sources=["قطاع الأحوال المدنية - وزارة الداخلية"],
                citations=[],
                nlp_analysis=nlp_result,
                evidence_validation=validation_report,
                metrics={
                    "retrieval_time_ms": retrieval_time_ms,
                    "response_latency_ms": total_latency_ms,
                },
            )

        # Clear any pending clarification state once resolved or abstained
        db_manager.update_session_clarification(session_id=session_id, awaiting=False)

        # Handle Path 2b: Safe Abstention (Slide 12 & 19)
        if not validation_report.is_sufficient:
            total_latency_ms = round((time.perf_counter() - start_total) * 1000.0, 3)
            abstention_msg = (
                validation_report.abstention_reason
                or "امتناع آمن: لا تتوفر وثيقة رسمية موثقة للإجابة على هذا السؤال."
            )
            db_manager.log_chat_message(
                session_id=session_id,
                role="assistant",
                message_text=abstention_msg,
                detected_intent=nlp_result.extracted_intent,
                rewritten_query=nlp_result.structured_search_query,
                decision_type="safe_abstention",
                confidence_score=validation_report.max_relevance_score,
                citations=[],
                retrieval_time_ms=retrieval_time_ms,
                total_latency_ms=total_latency_ms,
            )
            return ChatResponse(
                status="abstention",
                session_id=session_id,
                user_id=request.user_id,
                received_question=request.question,
                decision_type="safe_abstention",
                answer=abstention_msg,
                structured_guidance=None,
                sources=[],
                citations=[],
                nlp_analysis=nlp_result,
                evidence_validation=validation_report,
                metrics={
                    "retrieval_time_ms": retrieval_time_ms,
                    "response_latency_ms": total_latency_ms,
                },
            )

        # Handle Path 1: Verified Context -> Structured Grounded Answer (Slide 16)
        primary_chunk = retrieved_chunks[0]
        citation = SourceCitation(
            doc_code=primary_chunk["doc_code"],
            title=primary_chunk["doc_title"],
            authority=primary_chunk["authority"],
            original_url=primary_chunk["original_url"],
            last_updated=primary_chunk["last_updated"],
            verification_date=primary_chunk["verification_date"],
            version=primary_chunk["version"],
            verification_status="موثق رسمياً (Verified Official Source)",
            relevance_score=primary_chunk["rerank_score"],
        )

        ref_summary = (
            f"{primary_chunk['doc_title']} ({primary_chunk['original_url']}) — "
            f"آخر تحديث: {primary_chunk['last_updated']} | تاريخ التحقق: {primary_chunk['verification_date']}"
        )

        structured_guidance = StructuredGuidance(
            specific_service=primary_chunk["service_name_ar"],
            procedural_steps=primary_chunk["steps"],
            required_documents=primary_chunk["required_documents"],
            responsible_authority=primary_chunk["authority"],
            fees_and_duration=f"الرسوم: {primary_chunk['fees_text']} | المدة: {primary_chunk['processing_time']}",
            reference_and_verification=ref_summary,
        )

        formatted_answer = self._format_arabic_answer(structured_guidance)
        total_latency_ms = round((time.perf_counter() - start_total) * 1000.0, 3)

        db_manager.log_chat_message(
            session_id=session_id,
            role="assistant",
            message_text=formatted_answer,
            detected_intent=nlp_result.extracted_intent,
            rewritten_query=nlp_result.structured_search_query,
            decision_type="answered",
            confidence_score=validation_report.max_relevance_score,
            citations=[citation.model_dump()],
            retrieval_time_ms=retrieval_time_ms,
            total_latency_ms=total_latency_ms,
        )

        return ChatResponse(
            status="success",
            session_id=session_id,
            user_id=request.user_id,
            received_question=request.question,
            decision_type="answered",
            answer=formatted_answer,
            structured_guidance=structured_guidance,
            sources=[
                f"{primary_chunk['authority']} — {primary_chunk['doc_title']} ({primary_chunk['original_url']})"
            ],
            citations=[citation],
            nlp_analysis=nlp_result,
            evidence_validation=validation_report,
            metrics={
                "retrieval_time_ms": retrieval_time_ms,
                "response_latency_ms": total_latency_ms,
            },
        )

    def _format_arabic_answer(self, guidance: StructuredGuidance) -> str:
        steps_str = "\n".join(
            f"  {i+1}. {s}" for i, s in enumerate(guidance.procedural_steps)
        )
        docs_str = "\n".join(f"  - {d}" for d in guidance.required_documents)
        return (
            f"• الخدمة المحددة: {guidance.specific_service}\n"
            f"• الخطوات الإجرائية:\n{steps_str}\n"
            f"• قائمة المستندات المطلوبة:\n{docs_str}\n"
            f"• الجهة المسؤولة: {guidance.responsible_authority}\n"
            f"• الرسوم والمدة الزمنية: {guidance.fees_and_duration}\n"
            f"• المرجع وحالة التحقق: {guidance.reference_and_verification}\n"
            f"* {guidance.methodological_note}"
        )


rag_service = RAGOrchestratorService()
