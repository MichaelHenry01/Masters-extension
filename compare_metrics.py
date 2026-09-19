import json
import numpy as np
import matplotlib.pyplot as plt

# Load stored metrics
def load_metrics(file):
    with open(file, "r") as f:
        return json.load(f)

# Load both scheduler results
custom_metrics = load_metrics("metrics_custom.json")
default_metrics = load_metrics("metrics_default.json")

# Extract key metrics
metrics_labels = ["Avg JCT", "Avg Waiting Time", "Makespan", "Throughput"]
custom_values = [
    custom_metrics["avg_jct"],
    custom_metrics["avg_waiting"],
    custom_metrics["makespan"],
    custom_metrics["throughput"]
]
default_values = [
    default_metrics["avg_jct"],
    default_metrics["avg_waiting"],
    default_metrics["makespan"],
    default_metrics["throughput"]
]

# Print numeric comparison
print("\n📊 **Comparison of Schedulers**")
for i, label in enumerate(metrics_labels):
    print(f"{label}: Custom = {custom_values[i]:.2f}, Default = {default_values[i]:.2f}")

# **1️⃣ Bar Chart - Overall Performance Comparison**
plt.figure(figsize=(10,5))
bar_width = 0.3
x_indexes = np.arange(len(metrics_labels))

plt.bar(x_indexes - bar_width/2, custom_values, bar_width, label="Custom Scheduler", color='blue')
plt.bar(x_indexes + bar_width/2, default_values, bar_width, label="Default Scheduler", color='orange')

plt.xticks(ticks=x_indexes, labels=metrics_labels)
plt.ylabel("Value")
plt.title("📊 Performance Comparison: Custom vs. Default Scheduler")
plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.show()

# **2️⃣ Histograms - Job Completion Time Distribution**
custom_jct = [job["JCT"] for job in custom_metrics["job_metrics"] if job["JCT"] is not None]
default_jct = [job["JCT"] for job in default_metrics["job_metrics"] if job["JCT"] is not None]

plt.figure(figsize=(10,5))
plt.hist(custom_jct, bins=20, alpha=0.6, label="Custom Scheduler", color="blue")
plt.hist(default_jct, bins=20, alpha=0.6, label="Default Scheduler", color="orange")

plt.xlabel("Job Completion Time (sec)")
plt.ylabel("Number of Jobs")
plt.title("📊 Job Completion Time Distribution")
plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.show()
