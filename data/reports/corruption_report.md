# Corruption Comparison Report

## Metrics: baseline vs corrupted vs repaired

| Metric | Baseline | Corrupted | Repaired | Δ corruption | Δ repair |
|---|---:|---:|---:|---:|---:|
| retrieval_hit_rate | 1.000 | 0.625 | 1.000 | -0.375 | 0.375 |
| mean_token_f1 | 1.000 | 0.505 | 1.000 | -0.495 | 0.495 |
| judge_accuracy | 0.958 | 0.458 | 0.958 | -0.500 | 0.500 |
| mean_judge_score | 4.833 | 3.125 | 4.833 | -1.708 | 1.708 |

## Data quality (passed / total)
- corrupted: 4/6
- repaired: 6/6

## Freshness
- corrupted: is_fresh=False, stale_rows=5/23
- repaired: is_fresh=True, stale_rows=0/24

## Ket luan nhan qua
1. Corruption (blank summary / stale date / noise / truncate / duplicate) -> quality checks FAIL + freshness stale -> retrieval_hit_rate & mean_token_f1 giam.
2. Repair chay lai cleaning tu raw source -> quality/freshness phuc hoi -> metrics quay lai gan baseline.

> Luu y: chi ket luan corruption 'co tac dong' khi so lieu that su thay doi. Neu recovery chua hoan toan, ghi ro signal/metric con xau.

