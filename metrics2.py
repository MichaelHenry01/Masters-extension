import json
import subprocess
import datetime
import argparse
import numpy as np

def get_k8s_jobs():
    """Fetch job data from Kubernetes"""
    result = subprocess.run(["kubectl", "get", "jobs", "-o", "json"], capture_output=True, text=True, encoding="utf-8")
    jobs = json.loads(result.stdout)
    return jobs["items"]

def parse_job_times(jobs):
    """Extract job start and completion times"""
    job_times = []

    for job in jobs:
        name = job["metadata"]["name"]
        creation_time = job["metadata"]["creationTimestamp"]

        start_time = job["status"].get("startTime")
        completion_time = job["status"].get("completionTime")

        creation_time_dt = datetime.datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%SZ")
        start_time_dt = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ") if start_time else None
        completion_time_dt = datetime.datetime.strptime(completion_time, "%Y-%m-%dT%H:%M:%SZ") if completion_time else None

        if completion_time_dt:
            jct = (completion_time_dt - start_time_dt).total_seconds() if start_time_dt else None
            waiting_time = (start_time_dt - creation_time_dt).total_seconds() if start_time_dt else None
            flow_jct = (completion_time_dt - creation_time_dt).total_seconds()
            job_times.append({
                "name": name,
                "JCT": jct,
                "Waiting Time": waiting_time,
                "flow_jct": flow_jct,
                "creation_time": creation_time_dt.timestamp(),
                "start_time": start_time_dt.timestamp() if start_time_dt else None,
                "completion_time": completion_time_dt.timestamp()
            })

    return job_times

def compute_metrics(job_metrics):
    """Compute extended metrics"""
    jct_values = [job["JCT"] for job in job_metrics if job["JCT"] is not None]
    waiting_values = [job["Waiting Time"] for job in job_metrics if job["Waiting Time"] is not None]
    flow_values = [job["flow_jct"] for job in job_metrics if job.get("flow_jct") is not None]

    avg_jct = np.mean(jct_values)
    avg_waiting = np.mean(waiting_values)
    avg_flow = np.mean(flow_values)

    min_jct = np.min(jct_values)
    max_jct = np.max(jct_values)
    tail_latency = np.percentile(jct_values, 95)

    creation_times = [job["creation_time"] for job in job_metrics]
    start_times = [job["start_time"] for job in job_metrics if job["start_time"] is not None]
    completion_times = [job["completion_time"] for job in job_metrics]

    makespan_creation = max(completion_times) - min(creation_times)
    makespan_execution = max(completion_times) - min(start_times)
    avg_sched_delay = np.mean([job["start_time"] - job["creation_time"] for job in job_metrics if job["start_time"] is not None])

    throughput = len(jct_values) / makespan_creation

    return avg_jct, avg_flow, avg_waiting, min_jct, max_jct, tail_latency, makespan_creation, makespan_execution, avg_sched_delay, throughput

def compute_inter_launch_time():
    """Parse pod logs and compute average inter-launch time (ILT)"""
    result = subprocess.run(["kubectl", "get", "pods", "-o", "name"], capture_output=True, text=True)
    pod_names = result.stdout.strip().splitlines()

    start_entries = []
    for pod in pod_names:
        pod_name = pod.replace("pod/", "")
        try:
            logs = subprocess.run(["kubectl", "logs", pod_name], capture_output=True, text=True, encoding="utf-8").stdout
            for line in logs.splitlines():
                if line.startswith("START_TIME_UTC"):
                    timestamp_str = line.split(" ")[1]
                    timestamp_dt = datetime.datetime.fromisoformat(timestamp_str.replace("Z", ""))
                    start_entries.append((timestamp_dt, pod_name))
                    break
        except Exception as e:
            print(f"⚠️ Failed to get logs for {pod_name}: {e}")

    start_entries.sort()  # sort by timestamp
    start_times = [ts for ts, _ in start_entries]

    if len(start_times) < 2:
        print("⚠️ Not enough start times to compute ILT.")
        return None

    ilts = [(start_times[i] - start_times[i - 1]).total_seconds() for i in range(1, len(start_times))]
    avg_ilt = sum(ilts) / len(ilts)
    return avg_ilt

def save_metrics(scheduler, job_metrics, avg_jct, avg_flow, avg_waiting, min_jct, max_jct, tail_latency, makespan, makespan_exec, sched_delay, throughput, avg_ilt):
    metrics_filename = f"metrics_{scheduler}.json"

    metrics_data = {
        "scheduler": scheduler,
        "job_metrics": job_metrics,
        "avg_jct": avg_jct,
        "avg_flow_jct": avg_flow,
        "avg_waiting": avg_waiting,
        "min_jct": min_jct,
        "max_jct": max_jct,
        "tail_latency_95th": tail_latency,
        "makespan": makespan,
        "execution_window": makespan_exec,
        "avg_scheduling_delay": sched_delay,
        "throughput": throughput,
        "avg_ilt": avg_ilt
    }

    with open(metrics_filename, "w") as f:
        json.dump(metrics_data, f, indent=4)

    print(f"✅ {scheduler.capitalize()} Scheduler metrics saved to {metrics_filename}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure Kubernetes Job Metrics")
    parser.add_argument("--scheduler", type=str, required=True, choices=["custom", "default"], help="Specify the scheduler type")
    args = parser.parse_args()

    print(f"📊 Collecting metrics for {args.scheduler} scheduler...")

    job_metrics = parse_job_times(get_k8s_jobs())
    avg_jct, avg_flow, avg_waiting, min_jct, max_jct, tail_latency, makespan, makespan_exec, sched_delay, throughput = compute_metrics(job_metrics)

    avg_ilt = compute_inter_launch_time()
    if avg_ilt is not None:
        print(f"⏱️ Avg Inter-Launch Time (ILT): {avg_ilt:.2f} sec")
    else:
        print("⏱️ Could not compute ILT.")

    print(f"📊 Avg Job Completion Time (JCT): {avg_jct:.2f} sec")
    print(f"📊 Avg Flow JCT (creation → completion): {avg_flow:.2f} sec")
    print(f"📊 Avg Waiting Time: {avg_waiting:.2f} sec")
    print(f"📊 Min JCT: {min_jct:.2f} sec")
    print(f"📊 Max JCT: {max_jct:.2f} sec")
    print(f"📊 Tail Latency (95th percentile JCT): {tail_latency:.2f} sec")
    print(f"📊 Makespan (creation → last completion): {makespan:.2f} sec")
    print(f"📊 Execution Window (start → completion): {makespan_exec:.2f} sec")
    print(f"📊 Avg Scheduling Delay: {sched_delay:.2f} sec")
    print(f"📊 Throughput: {throughput:.2f} jobs/sec")

    save_metrics(args.scheduler, job_metrics, avg_jct, avg_flow, avg_waiting, min_jct, max_jct, tail_latency, makespan, makespan_exec, sched_delay, throughput, avg_ilt)
