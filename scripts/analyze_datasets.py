#!/usr/bin/env python3
"""
Phan tich cac dataset trong data/: CSV, thu muc log, thong ke va kha nang dung cho pipeline.
Chay: python scripts/analyze_datasets.py [--data-dir data] [--output report.txt]
"""
import os
import sys
import argparse
from pathlib import Path

def safe_read_csv(path, nrows=50000):
    try:
        import pandas as pd
        return pd.read_csv(path, nrows=nrows)
    except Exception as e:
        return None, str(e)

def analyze_data_dir(data_dir):
    data_path = Path(data_dir)
    if not data_path.is_dir():
        return {"error": f"Not a directory: {data_dir}"}
    
    report = {"path": str(data_path.absolute()), "csv_files": [], "log_folders": [], "other_dirs": []}
    
    for root, dirs, files in os.walk(data_path):
        rel = Path(root).relative_to(data_path) if root != str(data_path) else Path(".")
        for f in files:
            path = Path(root) / f
            rel_path = rel / f
            try:
                size_mb = path.stat().st_size / (1024 * 1024)
            except OSError:
                size_mb = 0
            
            if f.endswith(".csv"):
                report["csv_files"].append({
                    "path": str(rel_path).replace("\\", "/"),
                    "size_mb": round(size_mb, 2),
                    "full": str(path),
                })
        
        if rel == Path("."):
            for d in dirs:
                if d in ("dataset1", "apache-http-logs-master", "caudit-master", "russellmitchell"):
                    report["log_folders"].append(d)
                elif d not in ("raw", "processed", "datasets"):
                    report["other_dirs"].append(d)
    
    return report

def analyze_csv_detail(csv_path):
    try:
        import pandas as pd
        df = pd.read_csv(csv_path, nrows=100000)
        info = {
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        }
        if "is_attack" in df.columns:
            info["is_attack_counts"] = df["is_attack"].value_counts().to_dict()
        if "label" in df.columns:
            info["label_counts"] = df["label"].value_counts().head(10).to_dict()
        if "timestamp" in df.columns:
            info["has_timestamp"] = True
        if "source_ip" in df.columns:
            info["unique_ips"] = int(df["source_ip"].nunique())
        return info
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Analyze datasets in data/")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--output", default=None, help="Write report to file")
    parser.add_argument("--csv-detail", action="store_true", help="Include per-CSV stats (slower)")
    args = parser.parse_args()
    
    base = Path(args.data_dir)
    if not base.is_dir():
        base = Path(__file__).resolve().parent.parent / args.data_dir
    if not base.is_dir():
        print(f"[ERROR] Directory not found: {args.data_dir}")
        sys.exit(1)
    
    report = analyze_data_dir(base)
    
    lines = []
    lines.append("=" * 60)
    lines.append("ELKShield - Dataset Analysis Report")
    lines.append("=" * 60)
    lines.append(f"Data directory: {report['path']}")
    lines.append("")
    
    lines.append("--- CSV files ---")
    for f in report.get("csv_files", []):
        lines.append(f"  {f['path']}  ({f['size_mb']} MB)")
        if args.csv_detail and f["path"].endswith(".csv"):
            full = f.get("full") or str(base / f["path"])
            if os.path.isfile(full):
                detail = analyze_csv_detail(full)
                if "error" not in detail:
                    lines.append(f"    Rows (sample): {detail.get('rows', 'N/A')}, Columns: {len(detail.get('columns', []))}")
                    if "is_attack_counts" in detail:
                        lines.append(f"    is_attack: {detail['is_attack_counts']}")
                    if "label_counts" in detail:
                        lines.append(f"    label (top): {detail['label_counts']}")
                    if detail.get("has_timestamp"):
                        lines.append("    Has timestamp (time-split OK)")
                else:
                    lines.append(f"    Error: {detail['error']}")
    if not report.get("csv_files"):
        lines.append("  (none)")
    
    lines.append("")
    lines.append("--- Dataset / log folders ---")
    for d in report.get("log_folders", []):
        lines.append(f"  {d}/")
    if report.get("other_dirs"):
        lines.append("  Other: " + ", ".join(report["other_dirs"]))
    
    lines.append("")
    lines.append("--- Suitability ---")
    lines.append("  SSH pipeline: use CSV with source_ip, status, (is_attack) or auth.log.anon from dataset1/")
    lines.append("  Web pipeline: use CSV with request, response, source_ip or apache-http-logs-master/*.txt")
    lines.append("  Time-split train: requires 'timestamp' column.")
    lines.append("=" * 60)
    
    text = "\n".join(lines)
    print(text)
    
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(text, encoding="utf-8")
        print(f"\nReport saved to {out_path}")

if __name__ == "__main__":
    main()
