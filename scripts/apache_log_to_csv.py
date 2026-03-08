#!/usr/bin/env python3
"""
Convert Apache access log (Combined/Common) to CSV format pipeline.
Supports lines wrapped in double quotes (e.g. apache-http-logs-master).
Output: timestamp, source_ip, request, response, (optional is_attack if labels file).
"""
import argparse
import re
import sys
from pathlib import Path

# Apache Combined: IP - - [date] "METHOD path HTTP/x.x" status size "referer" "user-agent"
# Or with outer quote: "IP - - [date] \"METHOD path HTTP/x.x\" status size ..."
APACHE_RE = re.compile(
    r'^"?\s*'
    r'(\S+)\s+'           # clientip
    r'-\s+-\s+'
    r'\[([^\]]+)\]\s+'    # timestamp
    r'"(\S+\s+[^"]+)\s+HTTP/[^"]*"\s+'  # request (METHOD path)
    r'(\d+)\s+'           # response (status)
    r'(\d+)'              # bytes
)

def parse_line(line):
    line = line.strip()
    if not line:
        return None
    m = APACHE_RE.match(line)
    if not m:
        return None
    clientip, ts, request, response, bytes_ = m.groups()
    return {
        "timestamp": ts,
        "source_ip": clientip,
        "request": request.strip(),
        "response": int(response) if response.isdigit() else 0,
        "bytes": int(bytes_) if bytes_.isdigit() else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert Apache access log to pipeline CSV")
    parser.add_argument("--input", required=True, help="Path to .txt or .log")
    parser.add_argument("--output", required=True, help="Output CSV")
    parser.add_argument("--encoding", default="utf-8", help="File encoding (default utf-8)")
    parser.add_argument("--max-lines", type=int, default=0, help="Max lines to read (0=all)")
    args = parser.parse_args()

    rows = []
    try:
        with open(args.input, "r", encoding=args.encoding, errors="replace") as f:
            for i, line in enumerate(f):
                if args.max_lines and i >= args.max_lines:
                    break
                rec = parse_line(line)
                if rec:
                    rows.append(rec)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {args.input}")
        sys.exit(1)

    if not rows:
        print("[WARNING] No valid lines parsed. Check format (Apache Combined).")
        sys.exit(1)

    import pandas as pd
    df = pd.DataFrame(rows)
    # Normalize timestamp for pipeline (optional: parse to datetime)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
