"""
Pydantic Schemas for HAQI Backend APIs (Compatible with both Pydantic v1 and v2).
Covers Chat, Structured Guidance (Slide 16), Metadata Schema (Slide 13),
Sessions, Eligibility Check (Slide 8), Evidence Validation (Slide 12),
Contradiction Review (Slide 19), User Feedback (Slide 14), and Evaluation (Slide 18).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HaqiBaseModel(BaseModel):
    """Base schema providing unified `.model_dump()` across Pydantic v1 and v2."""

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        if hasattr(super(), "model_dump"):
            return super().model_dump(*args, **kwargs)
        return self.dict(*args, **kwargs)


# ============================================================================
# 1. Official Document & Metadata Registry Schemas (Slide 13)
# ============================================================================
class DocumentMetadataSchema(HaqiBaseModel):
    doc_code: str = Field(..., description="Unique document identifier code")
    title: str = Field(..., description="1. عنوان الوثيقة (Title)")
    authority: str = Field(..., description="2. الجهة الحكومية (Authority)")
    original_url: str = Field(..., description="3. الرابط الأصلي (Original URL)")
    publication_date: str = Field(..., description="4. تاريخ النشر (Publication Date)")
    last_updated: str = Field(..., description="5. تاريخ التحديث (Last Updated)")
    service_category: str = Field(..., description="6. فئة الخدمة (Service Category)")
    verification_date: str = Field(..., description="7. تاريخ التحقق (Verification Date)")
    version: str = Field(default="1.0", description="8. إصدار الوثيقة (Version)")
    is_official_verified: bool = Field(default=True)
    status: str = Field(default="active")


class CreateDocumentRequest(DocumentMetadataSchema):
    pass


# ============================================================================
# 2. Structured Answer & Citation Schemas (Slide 10, 12, 16)
# ============================================================================
class SourceCitation(HaqiBaseModel):
    doc_code: str
    title: str
    authority: str
    original_url: str
    last_updated: str
    verification_date: str
    version: str
    verification_status: str = "موثق رسمياً (Verified Official Source)"
    relevance_score: float = 0.0


class StructuredGuidance(HaqiBaseModel):
    """Matches Slide 16: إجابة حقي المهيكلة."""

    specific_service: str = Field(..., description="الخدمة المحددة")
    procedural_steps: List[str] = Field(
        default_factory=list, description="الخطوات الإجرائية"
    )
    required_documents: List[str] = Field(
        default_factory=list, description="قائمة المستندات"
    )
    responsible_authority: str = Field(..., description="الجهة المسؤولة")
    fees_and_duration: Optional[str] = Field(
        default=None, description="الرسوم والمدة الزمنية"
    )
    reference_and_verification: str = Field(..., description="المرجع وحالة التحقق")
    methodological_note: str = Field(
        default="تنبيه منهجي: يجب دائماً التحقق من المتطلبات الدقيقة والرسوم مقابل أحدث المصادر الرسمية وقت طلب الخدمة.",
        description="Slide 6 & 19 methodological disclaimer",
    )


# ============================================================================
# 3. Chat & User Journey Schemas (Slide 7, 9, 10, 16)
# ============================================================================
class ChatRequest(HaqiBaseModel):
    question: str = Field(
        ..., description="سؤال المواطن باللغة العربية الفصحى أو العامية المصرية"
    )
    user_id: str = Field(default="guest_user", description="معرف المستخدم")
    session_id: Optional[str] = Field(default=None, description="معرف جلسة المحادثة")
    service_category: Optional[str] = Field(
        default=None, description="تصفية اختيارية حسب فئة الخدمة"
    )


class NLPAnalysisResult(HaqiBaseModel):
    """Slide 9: وحدة فهم اللغة العربية واللهجة المصرية."""

    original_text: str
    normalized_text: str
    detected_dialect_terms: Dict[str, str] = Field(default_factory=dict)
    extracted_intent: str
    extracted_intent_ar: str
    sub_type: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    structured_search_query: str
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    is_legal_opinion_request: bool = False
    is_out_of_scope: bool = False


class EvidenceValidationReport(HaqiBaseModel):
    """Slide 12: آلية ضمان الموثوقية والامتناع الآمن."""

    is_sufficient: bool
    decision_path: str = Field(
        ...,
        description="path_1_verified_context | path_2_clarification | path_2_safe_abstention",
    )
    source_identity_verified: bool
    relevance_passed: bool
    max_relevance_score: float
    grounding_score: float
    freshness_status: str
    contradiction_detected: bool = False
    contradiction_details: Optional[str] = None
    abstention_reason: Optional[str] = None


class ChatResponse(HaqiBaseModel):
    status: str = "success"
    session_id: str
    user_id: str
    received_question: str
    decision_type: str = Field(
        ..., description="answered | clarification_needed | safe_abstention"
    )
    answer: str
    structured_guidance: Optional[StructuredGuidance] = None
    clarification_question: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    citations: List[SourceCitation] = Field(default_factory=list)
    nlp_analysis: NLPAnalysisResult
    evidence_validation: EvidenceValidationReport
    metrics: Dict[str, float] = Field(default_factory=dict)


# ============================================================================
# 4. Eligibility & Missing Documents Checker (Slide 8 Item 7)
# ============================================================================
class EligibilityCheckRequest(HaqiBaseModel):
    sub_type: str = Field(
        default="general",
        description="نوع الإجراء الفرعي (first_time, renewal, replacement, general)",
    )
    age: Optional[int] = Field(default=None, description="عمر المتقدم بالسنوات")
    available_documents: List[str] = Field(
        default_factory=list, description="قائمة المستندات المتوفرة لدى المواطن حالياً"
    )


class EligibilityCheckResponse(HaqiBaseModel):
    service_slug: str
    service_name_ar: str
    sub_type: str
    is_eligible: bool
    eligibility_notes: List[str]
    required_documents: List[str]
    matched_documents: List[str]
    missing_documents: List[str]
    readiness_percentage: float
    official_reference: SourceCitation


# ============================================================================
# 5. Standalone Evidence Validation Request (Slide 12)
# ============================================================================
class StandaloneValidationRequest(HaqiBaseModel):
    question: str
    candidate_chunk_ids: Optional[List[str]] = None
    proposed_answer: Optional[str] = None


# ============================================================================
# 6. Contradiction Resolution & User Feedback Schemas (Slide 14 & 19)
# ============================================================================
class ContradictionResolveRequest(HaqiBaseModel):
    resolution_notes: str
    preferred_doc_code: str


class FeedbackRequest(HaqiBaseModel):
    session_id: str
    message_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    is_helpful: bool = True
    comment: Optional[str] = None


# ============================================================================
# 7. Benchmark Evaluation Report Schema (Slide 18)
# ============================================================================
class EvaluationMetricsSummary(HaqiBaseModel):
    run_id: str
    dataset_version: str
    total_cases: int
    # 1. كفاءة الاسترجاع (Retrieval Efficiency)
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    # 2. جودة الإجابة (Answer Quality)
    faithfulness: float
    answer_accuracy: float
    citation_precision: float
    # 3. الأمان والموثوقية (Safety & Reliability)
    abstention_quality: float
    unsupported_claim_rate: float
    # 4. الأداء الزمني (Temporal Performance)
    avg_retrieval_time_ms: float
    avg_response_latency_ms: float
    case_results: List[Dict[str, Any]] = Field(default_factory=list)
