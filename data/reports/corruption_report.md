# Corruption and Repair Comparison Report

## Evaluation Metrics
| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 |
| `mean_token_f1` | 1.0000 | 0.5741 | 1.0000 |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 |
| `mean_judge_score` | 5 | 3.2000 | 5 |

## Observability Signals
| Signal | Corrupted | Repaired |
| --- | --- | --- |
| Quality gate | 4/6 checks passed; overall FAIL | 6/6 checks passed; overall PASS |
| Freshness SLA | 11 stale / 22 rows; ratio 0.5000; status FAIL | 1 stale / 24 rows; ratio 0.0417; status PASS |

## State Analysis
- **Baseline:** reference performance on the clean benchmark dataset.
- **Corrupted:** quality gate and freshness signals should expose injected data defects before serving.
- **Repaired:** data rebuilt from the raw snapshot should restore the quality contract and improve the evaluation metrics toward baseline.

## Repair Evidence
- Corrupted quality status: **FAIL**
- Repaired quality status: **PASS**
- Corrupted freshness status: **FAIL**
- Repaired freshness status: **PASS**
