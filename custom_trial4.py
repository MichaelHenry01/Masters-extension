import time
from kubernetes import client, config
from datetime import datetime
import sys
from queue import PriorityQueue
import redis  # New: Redis client

# Setup for logging and buffering
print("✅ Scheduler started successfully!", flush=True)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load Kubernetes config (use load_kube_config for local testing)
try:
    config.load_incluster_config()
except config.config_exception.ConfigException:
    config.load_kube_config()

v1 = client.CoreV1Api()
SCHEDULER_NAME = "custom-scheduler"

DELAY_SECONDS = 0
rank_counter = 0
scheduled_pod_names = []

# New: Redis client connection
r = redis.Redis(host="redis.default.svc.cluster.local", port=6379)

# === NEW/CHANGED ===
# Feature weights (now meaningful because we normalize to [0,1])
WEIGHTS = {
    "T": 0.2045,  # train_time (smaller is better)
    "R": 0.2309,  # loss_reduction_rate (larger is better)
    "M": 0.3446,  # matrix_size (smaller is better)
    "G": 0.0804,  # gradient_update_size (smaller is better)
    "C": 0.0552,  # checkpoint_interval in steps (larger is better)
    "P": 0.0844,  # model_partitions (smaller is better)
}

# Burst-level min/max cache for normalization
FEATURE_STATS = {"T": (0, 0), "R": (0, 0), "M": (0, 0), "G": (0, 0), "C": (0, 0), "P": (0, 0)}


def compute_waiting_time(pod):
    start_time = pod.metadata.creation_timestamp.replace(tzinfo=None)
    return (datetime.utcnow() - start_time).total_seconds()

# === NEW/CHANGED ===
def _extract_features(pod):
    """
    Pull raw feature values from annotations. Accepts both old and new keys for compatibility.
    - checkpoint_interval (preferred) falls back to checkpoint_frequency if present.
    - train_time (preferred) falls back to estimated_train_time if present.
    All casts are defensive because YAML annotations may be strings.
    """
    ann = pod.metadata.annotations or {}

    # Prefer new, but accept legacy keys if present
    checkpoint_interval = int(ann.get("checkpoint_interval", ann.get("checkpoint_frequency", 5)))
    train_time = int(ann.get("train_time", ann.get("estimated_train_time", 20)))

    return {
        "T": train_time,
        "R": float(ann.get("loss_reduction_rate", 0.3)),
        "M": int(ann.get("matrix_size", 2000)),
        "G": int(ann.get("gradient_update_size", 500)),
        "C": checkpoint_interval,                 # steps between checkpoints (larger is better)
        "P": int(ann.get("model_partitions", 1)),
    }

# === NEW/CHANGED ===
def update_feature_stats(pods_in_burst):
    """
    Compute per-feature min/max for normalization over the current burst.
    Call this once per burst before scoring.
    """
    global FEATURE_STATS
    keys = ["T", "R", "M", "G", "C", "P"]
    values = {k: [] for k in keys}
    for p in pods_in_burst:
        f = _extract_features(p)
        for k in keys:
            values[k].append(f[k])

    FEATURE_STATS = {k: ((min(vals), max(vals)) if len(vals) > 0 else (0, 0)) for k, vals in values.items()}

# === NEW/CHANGED ===
def _norm(x, key, larger_better):
    """
    Normalize feature 'key' to [0,1] using burst-level min/max so that 1 = better.
    - For larger_better == True:  (x - min) / (max - min)
    - For larger_better == False: (max - x) / (max - min)
    Degenerate case (min==max): return neutral 0.5
    """
    mn, mx = FEATURE_STATS.get(key, (x, x))
    rng = mx - mn
    if rng <= 0:
        return 0.5
    z = (x - mn) / rng
    return z if larger_better else (1.0 - z)

# === NEW/CHANGED ===
def adjust_priority(pod):
    """
    Normalized weighted rank:
      - Smaller is better: T, M, G, P
      - Larger is better:  R, C  (C = checkpoint_interval in steps)
    Weights in WEIGHTS dict.
    """
    # (Keep waiting_time if you want to use it later in tie-breaks or logs)
    _ = compute_waiting_time(pod)

    f = _extract_features(pod)

    # Normalize each feature to [0,1] where 1 = better
    Tn = _norm(f["T"], "T", larger_better=False)
    Rn = _norm(f["R"], "R", larger_better=True)
    Mn = _norm(f["M"], "M", larger_better=False)
    Gn = _norm(f["G"], "G", larger_better=False)
    Cn = _norm(f["C"], "C", larger_better=True)
    Pn = _norm(f["P"], "P", larger_better=False)

    # Weighted sum (now scales are aligned so weights truly control importance)
    score = (
        WEIGHTS["T"] * Tn +
        WEIGHTS["R"] * Rn +
        WEIGHTS["M"] * Mn +
        WEIGHTS["G"] * Gn +
        WEIGHTS["C"] * Cn +
        WEIGHTS["P"] * Pn
    )
    return score

def select_best_node():
    nodes = v1.list_node().items
    if not nodes:
        print("❌ No available nodes found!")
        return None
    available_nodes = [node.metadata.name for node in nodes]
    print(f"✅ Available Nodes: {available_nodes}")
    selected_node = nodes[0].metadata.name
    print(f"📌 Selected Node: {selected_node}")
    return selected_node

def patch_bound_annotation(pod):
    global rank_counter, scheduled_pod_names

    pod_name = pod.metadata.name

    # 💤 Optional delay (skip for first pod)
    if not hasattr(patch_bound_annotation, "first"):
        patch_bound_annotation.first = True
    else:
        print(f"⏱️ Sleeping for {DELAY_SECONDS} seconds before patching {pod_name}")
        time.sleep(DELAY_SECONDS)

    # ⏳ Wait for previous pod to start (except first pod)
    if rank_counter > 0:
        prev_pod_name = scheduled_pod_names[rank_counter - 1]
        print(f"⏳ Waiting for {prev_pod_name} to start execution before patching {pod_name}...")
        while not r.get(f"started:{prev_pod_name}"):
            print("actually waiting for next podddddddddd")
            time.sleep(0.05)

    try:
        now = datetime.utcnow().isoformat()
        v1.patch_namespaced_pod(
            name=pod_name,
            namespace=pod.metadata.namespace,
            body={
                "metadata": {
                    "annotations": {
                        "bound_at": now,
                        "scheduled": "true",
                    }
                }
            }
        )
        print(f"⏳ Patched bound_at={now} for {pod_name}")

        # Track scheduled pod
        scheduled_pod_names.append(pod_name)
        rank_counter += 1

    except Exception as e:
        print(f"❌ Failed to patch pod {pod_name}: {e}")

def bind_pod_to_node(pod, node_name):
    if not node_name:
        print(f"❌ ERROR: Cannot bind {pod.metadata.name}, node_name is None or empty!")
        return

    print(f"📌 Binding {pod.metadata.name} to node {node_name}...")

    target = client.V1ObjectReference(kind="Node", api_version="v1", name=node_name)
    binding = client.V1Binding(metadata=client.V1ObjectMeta(name=pod.metadata.name), target=target)

    try:
        v1.create_namespaced_pod_binding(name=pod.metadata.name, namespace=pod.metadata.namespace, body=binding)
    except client.exceptions.ApiException as e:

def schedule_pod(pod, priority):
    pod_name = pod.metadata.name

    patch_bound_annotation(pod)

    print(f"📌 Scheduling {pod_name} with priority {priority} at {datetime.now().strftime('%H:%M:%S')}...")
    best_node = select_best_node()

    if best_node:
        bind_pod_to_node(pod, best_node)
    print(f"✅ Finished scheduling {pod_name} at {datetime.now().strftime('%H:%M:%S')}")

def custom_scheduler():
    print("🔍 Watching for new pending pods...")
    tie_breaker = 0

    while True:
        try:
            pending_pods = [
                pod for pod in v1.list_namespaced_pod(namespace="default").items
                if pod.status.phase == "Pending"
                and pod.spec.scheduler_name == SCHEDULER_NAME
                and not pod.spec.node_name
            ]

            if pending_pods:
                print(f"📌 Found {len(pending_pods)} pending pods.")

                # === NEW/CHANGED === compute burst-level stats once before scoring
                update_feature_stats(pending_pods)

                print("Did update features function, really changed paritions")

                pq = PriorityQueue()
                for pod in pending_pods:
                    priority = adjust_priority(pod)
                    pq.put((-priority, tie_breaker, pod))  # Max-heap behavior
                    tie_breaker += 1

                while not pq.empty():
                    priority, _, pod = pq.get()
                    schedule_pod(pod, -priority)

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error in scheduler loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print("🚀 Custom Scheduler with Delayed Binding Started! with latest  redisssss")
    custom_scheduler()
