#!/bin/bash
# AFM-Lite v0.2 Full Experiment Runner
# Estimated runtime: ~3 hours on CPU
# Run with: bash /home/z/my-project/afm-lite/run_v02_background.sh

cd /home/z/my-project/afm-lite
echo "Starting v0.2 experiments at $(date)" > v02_status.log

/home/z/.venv/bin/python3 run_v02_targeted.py >> v02_status.log 2>&1

echo "Completed at $(date)" >> v02_status.log
echo "Check results in: results_v02/"
echo "Check report: /home/z/my-project/AFM_VALIDATION_REPORT_V02_REAL.md"
