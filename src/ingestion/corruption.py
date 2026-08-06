"""Simulate cac dang data corruption co chu dich.

Owner: Huy Anh (Cleaning & Corruption). Pha 2 (CP5).

Moi loai corruption khop mot quality/freshness signal do duoc:
- drop_latest / stale_date  -> freshness xau
- blank_summary             -> summary_length fail
- duplicate                 -> uniqueness fail
- truncate_title / noise    -> retrieval hit & token_f1 giam
"""

from __future__ import annotations

import pandas as pd

from core.utils import normalize_whitespace, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Tao corrupted dataframe tu clean baseline + ghi corruption log."""
    df = df.copy().reset_index(drop=True)
    log: dict = {"original_rows": int(len(df)), "corruptions": []}

    # 1. Drop 3 record moi nhat (df sort published desc) -> mat freshness.
    latest_ids = df.head(3)["paper_id"].tolist()
    df = df[~df["paper_id"].isin(latest_ids)].reset_index(drop=True)
    log["corruptions"].append({"type": "drop_latest", "count": len(latest_ids), "paper_ids": latest_ids})

    # 2. Blank summary ~15% dong.
    blank_idx = df.sample(frac=0.15, random_state=42).index
    df.loc[blank_idx, "summary"] = ""
    df.loc[blank_idx, "summary_chars"] = 0
    log["corruptions"].append(
        {"type": "blank_summary", "count": int(len(blank_idx)), "paper_ids": df.loc[blank_idx, "paper_id"].tolist()}
    )

    # 3. Inject noise vao summary ~10% dong.
    noise_idx = df.sample(frac=0.10, random_state=7).index
    df.loc[noise_idx, "summary"] = df.loc[noise_idx, "summary"].astype(str) + " zzxq!!! ??? lorem noise 00xx"
    log["corruptions"].append(
        {"type": "noise_summary", "count": int(len(noise_idx)), "paper_ids": df.loc[noise_idx, "paper_id"].tolist()}
    )

    # 4. Truncate title ~10% dong.
    trunc_idx = df.sample(frac=0.10, random_state=11).index
    df.loc[trunc_idx, "title"] = df.loc[trunc_idx, "title"].astype(str).str[:8]
    log["corruptions"].append(
        {"type": "truncate_title", "count": int(len(trunc_idx)), "paper_ids": df.loc[trunc_idx, "paper_id"].tolist()}
    )

    # 5. Lam published cu di (stale) ~20% dong -> hong freshness.
    stale_idx = df.sample(frac=0.20, random_state=3).index
    df.loc[stale_idx, "published"] = "2005-01-01"
    df.loc[stale_idx, "age_days"] = 9999
    log["corruptions"].append(
        {"type": "stale_date", "count": int(len(stale_idx)), "paper_ids": df.loc[stale_idx, "paper_id"].tolist()}
    )

    # 6. Them duplicate rows -> hong uniqueness.
    dups = df.head(2).copy()
    df = pd.concat([df, dups], ignore_index=True)
    log["corruptions"].append({"type": "duplicate", "count": int(len(dups)), "paper_ids": dups["paper_id"].tolist()})

    # 7. Rebuild text_for_embedding tu du lieu da hong.
    df["text_for_embedding"] = (
        df["title"].fillna("").astype(str)
        + ". "
        + df["summary"].fillna("").astype(str)
        + " Authors: "
        + df["authors_joined"].fillna("").astype(str)
        + ". Categories: "
        + df["categories_joined"].fillna("").astype(str)
        + "."
    ).map(normalize_whitespace)

    log["final_rows"] = int(len(df))
    write_json(output_log_path, log)
    print(f"[corruption] original={log['original_rows']} -> final={log['final_rows']}; log={output_log_path}")
    return df
