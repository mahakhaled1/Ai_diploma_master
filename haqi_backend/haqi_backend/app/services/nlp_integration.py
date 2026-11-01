"""
Arabic NLP & Egyptian Dialect Understanding Module Integration (Slide 9).
Integrates Ahmed Rabie's Arabic NLP pipeline into the HAQI Backend:
1. المعالجة والتطبيع (Normalization): توحيد الحروف وإزالة التشويش والتشكيل.
2. استيعاب اللهجة المصرية: ربط المصطلحات الدارجة بالمسميات الرسمية.
3. تصنيف القصد (Intent Classification) واستخراج الكيانات (NER).
4. إعادة صياغة الاستعلام (Query Rewriting) والتوضيح (Clarification).
5. فصل التوجيه الإجرائي عن الفتاوى القانونية والاستشارات القضائية (Slide 19).
"""

import re
from typing import Any, Dict, List, Optional
from app.schemas import NLPAnalysisResult

# Egyptian Colloquial to Formal Government Terminology Mapping (Slide 9)
EGYPTIAN_DIALECT_MAP: Dict[str, str] = {
    "بطاقه": "بطاقة الرقم القومي",
    "بطاقة": "بطاقة الرقم القومي",
    "البطاقه": "بطاقة الرقم القومي",
    "البطاقة": "بطاقة الرقم القومي",
    "بطاقتي": "بطاقة الرقم القومي",
    "اطلع": "استخراج",
    "أطلع": "استخراج",
    "اعمل": "إجراءات استخراج",
    "أعمل": "إجراءات استخراج",
    "اجدد": "تجديد",
    "أجدد": "تجديد",
    "ضاعت": "بدل فاقد",
    "اتسرقت": "بدل فاقد",
    "مفقودة": "بدل فاقد",
    "اتكسرت": "بدل تالف",
    "باظت": "بدل تالف",
    "اول مره": "لأول مرة",
    "أول مرة": "لأول مرة",
    "جديدة": "لأول مرة",
    "شهاده ميلاد": "شهادة ميلاد مميكنة",
    "شهادة ميلاد": "شهادة ميلاد مميكنة",
    "ميلاد كمبيوتر": "شهادة ميلاد مميكنة",
    "قيد عائلي": "قيد عائلي مميكن",
    "قيد عائلى": "قيد عائلي مميكن",
    "توكيل": "توكيل رسمي بالشهر العقاري",
    "شهر عقاري": "مصلحة الشهر العقاري والتوثيق",
    "باسبور": "جواز السفر المصري المميكن",
    "جواز سفر": "جواز السفر المصري المميكن",
    "معاش": "برنامج الدعم النقدي تكافل وكرامة",
    "تكافل وكرامه": "برنامج الدعم النقدي تكافل وكرامة",
    "تكافل وكرامة": "برنامج الدعم النقدي تكافل وكرامة",
}

LEGAL_OPINION_KEYWORDS: tuple = (
    "ارفع قضية",
    "أرفع قضية",
    "حكم محكمة",
    "فتوى قانونية",
    "ثغرة قانونية",
    "ميراث شرعي",
    "نزاع قضائي",
    "تعويض قضائي",
    "عقوبة السجن",
    "هل يحق لي مقاضاة",
    "استشارة قانونية",
)

OUT_OF_SCOPE_KEYWORDS: tuple = (
    "تأشيرة أمريكا",
    "فيزا شنغن",
    "أسعار الذهب",
    "سعر الدولار",
    "مباراة الأهلي",
    "حالة الطقس",
    "وصفة طبخ",
    "برمجة بايثون",
    "شراء سيارة مستعملة",
)


def normalize_arabic_text(text: str) -> str:
    """Normalizes Arabic letters, strips diacritics (tashkeel), tatweel, and extra punctuation."""
    if not text:
        return ""
    # Remove tashkeel and tatweel
    text = re.sub(r"[\u0617-\u061A\u064B-\u0652\u0640]", "", text)
    # Normalize Alef variants
    text = re.sub(r"[إأآا]", "ا", text)
    # Normalize Teh Marbuta to Heh and Alef Maksura to Yeh for consistent matching
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ؤ", "ء", text)
    text = re.sub(r"ئ", "ء", text)
    # Remove punctuation except Arabic/Latin letters and numbers
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class ArabicNLPService:
    """Adapter & implementation for Arabic Query Understanding & Dialect Mapping."""

    def analyze_query(
        self,
        user_query: str,
        pending_intent: Optional[str] = None,
        awaiting_clarification: bool = False,
    ) -> NLPAnalysisResult:
        raw = user_query.strip()
        norm = normalize_arabic_text(raw)

        # Check if this is a follow-up answer to a clarification prompt (Slide 16: "تجديد")
        if awaiting_clarification and pending_intent == "national_id_application":
            sub_type = self._detect_nid_subtype(raw, norm)
            if sub_type:
                sub_ar_map = {
                    "first_time": "إصدار لأول مرة",
                    "renewal": "تجديد بطاقة الرقم القومي",
                    "replacement": "بدل فاقد أو تالف",
                }
                return NLPAnalysisResult(
                    original_text=raw,
                    normalized_text=norm,
                    detected_dialect_terms={raw: sub_ar_map[sub_type]},
                    extracted_intent="national_id_application",
                    extracted_intent_ar=f"National ID Application ({sub_ar_map[sub_type]})",
                    sub_type=sub_type,
                    entities={
                        "service": "بطاقة الرقم القومي",
                        "sub_type": sub_type,
                        "sector": "قطاع الأحوال المدنية",
                    },
                    structured_search_query=f"إجراءات ومستندات {sub_ar_map[sub_type]} - قطاع الأحوال المدنية",
                    needs_clarification=False,
                )

        # Detect dialect terms mapped to official concepts
        detected_dialect: Dict[str, str] = {}
        for colloq, formal in EGYPTIAN_DIALECT_MAP.items():
            if normalize_arabic_text(colloq) in norm or colloq in raw:
                detected_dialect[colloq] = formal

        # Check Legal Opinion / Litigation request (Slide 19 guardrail)
        is_legal = any(
            normalize_arabic_text(kw) in norm or kw in raw for kw in LEGAL_OPINION_KEYWORDS
        )

        # Check explicit Out-of-Scope topics
        is_oos = any(
            normalize_arabic_text(kw) in norm or kw in raw for kw in OUT_OF_SCOPE_KEYWORDS
        )

        # Intent & Sub-type Classification
        intent = "unknown"
        intent_ar = "غير محدد (Unknown Intent)"
        sub_type: Optional[str] = "general"
        sector = "غير محدد"

        if any(w in norm for w in ("بطاقه", "بطاقتي", "رقم قومي", "الرقم القومي")):
            intent = "national_id_application"
            intent_ar = "National ID Application (إصدار بطاقة رقم قومي)"
            sector = "قطاع الأحوال المدنية"
            sub_type = self._detect_nid_subtype(raw, norm)
        elif any(w in norm for w in ("شهاده ميلاد", "ميلاد")):
            intent = "birth_certificate"
            intent_ar = "Birth Certificate Issuance (استخراج شهادة ميلاد مميكنة)"
            sector = "قطاع الأحوال المدنية"
        elif any(w in norm for w in ("قيد عاءلي", "قيد عائلي")):
            intent = "family_record"
            intent_ar = "Family Record Issuance (استخراج قيد عائلي مميكن)"
            sector = "قطاع الأحوال المدنية"
        elif any(w in norm for w in ("توكيل", "شهر عقاري", "توثيق")):
            intent = "notary_power_of_attorney"
            intent_ar = "Notary Power of Attorney (توكيل رسمي بالشهر العقاري)"
            sector = "مصلحة الشهر العقاري والتوثيق"
        elif any(w in norm for w in ("معاش", "تكافل", "كرامه", "تضامن")):
            intent = "social_pension_support"
            intent_ar = "Social Solidarity Pension (تكافل وكرامة)"
            sector = "وزارة التضامن الاجتماعي"
        elif any(w in norm for w in ("جواز سفر", "باسبور", "جوازات")):
            intent = "passport_service"
            intent_ar = "Passport Issuance/Renewal (استخراج أو تجديد جواز السفر)"
            sector = "الإدارة العامة للجوازات والهجرة والجنسية"

        # Determine if Clarification is needed (Slide 7 Step 4 & Slide 16 Example)
        needs_clarification = False
        clarification_question = None
        clarification_options: List[str] = []

        if intent == "national_id_application" and sub_type is None and not is_legal:
            needs_clarification = True
            clarification_question = (
                "أقدر أساعدك في معرفة الإجراءات والمستندات الرسمية لبطاقة الرقم القومي. "
                "هل دي أول مرة تستخرج بطاقة، ولا تجديد، ولا بدل فاقد/تالف؟"
            )
            clarification_options = [
                "أول مرة (بلوغ سن 15 عاماً)",
                "تجديد بطاقة منتهية أو تحديث بيانات",
                "بدل فاقد أو تالف",
            ]

        # Build Structured Search Query (Slide 9 Example: "إجراءات ومستندات استخراج بطاقة الرقم القومي – قطاع الأحوال المدنية")
        structured_query = self._build_structured_query(intent, sub_type, sector, norm)

        entities = {
            "intent": intent,
            "sub_type": sub_type or "unspecified",
            "sector": sector,
        }

        return NLPAnalysisResult(
            original_text=raw,
            normalized_text=norm,
            detected_dialect_terms=detected_dialect,
            extracted_intent=intent,
            extracted_intent_ar=intent_ar,
            sub_type=sub_type,
            entities=entities,
            structured_search_query=structured_query,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            clarification_options=clarification_options,
            is_legal_opinion_request=is_legal,
            is_out_of_scope=(is_oos or (intent == "unknown" and not is_legal)),
        )

    def _detect_nid_subtype(self, raw: str, norm: str) -> Optional[str]:
        if any(
            w in norm
            for w in ("اول مره", "لاول مره", "جديده", "15 سنه", "15 عام", "طالب", "سن 15")
        ):
            return "first_time"
        if any(
            w in norm
            for w in (
                "تجديد",
                "اجدد",
                "منتهيه",
                "قديمه",
                "تغيير المهنه",
                "تغيير الحاله",
                "تحديث",
            )
        ):
            return "renewal"
        if any(
            w in norm
            for w in ("بدل فاقد", "بدل تالف", "ضاعت", "اتسرقت", "اتكسرت", "مفقوده", "باظت", "فاقد", "تالف")
        ):
            return "replacement"
        return None

    def _build_structured_query(
        self, intent: str, sub_type: Optional[str], sector: str, fallback_norm: str
    ) -> str:
        if intent == "national_id_application":
            if sub_type == "first_time":
                return "إجراءات ومستندات استخراج بطاقة الرقم القومي لأول مرة – قطاع الأحوال المدنية"
            if sub_type == "renewal":
                return "إجراءات ومستندات تجديد بطاقة الرقم القومي – قطاع الأحوال المدنية"
            if sub_type == "replacement":
                return "إجراءات ومستندات بدل فاقد أو تالف بطاقة الرقم القومي – قطاع الأحوال المدنية"
            return "إجراءات ومستندات استخراج بطاقة الرقم القومي – قطاع الأحوال المدنية"
        if intent == "birth_certificate":
            return "إجراءات ومستندات استخراج شهادة ميلاد مميكنة – قطاع الأحوال المدنية"
        if intent == "family_record":
            return "إجراءات ومستندات استخراج قيد عائلي مميكن – قطاع الأحوال المدنية"
        if intent == "notary_power_of_attorney":
            return "إجراءات ومستندات تحرير توكيل رسمي – مصلحة الشهر العقاري والتوثيق"
        if intent == "social_pension_support":
            return "إجراءات ومستندات التقديم على معاش تكافل وكرامة – وزارة التضامن الاجتماعي"
        if intent == "passport_service":
            return "إجراءات ومستندات استخراج وتجديد جواز السفر المميكن – الإدارة العامة للجوازات"
        return fallback_norm


nlp_service = ArabicNLPService()
