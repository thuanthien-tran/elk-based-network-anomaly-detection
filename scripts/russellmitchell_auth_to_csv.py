#!/usr/bin/env python3
"""
Chuyen auth.log tu dataset russellmitchell (gather/*/logs/auth.log) thanh CSV pipeline ELKShield.
Ho tro gắn nhan tu labels/intranet_server/logs/auth.log (JSONL: line, labels) de danh is_attack.
Chay: python scripts/russellmitchell_auth_to_csv.py [--data-dir data/russellmitchell] [--output data/raw/russellmitchell_auth.csv] [--with-labels]
"""
import argparse
import re
import json
from pathlib import Path
from datetime import datetime

def parse_syslog_line(line):
    """Parse one line of syslog: timestamp, host, proc, message. Returns (timestamp_str, host, message) or None."""
    # Jan 23 16:30:46 intranet-server sshd[25184]: Accepted publickey for jhall from ...
    m = re.match(r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s*(.*)$', line.strip())
    if not m:
        return None
    ts_str, host, proc, pid, message = m.groups()
    # Build full message for downstream parser (optional: include host in message)
    return (ts_str, host or '', message or '')

def parse_ssh_message(message):
    """Reuse logic from data_extraction.parse_ssh_message."""
    import sys
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.data_extraction import parse_ssh_message as _parse
    return _parse(message)

def main():
    parser = argparse.ArgumentParser(description='Convert russellmitchell auth.log to pipeline CSV')
    parser.add_argument('--data-dir', default='data/russellmitchell', help='Root of russellmitchell dataset')
    parser.add_argument('--output', default='data/raw/russellmitchell_auth.csv', help='Output CSV path')
    parser.add_argument('--with-labels', action='store_true', help='Use labels to set is_attack for escalation/attacker lines')
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"Error: not a directory: {data_dir}")
        return 1
    
    # Find all auth.log and auth.log.* under gather/*/logs/
    auth_files = []
    for p in data_dir.glob('gather/*/logs/auth.log*'):
        if p.is_file():
            auth_files.append(p)
    
    if not auth_files:
        print(f"No auth.log* found under {data_dir}/gather/*/logs/")
        return 1
    
    # Optional: load labels (intranet_server only has auth.log labels in this dataset)
    attack_lines = set()
    if args.with_labels:
        labels_file = data_dir / 'labels' / 'intranet_server' / 'logs' / 'auth.log'
        if labels_file.is_file():
            with open(labels_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        num = obj.get('line')
                        labels = obj.get('labels', [])
                        if num is not None and labels:
                            if any('attacker' in str(l).lower() or l in ('escalate', 'escalated_command', 'escalated_sudo_command', 'escalated_sudo_session') for l in labels):
                                attack_lines.add(int(num))
                    except json.JSONDecodeError:
                        pass
            print(f"Loaded {len(attack_lines)} attack line numbers from labels")
    
    rows = []
    for auth_path in sorted(auth_files):
        with open(auth_path, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                parsed = parse_syslog_line(line)
                if not parsed:
                    continue
                ts_str, host, message = parsed
                source_ip, user, status, is_attack, attack_type = parse_ssh_message(message)
                if not message.strip():
                    continue
                msg_lower = message.lower()
                if 'sshd' not in msg_lower and 'ssh' not in msg_lower and 'su[' not in msg_lower and 'sudo' not in msg_lower and 'pam_unix' not in msg_lower and 'cron' not in msg_lower:
                    continue
                if args.with_labels and 'intranet_server' in str(auth_path) and line_num in attack_lines:
                    is_attack = True
                    if not attack_type:
                        attack_type = 'escalation'
                # Add year for datetime parsing (dataset is 2022)
                ts_with_year = f"2022 {ts_str}" if re.match(r'^\w{3}\s+\d{1,2}\s+', ts_str) else ts_str
                rows.append({
                    'timestamp': ts_with_year,
                    'host': host,
                    'source_ip': source_ip or '',
                    'user': user or '',
                    'status': status or '',
                    'message': message.strip(),
                    'attack_type': attack_type or '',
                    'is_attack': is_attack,
                    'log_type': 'ssh',
                })
    
    if not rows:
        print("No SSH/auth lines found.")
        return 1
    
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['timestamp', 'host', 'source_ip', 'user', 'status', 'message', 'attack_type', 'is_attack', 'log_type'])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0

if __name__ == '__main__':
    exit(main())
