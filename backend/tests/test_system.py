"""
System Quality Evaluation Tests for Gorilla AI.
Measures response quality, consistency, memory accuracy, and retrieval quality.
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Callable
import pytest


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    test_name: str
    score: float  # 0.0-1.0
    latency_ms: float
    details: dict = field(default_factory=dict)


@dataclass
class EvalReport:
    results: list[EvalResult] = field(default_factory=list)

    def add(self, result: EvalResult):
        self.results.append(result)

    def summary(self) -> dict:
        if not self.results:
            return {}
        scores = [r.score for r in self.results]
        latencies = [r.latency_ms for r in self.results]
        return {
            "total_tests": len(self.results),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "passed": sum(1 for s in scores if s >= 0.7),
            "failed": sum(1 for s in scores if s < 0.7),
        }

    def print_report(self):
        print("\n" + "=" * 60)
        print("GORILLA AI QUALITY EVALUATION REPORT")
        print("=" * 60)
        for r in self.results:
            status = "PASS" if r.score >= 0.7 else "FAIL"
            print(f"[{status}] {r.test_name}")
            print(f"       Score: {r.score:.1%} | Latency: {r.latency_ms:.0f}ms")
            if r.details:
                for k, v in r.details.items():
                    print(f"       {k}: {v}")
        print("-" * 60)
        summary = self.summary()
        print(f"OVERALL: {summary['avg_score']:.1%} | "
              f"Pass: {summary['passed']}/{summary['total_tests']} | "
              f"Avg Latency: {summary['avg_latency_ms']:.0f}ms")
        print("=" * 60)


# ─── Evaluators ──────────────────────────────────────────────────────────────

class ResponseQualityEvaluator:
    """Evaluates response quality using keyword presence and length heuristics."""

    def evaluate(self, query: str, response: str, expected_keywords: list[str]) -> float:
        if not response:
            return 0.0

        # Keyword coverage
        found = sum(1 for kw in expected_keywords if kw.lower() in response.lower())
        keyword_score = found / len(expected_keywords) if expected_keywords else 1.0

        # Length score (penalize too short or truncated)
        length = len(response)
        if length < 20:
            length_score = 0.2
        elif length < 50:
            length_score = 0.6
        else:
            length_score = 1.0

        # Repetition penalty
        words = response.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            rep_score = min(1.0, unique_ratio * 1.5)
        else:
            rep_score = 1.0

        return (keyword_score * 0.5 + length_score * 0.3 + rep_score * 0.2)


class ConsistencyEvaluator:
    """Tests if character stays consistent across turns."""

    def evaluate(self, character_name: str, responses: list[str]) -> float:
        if not responses:
            return 0.0

        scores = []
        for resp in responses:
            resp_lower = resp.lower()
            # Check character doesn't break role
            breaks = ["私はAI", "私はアシスタント", "I am an AI", "as an AI"]
            has_break = any(b.lower() in resp_lower for b in breaks)
            scores.append(0.0 if has_break else 1.0)

        return sum(scores) / len(scores)


class MemoryAccuracyEvaluator:
    """Tests if stated facts are recalled correctly."""

    def evaluate(self, stated_fact: str, recall_response: str) -> float:
        words = [w for w in stated_fact.lower().split() if len(w) > 3]
        if not words:
            return 0.0
        found = sum(1 for w in words if w in recall_response.lower())
        return found / len(words)


class RetrievalQualityEvaluator:
    """Evaluates RAG retrieval relevance."""

    def evaluate(self, query: str, retrieved_docs: list[str]) -> float:
        if not retrieved_docs:
            return 0.0

        query_words = set(query.lower().split())
        scores = []
        for doc in retrieved_docs:
            doc_words = set(doc.lower().split())
            if not doc_words:
                continue
            overlap = len(query_words & doc_words) / len(query_words | doc_words)
            scores.append(overlap)

        return sum(scores) / len(scores) if scores else 0.0


# ─── Test Cases ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_response_quality_suite():
    """Suite of response quality tests."""
    evaluator = ResponseQualityEvaluator()
    report = EvalReport()

    test_cases = [
        {
            "name": "日本語基本応答",
            "query": "日本の首都はどこですか？",
            "response": "日本の首都は東京です。東京は政治・経済・文化の中心地として知られています。",
            "keywords": ["東京", "首都"],
        },
        {
            "name": "長文説明品質",
            "query": "機械学習とは何ですか？",
            "response": "機械学習は、コンピュータがデータから自動的に学習し、経験から改善するAI技術です。データのパターンを認識し、予測や分類を行います。",
            "keywords": ["データ", "学習", "AI"],
        },
        {
            "name": "空の応答検出",
            "query": "テスト",
            "response": "",
            "keywords": ["テスト"],
        },
    ]

    for tc in test_cases:
        start = time.perf_counter()
        score = evaluator.evaluate(tc["query"], tc["response"], tc["keywords"])
        latency = (time.perf_counter() - start) * 1000
        report.add(EvalResult(tc["name"], score, latency))

    report.print_report()
    summary = report.summary()
    assert summary["avg_score"] >= 0.5, f"Quality score too low: {summary['avg_score']}"


@pytest.mark.asyncio
async def test_consistency_suite():
    """Character consistency evaluation."""
    evaluator = ConsistencyEvaluator()
    report = EvalReport()

    # Simulate character responses
    consistent_responses = [
        "そうですね、私はアリスです。今日も元気ですよ！",
        "うふふ、その質問は面白いですね。私なりの意見を言うと...",
        "お兄さん、もっと具体的に聞いてくれたら答えやすいです。",
    ]

    inconsistent_responses = [
        "そうですね...",
        "私はAIアシスタントですので、感情はありません。",  # Role break
        "どんなことでもお聞きください。",
    ]

    start = time.perf_counter()
    score_consistent = evaluator.evaluate("アリス", consistent_responses)
    score_inconsistent = evaluator.evaluate("アリス", inconsistent_responses)
    latency = (time.perf_counter() - start) * 1000

    report.add(EvalResult("一貫性テスト（正常）", score_consistent, latency / 2))
    report.add(EvalResult("一貫性テスト（破綻検出）", 1.0 - score_inconsistent, latency / 2,
                          {"detected_break": score_inconsistent < 1.0}))

    report.print_report()


@pytest.mark.asyncio
async def test_memory_accuracy():
    """Memory recall accuracy tests."""
    evaluator = MemoryAccuracyEvaluator()
    report = EvalReport()

    test_cases = [
        {
            "name": "基本情報記憶",
            "stated": "私の名前は田中太郎で、東京在住のエンジニアです",
            "recall": "はい、田中太郎さんは東京に住んでいるエンジニアですね。",
        },
        {
            "name": "好み記憶",
            "stated": "猫が大好きで、特に三毛猫が好きです",
            "recall": "猫、特に三毛猫がお好きなんですね！",
        },
        {
            "name": "部分的記憶",
            "stated": "10年前に大阪で生まれて、学生時代は京都に住んでいました",
            "recall": "大阪のご出身でしたね。",
        },
    ]

    for tc in test_cases:
        start = time.perf_counter()
        score = evaluator.evaluate(tc["stated"], tc["recall"])
        latency = (time.perf_counter() - start) * 1000
        report.add(EvalResult(tc["name"], score, latency))

    report.print_report()


@pytest.mark.asyncio
async def test_retrieval_quality():
    """RAG retrieval quality tests."""
    evaluator = RetrievalQualityEvaluator()
    report = EvalReport()

    test_cases = [
        {
            "name": "高関連度取得",
            "query": "機械学習アルゴリズムの種類",
            "docs": [
                "機械学習には教師あり学習、教師なし学習、強化学習の3種類があります。",
                "深層学習はニューラルネットワークを多層化した機械学習の一手法です。",
            ],
        },
        {
            "name": "低関連度検出",
            "query": "機械学習アルゴリズム",
            "docs": [
                "今日の天気は晴れです。",
                "美味しいラーメンの作り方。",
            ],
        },
    ]

    for tc in test_cases:
        start = time.perf_counter()
        score = evaluator.evaluate(tc["query"], tc["docs"])
        latency = (time.perf_counter() - start) * 1000
        report.add(EvalResult(tc["name"], score, latency))

    report.print_report()


# ─── Benchmark Runner ─────────────────────────────────────────────────────────

def run_benchmark():
    """Run all benchmarks and print a comprehensive report."""
    asyncio.run(test_response_quality_suite())
    asyncio.run(test_consistency_suite())
    asyncio.run(test_memory_accuracy())
    asyncio.run(test_retrieval_quality())


if __name__ == "__main__":
    run_benchmark()
