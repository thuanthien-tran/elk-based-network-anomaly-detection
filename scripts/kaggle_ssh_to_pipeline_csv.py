#!/usr/bin/env python3
"""
Chuyen CSV dataset Kaggle SSH Anomaly sang dinh dang pipeline ELKShield.
Dataset: https://www.kaggle.com/datasets/mdwiraputradananjaya/ssh-anomaly-dataset

Kaggle co: timestamp, source_ip, username, event_type, status, label
Pipeline can: timestamp, source_ip, user, status, is_attack, ...
"""
import pandas as pd
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description='Convert Kaggle SSH anomaly CSV to pipeline format')
    parser.add_argument('--input', required=True, help='Path to ssh_anomaly_dataset.csv from Kaggle')
    parser.add_argument('--output', required=True, help='Output CSV for preprocessing/ml_detector')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] Not found: {args.input}")
        print("  Download from: https://www.kaggle.com/datasets/mdwiraputradananjaya/ssh-anomaly-dataset")
        sys.exit(1)

    print(f"Reading {args.input}...")
    df = pd.read_csv(args.input)
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")

    # Map Kaggle columns to pipeline columns (timestamp, source_ip, username, event_type, status, label)
    out = pd.DataFrame()
    out['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    out['source_ip'] = df['source_ip'].astype(str) if 'source_ip' in df.columns else ''
    out['user'] = (df['username'].astype(str) if 'username' in df.columns else df.get('user', pd.Series(['']*len(df))).astype(str))

    event_type = df.get('event_type', pd.Series(['']*len(df))).astype(str)
    out['status'] = 'failed'
    out.loc[event_type.str.contains('Accepted', case=False, na=False), 'status'] = 'accepted'
    out.loc[event_type.str.contains('Failed', case=False, na=False), 'status'] = 'failed'

    # is_attack from label: brute_force / brute_for -> True, normal -> False
    label_col = df.get('label', df.get('is_attack', None))
    if label_col is not None:
        out['is_attack'] = label_col.astype(str).str.lower().str.contains('brute', na=False)
    else:
        out['is_attack'] = (out['status'] == 'failed')
    out['attack_type'] = out['is_attack'].map({True: 'brute_force', False: ''})
    out['message'] = out.apply(
        lambda r: f"sshd: {r['status']} password for {r['user']} from {r['source_ip']} port 22 ssh2",
        axis=1
    )
    out['log_type'] = 'ssh'
    out['geoip_country'] = ''
    out['geoip_city'] = ''

    out.to_csv(args.output, index=False)
    print(f"Saved: {args.output} ({len(out)} rows)")
    print(f"  is_attack=True: {out['is_attack'].sum()}, is_attack=False: {(~out['is_attack']).sum()}")

if __name__ == '__main__':
    main()
