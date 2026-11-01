"""
Evidence Validation & Safe Abstention Engine (Slide 12, 19, 22).
Developed by Maha in collaboration with Hassan (RAG Lead):
- هوية المصدر (Source Identity): التحقق من تبعية الوثيقة لجهة رسمية معتمدة.
- فحص الصلة (Relevance Check): مطابقة الدليل المسترجع مع سؤال المواطن.
- تتبع التواريخ (Date Tracking): رصد تاريخ النشر وآخر تحديث متاح.
- كشف التعارض (Contradiction Detection): رصد التناقضات وتحويلها للمراجعة البشرية.
- المسار 1: توفر أدلة كافية (Sufficient Evidence) -> سياق موثق (Verified Context) -> إجابة مدعومة بالمصادر والروابط.
- المسار 2: عدم كفاية الأدلة (Insufficient Evidence) -> منع التخمين التوليدي -> طلب توضيح أو امتناع آمن (Safe Abstention).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config import settings
from app.database import db_manager
from app.schemas import EvidenceValidationReport, NLPAnalysisResult
from app.services.nlp_integration import normalize_arabic_text


class EvidenceValidationService:
    """Implements the 4-pillar Evidence Validation & Safe Abstention mechanism (Slide 12)."""

    def validate_evidence(
        self,
        nlp_result: NLPAnalysisResult,
        retrieved_chunks: List[Dict[str, Any]],
        proposed_answer: Optional[str] = None,
    ) -> EvidenceValidationReport:
        # 1. Guardrail: Legal Fatwa / Litigation Strategy Request -> Immediate Safe Abstention (Slide 19)
        if nlp_result.is_legal_opinion_request:
            return EvidenceValidationReport(
                is_sufficient=False,
                decision_path="path_2_safe_abstention",
                source_identity_verified=False,
                relevance_passed=False,
                max_relevance_score=0.0,
                grounding_score=0.0,
                freshness_status="not_applicable",
                contradiction_detected=False,
                abstention_reason=(
                    "امتناع آمن (Safe Abstention): نظام «حقي» يقدم إرشاداً إجرائياً مبنياً على اللوائح الحكومية الرسمية فقط، "
                    "ولا يقدم فتاوى قانونية أو استشارات قضائية في النزاعات. يُرجى استشارة محامٍ مختص أو التوجه للمساعدة القضائية."
                ),
            )

        # 2. Path 2a: Ambiguous procedural query -> Request Clarification instead of guessing (Slide 7, 12, 16)
        if nlp_result.needs_clarification:
            return EvidenceValidationReport(
                is_sufficient=False,
                decision_path="path_2_clarification",
                source_identity_verified=True,
                relevance_passed=True,
                max_relevance_score=0.75,
                grounding_score=1.0,
                freshness_status="verified_up_to_date",
                contradiction_detected=False,
                abstention_reason=(
                    "طلب توضيح لمنع التخمين التوليدي: السؤال يحتمل أكثر من إجراء فرعي مختلف في المستندات والخطوات."
                ),
            )

        # 3. Check if out-of-scope or no retrieved chunks
        if nlp_result.is_out_of_scope or not retrieved_chunks:
            return EvidenceValidationReport(
                is_sufficient=False,
                decision_path="path_2_safe_abstention",
                source_identity_verified=False,
                relevance_passed=False,
                max_relevance_score=retrieved_chunks[0]["rerank_score"] if retrieved_chunks else 0.0,
                grounding_score=0.0,
                freshness_status="no_verified_source",
                contradiction_detected=False,
                abstention_reason=(
                    "امتناع آمن (Safe Abstention): لا يتوفر دليل رسمي موثق في قاعدة المعرفة الحكومية يجيب على هذا الاستفسار بدقة. "
                    "يمتنع النظام عن التوليد التخميني حفاظاً على موثوقية المعلومة."
                ),
            )

        top_chunk = retrieved_chunks[0]
        max_rel_score = float(top_chunk.get("rerank_score", 0.0))

        # Pillar 1: هوية المصدر (Source Identity Verification)
        source_verified = self._verify_source_authority(top_chunk)

        # Pillar 2: فحص الصلة (Relevance Check against threshold)
        relevance_passed = max_rel_score >= settings.min_relevance_score

        # Pillar 3: تتبع التواريخ (Date & Freshness Tracking)
        freshness_status = self._check_source_freshness(top_chunk)

        # Pillar 4: كشف التعارض (Contradiction Detection across chunks of same service/subtype)
        contradiction_detected, contradiction_details = self._detect_contradictions(
            nlp_result.original_text, retrieved_chunks
        )

        # Grounding Score calculation (verifies proposed answer or chunk completeness)
        grounding_score = self._compute_grounding_score(top_chunk, proposed_answer)

        # If Contradiction is detected -> Safe Abstention & Route to Human Review (Slide 12, 19, 22)
        if contradiction_detected:
            return EvidenceValidationReport(
                is_sufficient=False,
                decision_path="path_2_safe_abstention",
                source_identity_verified=source_verified,
                relevance_passed=relevance_passed,
                max_relevance_score=max_rel_score,
                grounding_score=grounding_score,
                freshness_status=freshness_status,
                contradiction_detected=True,
                contradiction_details=contradiction_details,
                abstention_reason=(
                    "امتناع آمن بسبب تعارض المصادر (Conflicting Sources): تم رصد تعارض بين وثيقتين وإحالة الموضوع للمراجعة البشرية."
                ),
            )

        # If Source is not official, Relevance is too low, or Source is expired -> Safe Abstention
        if (
            not source_verified
            or not relevance_passed
            or freshness_status == "outdated_unverified"
            or grounding_score < settings.min_grounding_score
        ):
            reason = "امتناع آمن (Safe Abstention): الأدلة المسترجعة غير كافية أو غير معتمدة رسمياً."
            if not source_verified:
                reason = "امتناع آمن: الوثيقة المسترجعة لا تنتمي لجهة حكومية رسمية معتمدة."
            elif freshness_status == "outdated_unverified":
                reason = "امتناع آمن: الوثيقة المسترجعة قديمة وتجاوزت فترة التحقق المسموحة."
            elif grounding_score < settings.min_grounding_score:
                reason = "امتناع آمن: الإجابة المقترحة تتضمن ادعاءات غير مسندة للدليل الرسمي."

            return EvidenceValidationReport(
                is_sufficient=False,
                decision_path="path_2_safe_abstention",
                source_identity_verified=source_verified,
                relevance_passed=relevance_passed,
                max_relevance_score=max_rel_score,
                grounding_score=grounding_score,
                freshness_status=freshness_status,
                contradiction_detected=False,
                abstention_reason=reason,
            )

        # Path 1: Sufficient Evidence -> Verified Context
        return EvidenceValidationReport(
            is_sufficient=True,
            decision_path="path_1_verified_context",
            source_identity_verified=True,
            relevance_passed=True,
            max_relevance_score=max_rel_score,
            grounding_score=grounding_score,
            freshness_status=freshness_status,
            contradiction_detected=False,
            abstention_reason=None,
        )

    def _verify_source_authority(self, chunk: Dict[str, Any]) -> bool:
        if not chunk.get("is_official_verified", False):
            return False
        authority = chunk.get("authority", "")
        url = chunk.get("original_url", "")
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        domain_ok = any( domain == td or domain.endswith("." + td) for td in settings.trusted_domains )
        auth_ok = any(ta in authority for ta in settings.trusted_authorities)
        return domain_ok and auth_ok

    def _check_source_freshness(self, chunk: Dict[str, Any]) -> str:
        last_updated_str = chunk.get("last_updated", "2025-01-01")
        try:
            updated_dt = datetime.strptime(last_updated_str, "%Y-%m-%d")
            age_days = (datetime.utcnow() - updated_dt).days
            if age_days > settings.max_doc_age_days:
                return "outdated_unverified"
            return "verified_up_to_date"
        except ValueError:
            return "verified_up_to_date"

    def _detect_contradictions(
        self, query_text: str, chunks: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Detects if two high-scoring chunks for the exact same intent & subtype contradict on fees or steps."""
        if len(chunks) < 2:
            return False, None
        first, second = chunks[0], chunks[1]
        if (
            first.get("intent_tag") == second.get("intent_tag")
            and first.get("sub_type") == second.get("sub_type")
            and first.get("doc_code") != second.get("doc_code")
            and second.get("rerank_score", 0.0) >= settings.min_relevance_score
        ):
            if first.get("fees_text") != second.get("fees_text") or first.get("steps") != second.get("steps"):
                desc = (
                    f"تعارض مرصود في إجراءات/رسوم ({first.get('service_name_ar')}) "
                    f"بين الوثيقة {first.get('doc_code')} والوثيقة {second.get('doc_code')}."
                )
                db_manager.create_contradiction_flag(
                    query_text=query_text,
                    doc_code_a=first.get("doc_code", "DOC-A"),
                    doc_code_b=second.get("doc_code", "DOC-B"),
                    conflict_description=desc,
                )
                return True, desc
        return False, None

    def _compute_grounding_score(
        self, top_chunk: Dict[str, Any], proposed_answer: Optional[str] = None
    ) -> float:
        if not proposed_answer:
            # Grounded generation directly from verified chunk structure has 1.0 faithfulness
            return 1.0 if top_chunk.get("steps") and top_chunk.get("required_documents") else 0.75

        evidence_text = " ".join(
            [
                top_chunk.get("service_name_ar", ""),
                top_chunk.get("chunk_text", ""),
                top_chunk.get("authority", ""),
                " ".join(top_chunk.get("steps", [])),
                " ".join(top_chunk.get("required_documents", [])),
            ]
        )
        ev_tokens = set(normalize_arabic_text(evidence_text).split())
        ans_tokens = [
            t
            for t in normalize_arabic_text(proposed_answer).split()
            if len(t) > 2
        ]
        if not ans_tokens:
            return 0.0
        overlap = sum(1 for t in ans_tokens if t in ev_tokens)
        return round(min(1.0, overlap / max(len(ans_tokens), 1)), 4)


evidence_validator = EvidenceValidationService()
