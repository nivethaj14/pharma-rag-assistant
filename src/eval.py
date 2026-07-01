import json
from rag_query import rag_query

# Ground truth evaluation set
# Format: question, expected_source_keywords, expected_answer_keywords
EVAL_SET = [
    {
        "question": "What are the safety monitoring requirements for radiopharmaceutical therapies?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["safety", "monitoring", "radiation", "adverse"],
        "notes": "Should cite Safety Monitoring section"
    },
    {
        "question": "How long should sponsors monitor for late radiation adverse events?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["5 years", "rAESI", "postmarketing"],
        "notes": "Should return specific 5-year timeframe"
    },
    {
        "question": "What is the recommended approach for dose escalation in oncology trials?",
        "expected_sources": ["25037821fnl", "508ed_dg_rpt_dosage"],
        "expected_keywords": ["dose", "escalation", "toxicity", "MTD"],
        "notes": "Should cite multiple documents"
    },
    {
        "question": "What participant populations are suitable for RPT dose-finding trials?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["participant", "population", "life expectancy", "cancer"],
        "notes": "Should cite Participant Population section"
    },
    {
        "question": "What is dosimetry and why is it important for RPTs?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["dosimetry", "absorbed dose", "organ", "imaging"],
        "notes": "Should cite Dosimetry section"
    },
    {
        "question": "How should informed consent address radiation toxicity risks?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["informed consent", "toxicity", "long-term", "risk"],
        "notes": "Should cite Trial Design section"
    },
    {
        "question": "What are the key clinical trial endpoints for cancer drug approval?",
        "expected_sources": ["25037821fnl"],
        "expected_keywords": ["endpoint", "approval", "efficacy", "survival"],
        "notes": "Should cite second document"
    },
    {
        "question": "What is the difference between EBRT and RPT dosing approaches?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["EBRT", "RPT", "organ", "tolerance"],
        "notes": "Should explain key difference"
    },
    {
        "question": "How should sponsors handle cumulative radiation dose limits?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["cumulative", "administered activity", "limit", "cycles"],
        "notes": "Should cite Trial Design section"
    },
    {
        "question": "What biomarkers should be considered for delayed radiation toxicity?",
        "expected_sources": ["508ed_dg_rpt_dosage"],
        "expected_keywords": ["biomarker", "delayed", "radiation", "blood"],
        "notes": "Should cite Safety Monitoring section"
    }
]


def evaluate_result(result: dict, eval_item: dict) -> dict:
    """Score a single RAG result against ground truth."""
    answer = result["answer"].lower()
    sources = [s["file_name"].lower() for s in result["sources"]]

    # Check keyword presence in answer
    keywords_found = [
        kw for kw in eval_item["expected_keywords"]
        if kw.lower() in answer
    ]
    keyword_score = len(keywords_found) / len(eval_item["expected_keywords"])

    # Check source retrieval
    sources_found = [
        exp for exp in eval_item["expected_sources"]
        if any(exp.lower() in src for src in sources)
    ]
    source_score = len(sources_found) / len(eval_item["expected_sources"])

    # Check answer is not a refusal
    refused = "cannot find" in answer or "not available" in answer
    
    return {
        "question": eval_item["question"],
        "notes": eval_item["notes"],
        "keyword_score": round(keyword_score, 2),
        "source_score": round(source_score, 2),
        "overall_score": round((keyword_score + source_score) / 2, 2),
        "keywords_found": keywords_found,
        "keywords_missed": [
            kw for kw in eval_item["expected_keywords"]
            if kw.lower() not in answer
        ],
        "sources_found": sources_found,
        "refused": refused,
        "chunks_retrieved": result["chunks_retrieved"]
    }


def run_eval():
    """Run full evaluation suite and print report."""
    print("=" * 60)
    print("PharmaRAG Evaluation Report")
    print("=" * 60)

    results = []
    for i, item in enumerate(EVAL_SET, 1):
        print(f"\n[{i}/{len(EVAL_SET)}] {item['question'][:60]}...")
        try:
            rag_result = rag_query(item["question"])
            eval_result = evaluate_result(rag_result, item)
            results.append(eval_result)
            print(f"  Keyword score:  {eval_result['keyword_score']:.0%}")
            print(f"  Source score:   {eval_result['source_score']:.0%}")
            print(f"  Overall score:  {eval_result['overall_score']:.0%}")
            print(f"  Refused:        {eval_result['refused']}")
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "question": item["question"],
                "overall_score": 0,
                "error": str(e)
            })

    # Summary
    valid = [r for r in results if "error" not in r]
    avg_keyword = sum(r["keyword_score"] for r in valid) / len(valid)
    avg_source  = sum(r["source_score"]  for r in valid) / len(valid)
    avg_overall = sum(r["overall_score"] for r in valid) / len(valid)
    refusals    = sum(1 for r in valid if r.get("refused"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Questions evaluated:  {len(EVAL_SET)}")
    print(f"Avg keyword score:    {avg_keyword:.0%}")
    print(f"Avg source score:     {avg_source:.0%}")
    print(f"Avg overall score:    {avg_overall:.0%}")
    print(f"Refusals:             {refusals}/{len(valid)}")

    # Save results
    with open("docs/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to docs/eval_results.json")


if __name__ == "__main__":
    run_eval()