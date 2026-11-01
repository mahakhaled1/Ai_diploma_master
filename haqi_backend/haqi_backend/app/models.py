"""
PostgreSQL SQLAlchemy 2.0 ORM Models for HAQI (حقي).
Implements the 8-field Official Document Metadata Schema (Slide 13),
Service Chunks, Users, Multi-turn Chat Sessions, Messages,
Contradiction Flags (Human-in-the-Loop, Slide 12 & 19), User Feedback,
and Benchmark Evaluation Runs (Slide 18).
"""

from datetime import date, datetime
from typing import Optional

try:
    from sqlalchemy import (
        Boolean,
        Column,
        Date,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        String,
        Text,
    )
    from sqlalchemy.orm import declarative_base, relationship

    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()

    class OfficialDocumentORM(Base):
        """Slide 13: Metadata Schema (حقول البيانات الوصفية الثمانية)."""

        __tablename__ = "official_documents"

        id = Column(Integer, primary_key=True, index=True)
        doc_code = Column(String(64), unique=True, nullable=False, index=True)
        title = Column(String(500), nullable=False)               # 1. عنوان الوثيقة
        authority = Column(String(255), nullable=False, index=True)  # 2. الجهة الحكومية
        original_url = Column(String(1000), nullable=False)       # 3. الرابط الأصلي
        publication_date = Column(String(32), nullable=False)     # 4. تاريخ النشر
        last_updated = Column(String(32), nullable=False)         # 5. تاريخ التحديث
        service_category = Column(String(150), nullable=False, index=True)  # 6. فئة الخدمة
        verification_date = Column(String(32), nullable=False)    # 7. تاريخ التحقق
        version = Column(String(50), nullable=False, default="1.0")  # 8. إصدار الوثيقة
        is_official_verified = Column(Boolean, nullable=False, default=True)
        status = Column(String(50), nullable=False, default="active")
        created_at = Column(DateTime, default=datetime.utcnow)

        chunks = relationship(
            "ServiceChunkORM", back_populates="document", cascade="all, delete-orphan"
        )

    class ServiceChunkORM(Base):
        """Indexed official procedural chunks linked to an OfficialDocumentORM."""

        __tablename__ = "service_chunks"

        id = Column(Integer, primary_key=True, index=True)
        chunk_id = Column(String(64), unique=True, nullable=False, index=True)
        document_id = Column(
            Integer, ForeignKey("official_documents.id", ondelete="CASCADE"), nullable=False
        )
        service_slug = Column(String(100), nullable=False, index=True)
        service_name_ar = Column(String(255), nullable=False)
        sub_type = Column(String(100), default="general")
        intent_tag = Column(String(100), nullable=False, index=True)
        chunk_text = Column(Text, nullable=False)
        steps_json = Column(Text, nullable=False, default="[]")
        required_documents_json = Column(Text, nullable=False, default="[]")
        eligibility_criteria_json = Column(Text, nullable=False, default="[]")
        fees_text = Column(String(500), default="")
        processing_time = Column(String(255), default="")
        keywords_ar = Column(Text, default="")
        created_at = Column(DateTime, default=datetime.utcnow)

        document = relationship("OfficialDocumentORM", back_populates="chunks")

    class UserORM(Base):
        """User record following Data Minimization principles (Slide 19)."""

        __tablename__ = "users"

        user_id = Column(String(100), primary_key=True, index=True)
        role = Column(String(50), nullable=False, default="citizen")
        preferred_dialect = Column(String(50), nullable=False, default="ar-EG")
        created_at = Column(DateTime, default=datetime.utcnow)
        last_active_at = Column(DateTime, default=datetime.utcnow)

    class ChatSessionORM(Base):
        """Multi-turn conversation session supporting Clarification state (Slide 7 & 16)."""

        __tablename__ = "chat_sessions"

        session_id = Column(String(100), primary_key=True, index=True)
        user_id = Column(
            String(100), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
        )
        pending_intent = Column(String(100), nullable=True)
        pending_service_slug = Column(String(100), nullable=True)
        awaiting_clarification = Column(Boolean, nullable=False, default=False)
        clarification_options_json = Column(Text, default="[]")
        is_active = Column(Boolean, nullable=False, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow)

    class ChatMessageORM(Base):
        """Individual turn message stored with grounding citations and latency."""

        __tablename__ = "chat_messages"

        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(
            String(100),
            ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
        role = Column(String(30), nullable=False)
        message_text = Column(Text, nullable=False)
        detected_intent = Column(String(100), nullable=True)
        rewritten_query = Column(Text, nullable=True)
        decision_type = Column(String(50), nullable=True)
        confidence_score = Column(Float, default=0.0)
        citations_json = Column(Text, default="[]")
        retrieval_time_ms = Column(Float, default=0.0)
        total_latency_ms = Column(Float, default=0.0)
        created_at = Column(DateTime, default=datetime.utcnow)

    class ContradictionFlagORM(Base):
        """Human-in-the-loop review queue for conflicting official sources (Slide 12 & 19)."""

        __tablename__ = "contradiction_flags"

        id = Column(Integer, primary_key=True, index=True)
        query_text = Column(Text, nullable=False)
        doc_code_a = Column(String(64), nullable=False)
        doc_code_b = Column(String(64), nullable=False)
        conflict_description = Column(Text, nullable=False)
        status = Column(String(50), nullable=False, default="pending_human_review")
        resolution_notes = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        resolved_at = Column(DateTime, nullable=True)

    class UserFeedbackORM(Base):
        """Citizen feedback on answer quality & citation helpfulness (Slide 14)."""

        __tablename__ = "user_feedback"

        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(100), nullable=False, index=True)
        message_id = Column(Integer, nullable=True)
        rating = Column(Integer, nullable=False)
        is_helpful = Column(Boolean, nullable=False, default=True)
        comment = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

    class EvaluationRunORM(Base):
        """Stores quantitative & qualitative benchmark evaluation runs (Slide 18)."""

        __tablename__ = "evaluation_runs"

        id = Column(Integer, primary_key=True, index=True)
        run_id = Column(String(64), unique=True, nullable=False, index=True)
        dataset_version = Column(String(50), nullable=False)
        total_cases = Column(Integer, nullable=False)
        recall_at_k = Column(Float, nullable=False)
        mrr = Column(Float, nullable=False)
        ndcg_at_k = Column(Float, nullable=False)
        faithfulness = Column(Float, nullable=False)
        answer_accuracy = Column(Float, nullable=False)
        citation_precision = Column(Float, nullable=False)
        abstention_quality = Column(Float, nullable=False)
        unsupported_claim_rate = Column(Float, nullable=False)
        avg_retrieval_time_ms = Column(Float, nullable=False)
        avg_response_latency_ms = Column(Float, nullable=False)
        detailed_results_json = Column(Text, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None
