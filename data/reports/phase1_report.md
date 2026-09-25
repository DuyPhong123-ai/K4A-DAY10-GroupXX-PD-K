# Phase 1 Baseline Report

## Source Summary
- **Source API:** Crossref REST API
- **Query:** agentic retrieval augmented generation large language model
- **Total Ingested:** 24
- **Clean Records:** 24
- **Collection Name:** papers-baseline
- **Embedding Model:** sentence-transformers/all-MiniLM-L6-v2
- **Run Date:** 2026-09-25

## Evaluation Metrics
| Metric | Baseline |
| --- | --- |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

## Data Quality and Freshness
| Signal | Baseline |
| --- | --- |
| Quality gate | 6/6 checks passed; overall PASS |
| Freshness SLA | 1 stale / 24 rows; ratio 0.0417; status PASS |

### Freshness Details
- Latest published: 2026-07-22
- Oldest published: 2026-03-28
- Threshold: 180 days

## Interpretation
- The baseline is eligible for serving only when the quality gate and Freshness SLA both pass.
- Retrieval and answer metrics above are the reference values for corruption impact analysis.
