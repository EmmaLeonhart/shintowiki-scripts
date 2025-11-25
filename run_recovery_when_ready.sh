#!/bin/bash
# Run this script to recover removed interwikis after cleanup completes

echo "Waiting for cleanup to complete..."
echo "Checking every 30 seconds..."

while pgrep -f "cleanup_interwiki_duplicates.py" > /dev/null; do
    sleep 30
    echo "Still running... $(date)"
done

echo ""
echo "Cleanup complete! Running recovery script..."
echo ""

python recover_removed_interwikis.py
