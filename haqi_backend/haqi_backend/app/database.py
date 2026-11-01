"""
Database Layer & Repository Manager for HAQI (حقي).
Supports PostgreSQL via SQLAlchemy 2.0 (primary production database configured via DATABASE_URL)
and automatically falls back to local SQLite persistence when PostgreSQL is offline during local
development or CI testing. Seeds the verified Egyptian Civil Status knowledge base on startup.
"""

import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models import SQLALCHEMY_AVAILABLE, Base
from app.seed_data import OFFICIAL_DOCUMENTS_SEED, SERVICE_CHUNKS_SEED


class DatabaseManager:
    """Unified Database Manager supporting PostgreSQL (SQLAlchemy) and SQLite fallback."""

    def __init__(self, db_path: Optional[str] = None):
        self.sqlite_path = db_path or settings.sqlite_fallback_path
        self.engine_type = "sqlite_fallback"
        self.sa_engine = None
        self._init_storage()
        self.seed_initial_data()

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_storage(self) -> None:
        if SQLALCHEMY_AVAILABLE:
            try:
                from sqlalchemy import create_engine, text

                engine = create_engine(
                    settings.database_url,
                    pool_pre_ping=True,
                    connect_args={"connect_timeout": 2},
                )
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                Base.metadata.create_all(bind=engine)
                self.sa_engine = engine
                self.engine_type = "postgresql_sqlalchemy"
                return
            except Exception:
                # PostgreSQL server not reachable locally; fall back smoothly to SQLite
                pass

        schema_ddl = """
            CREATE TABLE IF NOT EXISTS official_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                authority TEXT NOT NULL,
                original_url TEXT NOT NULL,
                publication_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                service_category TEXT NOT NULL,
                verification_date TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT '1.0',
                is_official_verified INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS service_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                document_id INTEGER NOT NULL,
                service_slug TEXT NOT NULL,
                service_name_ar TEXT NOT NULL,
                sub_type TEXT NOT NULL DEFAULT 'general',
                intent_tag TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                required_documents_json TEXT NOT NULL,
                eligibility_criteria_json TEXT NOT NULL,
                fees_text TEXT,
                processing_time TEXT,
                keywords_ar TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES official_documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'citizen',
                preferred_dialect TEXT NOT NULL DEFAULT 'ar-EG',
                created_at TEXT NOT NULL,
                last_active_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                pending_intent TEXT,
                pending_service_slug TEXT,
                awaiting_clarification INTEGER NOT NULL DEFAULT 0,
                clarification_options_json TEXT DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message_text TEXT NOT NULL,
                detected_intent TEXT,
                rewritten_query TEXT,
                decision_type TEXT,
                confidence_score REAL DEFAULT 0.0,
                citations_json TEXT DEFAULT '[]',
                retrieval_time_ms REAL DEFAULT 0.0,
                total_latency_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contradiction_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                doc_code_a TEXT NOT NULL,
                doc_code_b TEXT NOT NULL,
                conflict_description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_human_review',
                resolution_notes TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            );

            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id INTEGER,
                rating INTEGER NOT NULL,
                is_helpful INTEGER NOT NULL DEFAULT 1,
                comment TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evaluation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                dataset_version TEXT NOT NULL,
                total_cases INTEGER NOT NULL,
                recall_at_k REAL NOT NULL,
                mrr REAL NOT NULL,
                ndcg_at_k REAL NOT NULL,
                faithfulness REAL NOT NULL,
                answer_accuracy REAL NOT NULL,
                citation_precision REAL NOT NULL,
                abstention_quality REAL NOT NULL,
                unsupported_claim_rate REAL NOT NULL,
                avg_retrieval_time_ms REAL NOT NULL,
                avg_response_latency_ms REAL NOT NULL,
                detailed_results_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """
        try:
            conn = self._get_sqlite_conn()
            conn.executescript(schema_ddl)
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            # Handle filesystems (such as FUSE/WSL/network mounts) that do not support SQLite POSIX file locks
            self.sqlite_path = os.path.join(tempfile.gettempdir(), "haqi_local.db")
            conn = self._get_sqlite_conn()
            conn.executescript(schema_ddl)
            conn.commit()
            conn.close()

    def seed_initial_data(self) -> None:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        doc_id_map: Dict[str, int] = {}
        for doc in OFFICIAL_DOCUMENTS_SEED:
            cur.execute(
                """
                INSERT OR IGNORE INTO official_documents
                (doc_code, title, authority, original_url, publication_date, last_updated,
                 service_category, verification_date, version, is_official_verified, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc["doc_code"],
                    doc["title"],
                    doc["authority"],
                    doc["original_url"],
                    doc["publication_date"],
                    doc["last_updated"],
                    doc["service_category"],
                    doc["verification_date"],
                    doc["version"],
                    1 if doc.get("is_official_verified", True) else 0,
                    doc.get("status", "active"),
                    now_iso,
                ),
            )
            cur.execute(
                "SELECT id FROM official_documents WHERE doc_code = ?", (doc["doc_code"],)
            )
            row = cur.fetchone()
            if row:
                doc_id_map[doc["doc_code"]] = row["id"]

        for chunk in SERVICE_CHUNKS_SEED:
            doc_id = doc_id_map.get(chunk["doc_code"], 1)
            cur.execute(
                """
                INSERT OR IGNORE INTO service_chunks
                (chunk_id, document_id, service_slug, service_name_ar, sub_type, intent_tag,
                 chunk_text, steps_json, required_documents_json, eligibility_criteria_json,
                 fees_text, processing_time, keywords_ar, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["chunk_id"],
                    doc_id,
                    chunk["service_slug"],
                    chunk["service_name_ar"],
                    chunk["sub_type"],
                    chunk["intent_tag"],
                    chunk["chunk_text"],
                    json.dumps(chunk["steps"], ensure_ascii=False),
                    json.dumps(chunk["required_documents"], ensure_ascii=False),
                    json.dumps(chunk["eligibility_criteria"], ensure_ascii=False),
                    chunk["fees_text"],
                    chunk["processing_time"],
                    chunk["keywords_ar"],
                    now_iso,
                ),
            )

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------------
    # Document & Chunk Queries
    # ------------------------------------------------------------------------
    def list_documents(self, service_category: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        if service_category:
            cur.execute(
                "SELECT * FROM official_documents WHERE service_category = ? ORDER BY id ASC",
                (service_category,),
            )
        else:
            cur.execute("SELECT * FROM official_documents ORDER BY id ASC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            r["is_official_verified"] = bool(r["is_official_verified"])
        return rows

    def create_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT OR REPLACE INTO official_documents
            (doc_code, title, authority, original_url, publication_date, last_updated,
             service_category, verification_date, version, is_official_verified, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_data["doc_code"],
                doc_data["title"],
                doc_data["authority"],
                doc_data["original_url"],
                doc_data["publication_date"],
                doc_data["last_updated"],
                doc_data["service_category"],
                doc_data["verification_date"],
                doc_data.get("version", "1.0"),
                1 if doc_data.get("is_official_verified", True) else 0,
                doc_data.get("status", "active"),
                now_iso,
            ),
        )
        conn.commit()
        cur.execute(
            "SELECT * FROM official_documents WHERE doc_code = ?", (doc_data["doc_code"],)
        )
        row = dict(cur.fetchone())
        row["is_official_verified"] = bool(row["is_official_verified"])
        conn.close()
        return row

    def get_all_chunks_with_docs(
        self, service_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        sql = """
            SELECT
                c.*,
                d.doc_code,
                d.title AS doc_title,
                d.authority,
                d.original_url,
                d.publication_date,
                d.last_updated,
                d.service_category,
                d.verification_date,
                d.version,
                d.is_official_verified,
                d.status AS doc_status
            FROM service_chunks c
            JOIN official_documents d ON c.document_id = d.id
        """
        params: tuple = ()
        if service_category:
            sql += " WHERE d.service_category = ?"
            params = (service_category,)
        cur.execute(sql, params)
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            item["steps"] = json.loads(item["steps_json"])
            item["required_documents"] = json.loads(item["required_documents_json"])
            item["eligibility_criteria"] = json.loads(item["eligibility_criteria_json"])
            item["is_official_verified"] = bool(item["is_official_verified"])
            rows.append(item)
        conn.close()
        return rows

    def get_service_by_slug(
        self, service_slug: str, sub_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        all_chunks = self.get_all_chunks_with_docs()
        matches = [c for c in all_chunks if c["service_slug"] == service_slug]
        if sub_type and sub_type != "general":
            filtered = [c for c in matches if c["sub_type"] == sub_type]
            if filtered:
                return filtered
        return matches

    # ------------------------------------------------------------------------
    # User & Session Management (Data Minimization Compliant - Slide 19)
    # ------------------------------------------------------------------------
    def ensure_user(self, user_id: str) -> Dict[str, Any]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT OR IGNORE INTO users (user_id, role, preferred_dialect, created_at, last_active_at)
            VALUES (?, 'citizen', 'ar-EG', ?, ?)
            """,
            (user_id, now_iso, now_iso),
        )
        cur.execute(
            "UPDATE users SET last_active_at = ? WHERE user_id = ?", (now_iso, user_id)
        )
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = dict(cur.fetchone())
        conn.close()
        return user

    def get_or_create_session(
        self, user_id: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        self.ensure_user(user_id)
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        if session_id:
            cur.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ? AND is_active = 1",
                (session_id,),
            )
            existing = cur.fetchone()
            if existing:
                sess = dict(existing)
                sess["awaiting_clarification"] = bool(sess["awaiting_clarification"])
                sess["clarification_options"] = json.loads(
                    sess["clarification_options_json"] or "[]"
                )
                conn.close()
                return sess

        new_sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        cur.execute(
            """
            INSERT OR REPLACE INTO chat_sessions
            (session_id, user_id, pending_intent, pending_service_slug, awaiting_clarification,
             clarification_options_json, is_active, created_at, updated_at)
            VALUES (?, ?, NULL, NULL, 0, '[]', 1, ?, ?)
            """,
            (new_sid, user_id, now_iso, now_iso),
        )
        conn.commit()
        cur.execute("SELECT * FROM chat_sessions WHERE session_id = ?", (new_sid,))
        sess = dict(cur.fetchone())
        sess["awaiting_clarification"] = bool(sess["awaiting_clarification"])
        sess["clarification_options"] = json.loads(
            sess["clarification_options_json"] or "[]"
        )
        conn.close()
        return sess

    def update_session_clarification(
        self,
        session_id: str,
        awaiting: bool,
        pending_intent: Optional[str] = None,
        pending_service_slug: Optional[str] = None,
        options: Optional[List[str]] = None,
    ) -> None:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            UPDATE chat_sessions
            SET awaiting_clarification = ?,
                pending_intent = ?,
                pending_service_slug = ?,
                clarification_options_json = ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (
                1 if awaiting else 0,
                pending_intent,
                pending_service_slug,
                json.dumps(options or [], ensure_ascii=False),
                now_iso,
                session_id,
            ),
        )
        conn.commit()
        conn.close()

    def log_chat_message(
        self,
        session_id: str,
        role: str,
        message_text: str,
        detected_intent: Optional[str] = None,
        rewritten_query: Optional[str] = None,
        decision_type: Optional[str] = None,
        confidence_score: float = 0.0,
        citations: Optional[List[Dict[str, Any]]] = None,
        retrieval_time_ms: float = 0.0,
        total_latency_ms: float = 0.0,
    ) -> int:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT INTO chat_messages
            (session_id, role, message_text, detected_intent, rewritten_query,
             decision_type, confidence_score, citations_json, retrieval_time_ms,
             total_latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                message_text,
                detected_intent,
                rewritten_query,
                decision_type,
                confidence_score,
                json.dumps(citations or [], ensure_ascii=False),
                retrieval_time_ms,
                total_latency_ms,
                now_iso,
            ),
        )
        msg_id = cur.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,))
        sess_row = cur.fetchone()
        if not sess_row:
            conn.close()
            return {}
        sess = dict(sess_row)
        sess["awaiting_clarification"] = bool(sess["awaiting_clarification"])
        sess["is_active"] = bool(sess["is_active"])
        cur.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        messages = []
        for m in cur.fetchall():
            md = dict(m)
            md["citations"] = json.loads(md["citations_json"] or "[]")
            messages.append(md)
        sess["messages"] = messages
        conn.close()
        return sess

    def delete_session(self, session_id: str) -> bool:
        """Deletes session messages & deactivates session (Privacy / Data Minimization - Slide 19)."""
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # ------------------------------------------------------------------------
    # Contradiction Flags, Feedback & Evaluation Runs
    # ------------------------------------------------------------------------
    def create_contradiction_flag(
        self,
        query_text: str,
        doc_code_a: str,
        doc_code_b: str,
        conflict_description: str,
    ) -> Dict[str, Any]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT INTO contradiction_flags
            (query_text, doc_code_a, doc_code_b, conflict_description, status, created_at)
            VALUES (?, ?, ?, ?, 'pending_human_review', ?)
            """,
            (query_text, doc_code_a, doc_code_b, conflict_description, now_iso),
        )
        flag_id = cur.lastrowid
        conn.commit()
        cur.execute("SELECT * FROM contradiction_flags WHERE id = ?", (flag_id,))
        row = dict(cur.fetchone())
        conn.close()
        return row

    def list_contradiction_flags(self) -> List[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM contradiction_flags ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def resolve_contradiction_flag(
        self, flag_id: int, resolution_notes: str, preferred_doc_code: str
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        notes = f"[Preferred: {preferred_doc_code}] {resolution_notes}"
        cur.execute(
            """
            UPDATE contradiction_flags
            SET status = 'resolved_by_human', resolution_notes = ?, resolved_at = ?
            WHERE id = ?
            """,
            (notes, now_iso, flag_id),
        )
        conn.commit()
        cur.execute("SELECT * FROM contradiction_flags WHERE id = ?", (flag_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT INTO user_feedback (session_id, message_id, rating, is_helpful, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                feedback["session_id"],
                feedback.get("message_id"),
                feedback["rating"],
                1 if feedback.get("is_helpful", True) else 0,
                feedback.get("comment"),
                now_iso,
            ),
        )
        fid = cur.lastrowid
        conn.commit()
        cur.execute("SELECT * FROM user_feedback WHERE id = ?", (fid,))
        row = dict(cur.fetchone())
        row["is_helpful"] = bool(row["is_helpful"])
        conn.close()
        return row

    def save_evaluation_run(self, summary: Dict[str, Any]) -> None:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT OR REPLACE INTO evaluation_runs
            (run_id, dataset_version, total_cases, recall_at_k, mrr, ndcg_at_k,
             faithfulness, answer_accuracy, citation_precision, abstention_quality,
             unsupported_claim_rate, avg_retrieval_time_ms, avg_response_latency_ms,
             detailed_results_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary["run_id"],
                summary["dataset_version"],
                summary["total_cases"],
                summary["recall_at_k"],
                summary["mrr"],
                summary["ndcg_at_k"],
                summary["faithfulness"],
                summary["answer_accuracy"],
                summary["citation_precision"],
                summary["abstention_quality"],
                summary["unsupported_claim_rate"],
                summary["avg_retrieval_time_ms"],
                summary["avg_response_latency_ms"],
                json.dumps(summary.get("case_results", []), ensure_ascii=False),
                now_iso,
            ),
        )
        conn.commit()
        conn.close()

    def get_latest_evaluation_run(self) -> Optional[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM evaluation_runs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["case_results"] = json.loads(d["detailed_results_json"] or "[]")
        return d


db_manager = DatabaseManager()
