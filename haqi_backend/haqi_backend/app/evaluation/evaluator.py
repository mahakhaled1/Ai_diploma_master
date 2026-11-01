"""
Quantitative & Qualitative Benchmark Evaluation Engine for HAQI (حقي) — Slide 18.
Computes all 4 Evaluation Metric families specified in the architecture presentation:
1. كفاءة الاسترجاع (Retrieval Efficiency): Recall@K, MRR, nDCG@K
2. جودة الإجابة (Answer Quality): Faithfulness, Answer Accuracy, Citation Precision
3. الأمان والموثوقية (Safety & Reliability): Abstention Quality, Unsupported Claim Rate
4. الأداء الزمني (Temporal Performance): Retrieval Time (ms), Response Latency (ms)
"""

import json
import math
import os
import uuid
from typing import Any, Dict, List

from app.database import db_manager
from app.schemas import ChatRequest, EvaluationMetricsSummary
from app.services.nlp_integration import nlp_service
from app.services.rag_service import rag_service
from app.services.retrieval_integration import retrieval_service


class SystemEvaluator:
    """Runs the Benchmark Dataset against the live HAQI pipeline and computes metrics."""

    def __init__(self, dataset_path: str = None):
        if dataset_path is None:
            dataset_path = os.path.join(
                os.path.dirname(__file__), "benchmark_dataset.json"
            )
        self.dataset_path = dataset_path

    def load_dataset(self) -> Dict[str, Any]:
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_benchmark(self, top_k: int = 3) -> EvaluationMetricsSummary:
        data = self.load_dataset()
        dataset_version = data.get("dataset_version", "HAQI-Bench-v1.0")
        cases = data.get("cases", [])

        recall_scores: List[float] = []
        mrr_scores: List[float] = []
        ndcg_scores: List[float] = []

        faithfulness_scores: List[float] = []
        accuracy_scores: List[float] = []
        citation_precision_scores: List[float] = []

        abstention_decisions_correct: List[float] = []
        unsupported_claim_rates: List[float] = []

        retrieval_times: List[float] = []
        response_latencies: List[float] = []
        case_results: List[Dict[str, Any]] = []

        for case in cases:
            case_id = case["case_id"]
            question = case["question"]
            expected_decision = case["expected_decision"]
            expected_chunk_id = case.get("expected_chunk_id")
            expected_doc_code = case.get("expected_doc_code")
            expected_keywords = case.get("expected_keywords", [])

            # Run full RAG pipeline
            chat_res = rag_service.process_citizen_query(
                ChatRequest(
                    question=question,
                    user_id=f"eval_user_{case_id}",
                    session_id=f"eval_sess_{case_id}_{uuid.uuid4().hex[:6]}",
                )
            )

            ret_time = chat_res.metrics.get("retrieval_time_ms", 0.0)
            lat_time = chat_res.metrics.get("response_latency_ms", 0.0)
            retrieval_times.append(ret_time)
            response_latencies.append(lat_time)

            # Evaluate Retrieval Metrics on cases that have an expected knowledge chunk
            rank_found = None
            if expected_chunk_id:
                nlp_res = nlp_service.analyze_query(question)
                ranked_chunks = retrieval_service.retrieve_and_rerank(
                    nlp_result=nlp_res, top_k=top_k
                )
                retrieved_ids = [c["chunk_id"] for c in ranked_chunks]
                if expected_chunk_id in retrieved_ids:
                    rank_found = retrieved_ids.index(expected_chunk_id) + 1
                    recall_scores.append(1.0)
                    mrr_scores.append(1.0 / rank_found)
                    # nDCG@K for binary relevance with 1 ideal target: 1 / log2(rank + 1)
                    ndcg_scores.append(1.0 / math.log2(rank_found + 1))
                else:
                    recall_scores.append(0.0)
                    mrr_scores.append(0.0)
                    ndcg_scores.append(0.0)

            # Evaluate Decision & Abstention Quality
            decision_match = 1.0 if chat_res.decision_type == expected_decision else 0.0
            if expected_decision in ("safe_abstention", "clarification_needed"):
                abstention_decisions_correct.append(decision_match)

            # Evaluate Answer Quality (Faithfulness, Accuracy, Citation Precision)
            if expected_decision == "answered":
                faith = chat_res.evidence_validation.grounding_score
                faithfulness_scores.append(faith)
                unsupported_claim_rates.append(max(0.0, 1.0 - faith))

                # Keyword coverage accuracy
                kw_hits = sum(1 for kw in expected_keywords if kw in chat_res.answer)
                kw_acc = kw_hits / max(len(expected_keywords), 1)
                accuracy_scores.append(round(0.5 * decision_match + 0.5 * kw_acc, 4))

                # Citation precision
                if chat_res.citations:
                    cit_matches = sum(
                        1
                        for c in chat_res.citations
                        if c.doc_code == expected_doc_code
                    )
                    citation_precision_scores.append(
                        cit_matches / len(chat_res.citations)
                    )
                else:
                    citation_precision_scores.append(0.0)
            else:
                # For clarification or abstention cases, verify expected keywords and zero hallucinated citations
                kw_hits = sum(1 for kw in expected_keywords if kw in chat_res.answer)
                kw_acc = kw_hits / max(len(expected_keywords), 1)
                accuracy_scores.append(round(0.5 * decision_match + 0.5 * kw_acc, 4))
                # No unsupported claims if the system properly abstained or asked for clarification
                if chat_res.decision_type in ("safe_abstention", "clarification_needed"):
                    faithfulness_scores.append(1.0)
                    unsupported_claim_rates.append(0.0)
                else:
                    faithfulness_scores.append(0.0)
                    unsupported_claim_rates.append(1.0)

            case_results.append(
                {
                    "case_id": case_id,
                    "category": case["category"],
                    "question": question,
                    "expected_decision": expected_decision,
                    "actual_decision": chat_res.decision_type,
                    "decision_correct": bool(decision_match == 1.0),
                    "retrieval_rank": rank_found,
                    "grounding_score": chat_res.evidence_validation.grounding_score,
                    "retrieval_time_ms": ret_time,
                    "response_latency_ms": lat_time,
                }
            )

        def avg(vals: List[float]) -> float:
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        run_id = f"eval_{uuid.uuid4().hex[:10]}"
        summary = EvaluationMetricsSummary(
            run_id=run_id,
            dataset_version=dataset_version,
            total_cases=len(cases),
            recall_at_k=avg(recall_scores),
            mrr=avg(mrr_scores),
            ndcg_at_k=avg(ndcg_scores),
            faithfulness=avg(faithfulness_scores),
            answer_accuracy=avg(accuracy_scores),
            citation_precision=avg(citation_precision_scores),
            abstention_quality=avg(abstention_decisions_correct),
            unsupported_claim_rate=avg(unsupported_claim_rates),
            avg_retrieval_time_ms=round(avg(retrieval_times), 3),
            avg_response_latency_ms=round(avg(response_latencies), 3),
            case_results=case_results,
        )

        db_manager.save_evaluation_run(summary.model_dump())
        return summary


evaluator = SystemEvaluator()
