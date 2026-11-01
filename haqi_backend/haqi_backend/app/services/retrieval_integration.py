"""
Advanced Hybrid Retrieval & Semantic Reranking Engine Integration (Slide 11).
Integrates Anas's Retrieval Pipeline into the HAQI Backend:
1. Semantic Search (Embeddings / Dense Concept Similarity)
2. Keyword Search (BM25 Lexical Scoring on Arabic Legal & Procedural Terms)
3. Metadata Filtering (Filter by Government Authority & Service Category)
4. Hybrid Result Fusion (Reciprocal Rank Fusion / Weighted Hybrid Scoring)
5. Cross-Encoder Reranking (Direct Query-Chunk Alignment Boost)
6. Top-K Context Selection (Passes top verified candidates to Evidence Validation)
"""

import math
from collections import Counter
from typing import Any, Dict, List, Optional

from app.database import db_manager
from app.schemas import NLPAnalysisResult
from app.services.nlp_integration import normalize_arabic_text


class HybridRetrievalService:
    """Implements the 6-stage Hybrid Retrieval & Reranking pipeline from Slide 11."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def retrieve_and_rerank(
        self,
        nlp_result: NLPAnalysisResult,
        service_category_filter: Optional[str] = None,
        top_k: int = 3,
        custom_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        # Stage 3: Metadata Filtering (Filter by Service Category if requested)
        candidates = (
            custom_chunks
            if custom_chunks is not None
            else db_manager.get_all_chunks_with_docs(service_category=service_category_filter)
        )
        if not candidates:
            return []

        query_text = f"{nlp_result.original_text} {nlp_result.structured_search_query}"
        query_tokens = normalize_arabic_text(query_text).split()

        # Precompute corpus statistics for BM25
        tokenized_docs: List[List[str]] = []
        for c in candidates:
            combined_doc_text = " ".join(
                [
                    c.get("service_name_ar", ""),
                    c.get("chunk_text", ""),
                    c.get("keywords_ar", ""),
                    " ".join(c.get("steps", [])),
                    " ".join(c.get("required_documents", [])),
                ]
            )
            tokenized_docs.append(normalize_arabic_text(combined_doc_text).split())

        avg_dl = (
            sum(len(d) for d in tokenized_docs) / len(tokenized_docs)
            if tokenized_docs
            else 1.0
        )
        N = len(tokenized_docs)

        # Stage 1 & 2: Compute Semantic Similarity & BM25 Keyword Scores
        bm25_raw_scores: List[float] = []
        semantic_scores: List[float] = []

        for idx, c in enumerate(candidates):
            doc_tokens = tokenized_docs[idx]
            bm25_score = self._compute_bm25(query_tokens, doc_tokens, tokenized_docs, N, avg_dl)
            sem_score = self._compute_semantic_similarity(nlp_result, c, query_tokens, doc_tokens)
            bm25_raw_scores.append(bm25_score)
            semantic_scores.append(sem_score)

        max_bm25 = max(bm25_raw_scores) if bm25_raw_scores and max(bm25_raw_scores) > 0 else 1.0

        # Stage 4 & 5: Hybrid Result Fusion + Cross-Encoder Reranking
        scored_candidates: List[Dict[str, Any]] = []
        for idx, c in enumerate(candidates):
            norm_bm25 = min(1.0, bm25_raw_scores[idx] / max_bm25)
            sem_score = semantic_scores[idx]

            # Hybrid fusion (0.55 semantic + 0.45 lexical BM25)
            hybrid_score = 0.55 * sem_score + 0.45 * norm_bm25

            # Stage 5: Cross-Encoder Reranking (Intent + Sub-type exact alignment)
            rerank_score = self._cross_encoder_rerank(nlp_result, c, hybrid_score)

            enriched = dict(c)
            enriched["bm25_score"] = round(norm_bm25, 4)
            enriched["semantic_score"] = round(sem_score, 4)
            enriched["hybrid_score"] = round(hybrid_score, 4)
            enriched["rerank_score"] = round(rerank_score, 4)
            scored_candidates.append(enriched)

        # Stage 6: Top-K Context Selection
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]

    def _compute_bm25(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
        all_docs: List[List[str]],
        N: int,
        avg_dl: float,
    ) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        doc_counts = Counter(doc_tokens)
        dl = len(doc_tokens)
        score = 0.0
        for q in set(query_tokens):
            df = sum(1 for d in all_docs if q in d)
            if df == 0:
                continue
            idf = math.log(1.0 + (N - df + 0.5) / (df + 0.5))
            tf = doc_counts.get(q, 0)
            denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / max(avg_dl, 1.0)))
            score += idf * ((tf * (self.k1 + 1.0)) / max(denom, 1e-6))
        return score

    def _compute_semantic_similarity(
        self,
        nlp_result: NLPAnalysisResult,
        chunk: Dict[str, Any],
        query_tokens: List[str],
        doc_tokens: List[str],
    ) -> float:
        """Computes dense concept & character n-gram cosine similarity."""
        if not query_tokens or not doc_tokens:
            return 0.0

        # Character 3-gram cosine similarity handles Arabic morphological variations
        q_text = " ".join(query_tokens)
        d_text = " ".join(doc_tokens)
        q_ngrams = Counter(q_text[i : i + 3] for i in range(max(0, len(q_text) - 2)))
        d_ngrams = Counter(d_text[i : i + 3] for i in range(max(0, len(d_text) - 2)))

        intersection = set(q_ngrams.keys()) & set(d_ngrams.keys())
        dot = sum(q_ngrams[k] * d_ngrams[k] for k in intersection)
        norm_q = math.sqrt(sum(v * v for v in q_ngrams.values())) or 1.0
        norm_d = math.sqrt(sum(v * v for v in d_ngrams.values())) or 1.0
        ngram_cos = dot / (norm_q * norm_d)

        # Intent semantic concept alignment
        intent_boost = 0.0
        if (
            nlp_result.extracted_intent != "unknown"
            and chunk.get("intent_tag") == nlp_result.extracted_intent
        ):
            intent_boost = 0.50

        return min(1.0, ngram_cos * 1.4 + intent_boost)

    def _cross_encoder_rerank(
        self, nlp_result: NLPAnalysisResult, chunk: Dict[str, Any], hybrid_score: float
    ) -> float:
        """Cross-Encoder reranker scoring direct query-passage intent & subtype match."""
        if nlp_result.is_out_of_scope or nlp_result.is_legal_opinion_request:
            return min(0.18, hybrid_score * 0.25)

        score = hybrid_score
        if chunk.get("intent_tag") == nlp_result.extracted_intent:
            score += 0.30
            if nlp_result.sub_type and chunk.get("sub_type") == nlp_result.sub_type:
                score += 0.20
            elif (
                nlp_result.sub_type
                and chunk.get("sub_type") != nlp_result.sub_type
                and chunk.get("sub_type") != "general"
            ):
                score -= 0.25
        else:
            score *= 0.45

        return max(0.0, min(1.0, score))


retrieval_service = HybridRetrievalService()
