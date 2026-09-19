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
        
        # Convert timestamps to datetime objects
        creation_time = datetime.datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%SZ")
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ") if start_time else None
        completion_time = datetime.datetime.strptime(completion_time, "%Y-%m-%dT%H:%M:%SZ") if completion_time else None
        
        if completion_time:
            jct = (completion_time - start_time).total_seconds() if start_time else None
            waiting_time = (start_time - creation_time).total_seconds() if start_time else None
            job_times.append({"name": name, "JCT": jct, "Waiting Time": waiting_time})
    
    return job_times

def compute_metrics(job_metrics):
    """Compute average JCT, waiting time, makespan, and throughput"""
    jct_values = [job["JCT"] for job in job_metrics if job["JCT"] is not None]
    waiting_values = [job["Waiting Time"] for job in job_metrics if job["Waiting Time"] is not None]

    avg_jct = np.mean(jct_values)
    avg_waiting = np.mean(waiting_values)

    start_times = [job["Waiting Time"] for job in job_metrics if job["Waiting Time"] is not None]
    completion_times = [job["JCT"] + job["Waiting Time"] for job in job_metrics if job["JCT"] is not None and job["Waiting Time"] is not None]

    makespan = max(completion_times) - min(start_times)
    throughput = len(jct_values) / makespan

    return avg_jct, avg_waiting, makespan, throughput

def save_metrics(scheduler, job_metrics, avg_jct, avg_waiting, makespan, throughput):
    """Save computed metrics to a JSON file"""
    metrics_filename = f"metrics_{scheduler}.json"

    metrics_data = {
        "scheduler": scheduler,
        "job_metrics": job_metrics,
        "avg_jct": avg_jct,
        "avg_waiting": avg_waiting,
        "makespan": makespan,
        "throughput": throughput
    }

    with open(metrics_filename, "w") as f:
        json.dump(metrics_data, f, indent=4)

    print(f"✅ {scheduler.capitalize()} Scheduler metrics saved to {metrics_filename}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure Kubernetes Job Metrics")
    parser.add_argument("--scheduler", type=str, required=True, choices=["custom", "default"], help="Specify the scheduler type")
    args = parser.parse_args()

    print(f"📊 Collecting metrics for {args.scheduler} scheduler...")

    # Get job data
    job_metrics = parse_job_times(get_k8s_jobs())

    # Compute metrics
    avg_jct, avg_waiting, makespan, throughput = compute_metrics(job_metrics)

    # Print results
    print(f"📊 Avg Job Completion Time (JCT): {avg_jct:.2f} sec")
    print(f"📊 Avg Waiting Time: {avg_waiting:.2f} sec")
    print(f"📊 Makespan: {makespan:.2f} sec")
    print(f"📊 Throughput: {throughput:.2f} jobs/sec")

    # Save results
    save_metrics(args.scheduler, job_metrics, avg_jct, avg_waiting, makespan, throughput)
