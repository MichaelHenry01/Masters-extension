import json
import re
from datetime import datetime

# Load pod metadata (with binding times)
with open("pod_metadata.json", encoding="utf-8") as f:
    metadata = json.load(f)

bound_times = {}
for pod in metadata["items"]:
    name = pod["metadata"]["name"]
    annotations = pod["metadata"].get("annotations", {})
    bound_at = annotations.get("bound_at")
    if bound_at and "-custom-" in name:
        bound_times[name] = datetime.fromisoformat(bound_at)

# Load train.py logs (with execution times)
with open("train_logs.txt", encoding="utf-8") as f:
    logs = f.read()

execution_times = {}
# Extract lines like: 🟢 [2025-04-24 02:15:33.245790] ml-job-4-light-custom-abc12 started executing.
pattern = re.compile(r"\[([^\]]+)\]\s+(ml-job-\d+-(?:light|io|heavy|slow)-custom-\w+)\s+started executing")
for match in pattern.findall(logs):
    timestamp_str, pod_name = match
    try:
        execution_times[pod_name] = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
    except Exception as e:
        print(f"❌ Failed to parse timestamp for {pod_name}: {e}")

# Sort both by timestamps
sorted_bound = sorted(bound_times.items(), key=lambda x: x[1])
sorted_exec = sorted(execution_times.items(), key=lambda x: x[1])

# Extract only pod names
bound_order = [name for name, _ in sorted_bound]
exec_order = [name for name, _ in sorted_exec]

# Compare order
print("🔍 Comparing execution order vs binding order...")
match_count = sum(1 for b, e in zip(bound_order, exec_order) if b == e)
total = min(len(bound_order), len(exec_order))

print(f"\n✅ {match_count} out of {total} jobs matched in execution and binding order")

# Show mismatch (if any)
print("\n🔁 First mismatches (if any):")
for i, (b, e) in enumerate(zip(bound_order, exec_order)):
    if b != e:
        print(f"❌ Order mismatch at position {i}: Bound={b} | Executed={e}")
