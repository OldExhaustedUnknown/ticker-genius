"""Run incremental verification on a few cases."""
import sys
sys.path.insert(0, "d:/ticker-genius/src")

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

from tickergenius.collection.verification_runner import VerificationRunner

# Reduce noise from http clients
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

print("Starting verification runner...")
runner = VerificationRunner()

# First, import cases from collected
print("\n1. Importing cases from collected...")
runner.import_all_cases()

# Run verification on first 5 cases as test
print("\n2. Running verification (limit=5)...")
results = runner.run_verification(limit=5)

print(f"\nProcessed: {results['total_processed']} cases")
print(f"Stats: {results['stats']}")

print("\n3. Getting updated report...")
report = runner.get_verification_report()
print(f"Legacy dependency: {report['legacy_dependency_pct']}%")

# Show details for tested cases
print("\n4. Results per case:")
for r in results['results']:
    print(f"  {r['case_id']}: before={r['before']['legacy']} legacy, after={r['after']['legacy']} legacy")
