import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application & Evidence Validation settings configured via environment variables."""

    app_name: str = os.getenv(
        "APP_NAME", "Haqi Egypt Service Guide - Backend API (حقي)"
    )
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    developer: str = "Maha — Backend, Database & Evaluation Lead"
    debug: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    port: int = int(os.getenv("PORT", "8000"))

    # Database Configuration (PostgreSQL primary + local SQLite fallback)
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/haqi_db"
    )
    sqlite_fallback_path: str = os.getenv(
        "SQLITE_FALLBACK_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "haqi_local.db"),
    )

    # Evidence Validation & Safe Abstention Thresholds (Slide 12 & 19)
    min_relevance_score: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.32"))
    min_grounding_score: float = float(os.getenv("MIN_GROUNDING_SCORE", "0.55"))
    max_doc_age_days: int = int(os.getenv("MAX_DOC_AGE_DAYS", "730"))
    require_official_authority: bool = os.getenv(
        "REQUIRE_OFFICIAL_AUTHORITY", "True"
    ).lower() in ("true", "1", "yes")

    # Trusted Official Egyptian Authorities (Slide 12 & 13)
    trusted_authorities: tuple = (
        "قطاع الأحوال المدنية - وزارة الداخلية",
        "مصلحة الأحوال المدنية - وزارة الداخلية",
        "بوابة مصر الرقمية",
        "وزارة التضامن الاجتماعي",
        "مصلحة الشهر العقاري والتوثيق - وزارة العدل",
        "الإدارة العامة للجوازات والهجرة والجنسية",
        "الهيئة القومية للتأمين الاجتماعي",
    )

    trusted_domains: tuple = (
        "digital.gov.eg",
        "moi.gov.eg",
        "cso.moi.gov.eg",
        "moss.gov.eg",
        "moj.gov.eg",
        "nosi.gov.eg",
        "egypt.gov.eg",
    )


settings = Settings()
