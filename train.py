import numpy as np
import time
import os
import requests
from kubernetes import client, config
from datetime import datetime
import sys
import redis

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
sys.stdout.flush()
sys.stderr.flush()


# Get own pod name
pod_name = os.environ.get("HOSTNAME", "")
namespace = "default"

# NEW: Write clean start time log for metrics script
print(f"START_TIME_UTC {datetime.utcnow().isoformat()}Z :: {pod_name}")

# print(f" [{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')}] {pod_name} started executing.")

#  NEW: Notify Redis that training has started
try:
    r = redis.Redis(host="redis.default.svc.cluster.local", port=6379)
    r.set(f"started:{pod_name}", "1")
    print(f" Marked started:{pod_name} in Redis.")
except Exception as e:
    print(f" Failed to update Redis started key for {pod_name}: {e}")


#  Fetch all environment variables with defaults
matrix_size = int(os.getenv("MATRIX_SIZE", "500"))
train_time = int(os.getenv("TRAIN_TIME", "10"))  # Max runtime in seconds
loss_reduction_rate = float(os.getenv("LOSS_REDUCTION_RATE", "0.05"))
gradient_update_size = int(os.getenv("GRADIENT_UPDATE_SIZE", "500"))
checkpoint_frequency = int(os.getenv("CHECKPOINT_FREQUENCY", "5"))
model_partitions = int(os.getenv("MODEL_PARTITIONS", "1")) 

#  Initial loss and convergence threshold
loss = 1.0
convergence_threshold = 0.01

# Compute number of steps based on workload features
base_steps = (matrix_size / 100) * (gradient_update_size / 100)
total_steps = int(max(10, base_steps))  # ensure minimum steps

print(f" Starting ML training simulation")
print(f" Matrix Size: {matrix_size}x{matrix_size}")
print(f" Computed Steps: {total_steps} |  Loss Rate: {loss_reduction_rate}")
print(f" Gradient Update Size: {gradient_update_size}")
print(f" Checkpoint Frequency: every {checkpoint_frequency} steps")
print(f" Model Partitions: {model_partitions}")
print(f" Early Stopping Threshold: {convergence_threshold}\n")

#  Allocate matrices for simulation
A = np.random.rand(matrix_size, matrix_size)
B = np.random.rand(matrix_size, matrix_size)

start_time = time.time()
last_checkpoint_step = 0

for step in range(1, total_steps + 1):
    for partition in range(model_partitions):
        print(f" Processing partition {partition+1}/{model_partitions} [step {step}/{total_steps}]")
        result = np.matmul(A, B)

        # Optional sync cost to mimic distributed training overhead
        if model_partitions > 1:
            time.sleep(0.05 * model_partitions)

    #  Reduce loss based on job-specific convergence rate
    loss *= (1 - loss_reduction_rate)
    print(f" Step {step}: Loss = {loss:.4f}")

    #  Simulated checkpointing overhead
    if step % checkpoint_frequency == 0:
        print(" Simulated checkpoint saved")
        time.sleep(0.1 + matrix_size / 50000)  # More delay for larger models
        last_checkpoint_step = step

    #  Early stopping if loss converged
    if loss <= convergence_threshold:
        print(f" Early stopping triggered at step {step}, loss = {loss:.4f}")
        break

print(" Training simulation completed.")
