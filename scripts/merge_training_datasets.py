#!/usr/bin/env python3
"""
Gộp các dataset SSH đã preprocess (Synthetic, Russell Mitchell, Kaggle, Custom) thành unified training dataset.
Chuẩn hóa cột (bỏ host, thêm geoip nếu thiếu). File nào tồn tại thì gộp, thiếu thì bỏ qua.
SIEM + ML Hybrid - Offline Training Pipeline.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cột chuẩn sau preprocess (theo data_preprocessing + ml_detector)
STANDARD_COLS = [
    "timestamp", "source_ip", "user", "status", "message",
    "attack_type", "is_attack", "geoip_country", "geoip_city", "log_type",
    "hour", "day_of_week", "day_of_month", "month",
    "is_weekend", "is_business_hours",
    "requests_per_ip", "ip_hash",
    "failed_login_count", "failed_login_count_window", "attack_type_frequency",
]


def normalize_df(df):
    """Chuẩn hóa DataFrame: bỏ cột thừa (host), thêm cột thiếu (geoip)."""
    out = df.copy()
    if "host" in out.columns:
        out = out.drop(columns=["host"])
    for col in STANDARD_COLS:
        if col not in out.columns:
            if col in ("geoip_country", "geoip_city"):
                out[col] = 0.0
            else:
                out[col] = None
    # Chỉ giữ cột có trong STANDARD_COLS
    cols = [c for c in STANDARD_COLS if c in out.columns]
    out = out[cols].copy()
    out["geoip_country"] = pd.to_numeric(out["geoip_country"], errors="coerce").fillna(0)
    out["geoip_city"] = pd.to_numeric(out["geoip_city"], errors="coerce").fillna(0)
    if "is_attack" in out.columns:
        out["is_attack"] = out["is_attack"].fillna(False)
        out["is_attack"] = out["is_attack"].astype(bool)
    return out


def rebalance_unified(df: pd.DataFrame, target_attack_ratio: float = 0.6, seed: int = 42) -> pd.DataFrame:
    """
    Rebalance unified dataset by downsampling attack rows only.
    Strategy: keep all normal rows, reduce attack-heavy sources first (Kaggle).
    """
    if "is_attack" not in df.columns:
        return df
    if "_source" not in df.columns:
        df["_source"] = "Unknown"

    work = df.copy()
    work["is_attack"] = work["is_attack"].astype(bool)

    n_attack = int(work["is_attack"].sum())
    n_total = len(work)
    n_normal = n_total - n_attack
    if n_total <= 0 or n_normal <= 0:
        return work

    target_attack = int(round((target_attack_ratio * n_normal) / max(1e-9, (1.0 - target_attack_ratio))))
    if n_attack <= target_attack:
        return work

    attack_df = work[work["is_attack"]].copy()
    normal_df = work[~work["is_attack"]].copy()
    drop_need = n_attack - target_attack

    # Drop attacks mostly from Kaggle first, then Synthetic, then Custom, then Russell.
    drop_priority = ["Kaggle", "Synthetic", "Custom", "Russell Mitchell"]
    keep_attack_parts = []
    rng_state = seed
    remaining_drop = drop_need
    remaining_attack = attack_df.copy()

    for src in drop_priority:
        src_rows = remaining_attack[remaining_attack["_source"] == src]
        if src_rows.empty:
            continue
        if remaining_drop <= 0:
            break
        can_drop = min(len(src_rows), remaining_drop)
        keep_src = src_rows.sample(n=(len(src_rows) - can_drop), random_state=rng_state) if can_drop < len(src_rows) else src_rows.iloc[0:0]
        keep_attack_parts.append(keep_src)
        remaining_drop -= can_drop
        remaining_attack = remaining_attack[remaining_attack["_source"] != src]
        rng_state += 1

    # Keep all non-priority attack rows.
    if not remaining_attack.empty:
        keep_attack_parts.append(remaining_attack)

    keep_attack = pd.concat(keep_attack_parts, ignore_index=True) if keep_attack_parts else attack_df.iloc[0:0]

    # Safety fallback: exact target by random sample if still above target.
    if len(keep_attack) > target_attack:
        keep_attack = keep_attack.sample(n=target_attack, random_state=seed)

    out = pd.concat([normal_df, keep_attack], ignore_index=True)
    return out


def main():
    parser = argparse.ArgumentParser(description="Gộp các dataset SSH đã preprocess thành unified training dataset (Synthetic, Russell, Kaggle, Custom).")
    parser.add_argument("--synthetic", default=None,
                        help="CSV đã preprocess từ Synthetic (mặc định: data/processed/logs.csv)")
    parser.add_argument("--russell", default=None,
                        help="CSV đã preprocess từ Russell Mitchell (mặc định: data/processed/russellmitchell_processed.csv)")
    parser.add_argument("--kaggle", default=None,
                        help="CSV đã preprocess từ Kaggle (mặc định: data/processed/pipeline_ssh_processed.csv)")
    parser.add_argument("--custom", default=None,
                        help="CSV đã preprocess từ tệp tùy chọn (mặc định: data/processed/custom_processed.csv). Bỏ qua nếu không tồn tại.")
    parser.add_argument("--output", "-o", default=None,
                        help="Unified CSV (mặc định: data/training/unified_ssh_dataset.csv)")
    parser.add_argument(
        "--balance-mode",
        choices=["off", "moderate"],
        default="moderate",
        help="Can bang sau khi gop (mac dinh: moderate)",
    )
    parser.add_argument(
        "--target-attack-ratio",
        type=float,
        default=0.60,
        help="Ty le attack muc tieu khi can bang moderate (mac dinh: 0.60)",
    )
    args = parser.parse_args()

    root = PROJECT_ROOT
    synthetic_path = Path(args.synthetic) if args.synthetic else root / "data" / "processed" / "logs.csv"
    russell_path = Path(args.russell) if args.russell else root / "data" / "processed" / "russellmitchell_processed.csv"
    kaggle_path = Path(args.kaggle) if args.kaggle else root / "data" / "processed" / "pipeline_ssh_processed.csv"
    custom_path = Path(args.custom) if args.custom else root / "data" / "processed" / "custom_processed.csv"
    out_path = Path(args.output) if args.output else root / "data" / "training" / "unified_ssh_dataset.csv"
    if not out_path.is_absolute():
        out_path = root / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    names = []

    # Tất cả nguồn trong data/processed có thể dùng cho train: Synthetic, Russell, Kaggle, Custom (nếu có)
    for path, name in [
        (synthetic_path, "Synthetic"),
        (russell_path, "Russell Mitchell"),
        (kaggle_path, "Kaggle"),
        (custom_path, "Custom"),
    ]:
        if not path.exists():
            print(f"[SKIP] Khong tim thay: {path} ({name})")
            continue
        try:
            df = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
            df = normalize_df(df)
            df["_source"] = name
            frames.append(df)
            names.append(name)
            print(f"  + {name}: {len(df)} dong")
        except Exception as e:
            print(f"[LOI] Doc {path}: {e}")
            sys.exit(1)

    if not frames:
        print("[LOI] Khong co file nao de gop. Chay preprocess cho tung nguon truoc.")
        sys.exit(1)

    unified = pd.concat(frames, ignore_index=True)

    # Rebalance after merge (default: moderate -> target attack ratio ~60%).
    if args.balance_mode == "moderate":
        before_total = len(unified)
        before_attack = int(unified["is_attack"].astype(bool).sum()) if "is_attack" in unified.columns else 0
        unified = rebalance_unified(unified, target_attack_ratio=args.target_attack_ratio, seed=42)
        after_total = len(unified)
        after_attack = int(unified["is_attack"].astype(bool).sum()) if "is_attack" in unified.columns else 0
        print(
            f"  Rebalance(moderate): {before_total} -> {after_total} dong, "
            f"Attack {before_attack} -> {after_attack}"
        )

    unified = unified.drop(columns=["_source"], errors="ignore")
    # Sắp xếp theo thời gian nếu có
    if "timestamp" in unified.columns:
        unified["timestamp"] = pd.to_datetime(unified["timestamp"], errors="coerce")
        unified = unified.sort_values("timestamp").reset_index(drop=True)
    unified.to_csv(out_path, index=False)
    n_attack = unified["is_attack"].sum() if "is_attack" in unified.columns else 0
    n_attack = int(n_attack)
    print(f"\nDa gop {len(unified)} dong -> {out_path}")
    print(f"  Normal: {len(unified) - n_attack}, Attack: {n_attack}")
    # Log ro nhung dataset da duoc dua vao unified
    print("  Nguon dataset dung trong unified:", ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
