#!/usr/bin/env python3
"""
ELKShield Unified Security Platform — One program orchestrates full pipeline.
Research architecture: Core (collector, processor, ml_engine, defense) + SIEM (elastic, kibana) + UI (dashboard, cli).

Chạy:  python elkshield.py
Sau đó: bấm Start Monitoring → tạo attack (test.log) → dashboard hiện alert → Suggest Defense.

Hoặc CLI:
  python elkshield.py --monitor   # chạy flow đầy đủ
  python elkshield.py --train     # train UNIFIED
  python elkshield.py --gui       # mở dashboard (mặc định)
"""
from elkshield.main import main

if __name__ == "__main__":
    main()
