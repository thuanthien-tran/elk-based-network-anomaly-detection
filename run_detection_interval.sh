#!/bin/bash
# Chay Detection online 1 lan. Dat cron chay script nay moi 5-15 phut de gan real-time.
# Vi du cron: */5 * * * * /path/to/ELKShield/run_detection_interval.sh >> /path/to/ELKShield/logs/detection.log 2>&1
cd "$(dirname "$0")"
python scripts/run_pipeline_detection.py
exit $?
