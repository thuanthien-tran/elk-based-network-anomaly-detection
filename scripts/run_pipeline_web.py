#!/usr/bin/env python3
"""
Chay pipeline cho log web (Apache): convert -> preprocess -> [train] -> [ghi ml-alerts ES].
  --train: train model (Isolation Forest/Random Forest) va luu data/models/web_attack_model.joblib
  --write-es: ghi ket qua predict vao ml-alerts-* voi ml_model=web (can --train hoac --model-file)
Chay: python scripts/run_pipeline_web.py --input data/apache-http-logs-master/acunetix.txt --from-apache --output-dir data --train --write-es
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

def run(cmd, cwd=None):
    print(f"[RUN] {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    if r.returncode != 0:
        print(f"[FAIL] exit code {r.returncode}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Run web log pipeline")
    parser.add_argument("--input", required=True, help="Apache log file (.txt) or CSV with request/response/source_ip")
    parser.add_argument("--from-apache", action="store_true", help="Input is raw Apache log; convert first")
    parser.add_argument("--output-dir", default="data", help="Base dir for raw/processed")
    parser.add_argument("--max-lines", type=int, default=0, help="Max lines when converting Apache log (0=all)")
    parser.add_argument("--train", action="store_true", help="Train ML model (Isolation Forest) and save to data/models/web_attack_model.joblib")
    parser.add_argument("--model-file", default="", help="Path to existing .joblib model (for --write-es without --train)")
    parser.add_argument("--model-type", default="isolation_forest", choices=["isolation_forest", "random_forest"], help="Model type when --train")
    parser.add_argument("--write-es", action="store_true", help="Write predictions to Elasticsearch ml-alerts-* with ml_model=web")
    parser.add_argument("--es-host", default="127.0.0.1", help="Elasticsearch host for --write-es")
    parser.add_argument("--es-port", type=int, default=9200, help="Elasticsearch port")
    args = parser.parse_args()

    base = Path(args.output_dir)
    raw_dir = base / "raw"
    processed_dir = base / "processed"
    models_dir = base / "models"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    if args.from_apache:
        raw_csv = raw_dir / "web_apache_pipeline.csv"
        enc = "--encoding utf-8"
        maxl = f" --max-lines {args.max_lines}" if args.max_lines else ""
        if not run(f'python scripts/apache_log_to_csv.py --input "{args.input}" --output "{raw_csv}" {enc}{maxl}'):
            sys.exit(1)
        input_csv = str(raw_csv)
    else:
        input_csv = args.input

    proc_csv = processed_dir / "pipeline_web_processed.csv"
    if not run(f'python scripts/data_preprocessing.py --input "{input_csv}" --output "{proc_csv}" '
               f'--clean --extract-time --extract-ip --log-type web'):
        sys.exit(1)

    model_file = args.model_file or str(models_dir / "web_attack_model.joblib")
    predictions_csv = processed_dir / "pipeline_web_predictions.csv"

    if args.train:
        if not run(f'python scripts/ml_detector.py --input "{proc_csv}" --train --model-type {args.model_type} '
                  f'--model-file "{model_file}" --output "{predictions_csv}"'):
            sys.exit(1)
        print(f"  Model saved: {model_file}")
    else:
        # Predict only (for --write-es with existing model)
        if args.write_es and not Path(model_file).is_file():
            print(f"[ERROR] --write-es requires --train or valid --model-file. Not found: {model_file}")
            sys.exit(1)
        if args.write_es:
            if not run(f'python scripts/ml_detector.py --input "{proc_csv}" --model-file "{model_file}" --output "{predictions_csv}"'):
                sys.exit(1)

    if args.write_es:
        if not Path(predictions_csv).is_file():
            if not args.train and not args.model_file:
                print("[ERROR] No predictions file. Use --train or run ML first.")
                sys.exit(1)
            if not run(f'python scripts/ml_detector.py --input "{proc_csv}" --model-file "{model_file}" --output "{predictions_csv}"'):
                sys.exit(1)
        if not run(f'python scripts/elasticsearch_writer.py --input "{predictions_csv}" --index ml-alerts '
                  f'--host {args.es_host} --port {args.es_port} --model-name web'):
            print("[WARN] Could not write to Elasticsearch. Results saved to CSV.")
        else:
            print("  Written to ml-alerts-* (ml_model=web). View in Kibana.")

    if not args.train and not args.write_es:
        print("\n[DONE] Web pipeline (preprocess) completed.")
        print(f"  Processed: {proc_csv}")
        print("  Add --train to train model, --write-es to write ml-alerts to Elasticsearch.")


if __name__ == "__main__":
    main()
