#!/bin/bash
# Run remaining OLP Phase 5 experiments sequentially
cd /home/z/my-project/olp-rssm

for condition in olp olp_kl; do
    for seed in 0 42 84; do
        f="results/${condition}_seed${seed}.json"
        if [ -f "$f" ]; then
            echo "=== SKIP $condition seed $seed (exists) ==="
        else
            echo "=== START $condition seed $seed at $(date) ==="
            python3 run_single.py "$condition" "$seed"
            echo "=== DONE $condition seed $seed at $(date) ==="
        fi
    done
done

echo "All experiments complete at $(date)"
