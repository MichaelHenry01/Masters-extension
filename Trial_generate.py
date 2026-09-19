import yaml
import random
import copy
import time

# Set a fixed seed to ensure reproducibility
i = 1
random.seed(42 + i)

# Number of jobs to generate
NUM_JOBS = 48

# Adjust this factor to control the range of matrix sizes
factor = 0.5

# Base job definition (without name/annotations)
job_template = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {},
    "spec": {
        "completions": 1,
        "parallelism": 1,
        "backoffLimit": 0,
        "template": {
            "metadata": {
                "annotations": {}
            },
            "spec": {
                "restartPolicy": "Never",
                "containers": [
                    {
                        "name": "ml-task",
                        "image": "micksempar/ml-training:latest",
                        "imagePullPolicy": "IfNotPresent",
                        "env": []
                    }
                ]
            }
        }
    }
}

# Define categories and distribute jobs
categories = ["light", "heavy", "io", "slow"]
jobs_per_category = NUM_JOBS // len(categories)

job_data_list = []
job_id = 1
for category in categories:
    for _ in range(jobs_per_category):
        if category == "light":
            matrix_size = int(random.randint(500, 800) * factor)
            train_time = random.randint(5, 10)
            loss_reduction_rate = round(random.uniform(0.5, 1.0), 2)
            gradient_update_size = random.randint(100, 400)
            checkpoint_frequency = random.randint(5, 10)
            model_partitions = random.randint(1, 2)
        elif category == "heavy":
            matrix_size = int(random.randint(2000, 3000) * factor)
            train_time = random.randint(20, 40)
            loss_reduction_rate = round(random.uniform(0.2, 0.5), 2)
            gradient_update_size = random.randint(800, 1500)
            checkpoint_frequency = random.randint(5, 10)
            model_partitions = random.randint(3, 5)
        elif category == "io":
            matrix_size = int(random.randint(1000, 1500) * factor)
            train_time = random.randint(15, 30)
            loss_reduction_rate = round(random.uniform(0.2, 0.5), 2)
            gradient_update_size = random.randint(300, 700)
            checkpoint_frequency = random.randint(1, 3)
            model_partitions = random.randint(2, 4)
        elif category == "slow":
            matrix_size = int(random.randint(800, 1300) * factor)
            train_time = random.randint(25, 40)
            loss_reduction_rate = round(random.uniform(0.05, 0.1), 2)
            gradient_update_size = random.randint(300, 700)
            checkpoint_frequency = random.randint(5, 10)
            model_partitions = random.randint(1, 3)

        job_data_list.append({
            "job_name": f"ml-job-{job_id}-{category}",
            "matrix_size": matrix_size,
            "train_time": train_time,
            "model_partitions": model_partitions,
            "loss_reduction_rate": loss_reduction_rate,
            "gradient_update_size": gradient_update_size,
            "checkpoint_frequency": checkpoint_frequency
        })
        job_id += 1

yaml_documents_custom = []
yaml_documents_default = []

for idx, job_data in enumerate(job_data_list):
    for scheduler in ["custom-scheduler", "default-scheduler"]:
        job = copy.deepcopy(job_template)
        job["metadata"]["name"] = f"{job_data['job_name']}-{scheduler.split('-')[0]}"
        job["spec"]["template"]["metadata"]["annotations"] = {
            "model_partitions": str(job_data["model_partitions"]),
            "matrix_size": str(job_data["matrix_size"]),
            "train_time": str(job_data["train_time"]),
            "loss_reduction_rate": str(job_data["loss_reduction_rate"]),
            "gradient_update_size": str(job_data["gradient_update_size"]),
            "checkpoint_frequency": str(job_data["checkpoint_frequency"])
        }
        job["spec"]["template"]["spec"]["containers"][0]["env"] = [
            {"name": "MATRIX_SIZE", "value": str(job_data["matrix_size"])},
            {"name": "TRAIN_TIME", "value": str(job_data["train_time"])},
            {"name": "MODEL_PARTITIONS", "value": str(job_data["model_partitions"])},
            {"name": "LOSS_REDUCTION_RATE", "value": str(job_data["loss_reduction_rate"])},
            {"name": "GRADIENT_UPDATE_SIZE", "value": str(job_data["gradient_update_size"])},
            {"name": "CHECKPOINT_FREQUENCY", "value": str(job_data["checkpoint_frequency"])}
        ]

        if scheduler == "custom-scheduler":
            job["spec"]["template"]["spec"]["schedulerName"] = scheduler
            
            # Add USE_EXECUTION_GATE=true for custom scheduler jobs
            job["spec"]["template"]["spec"]["containers"][0]["env"].append({
                "name": "USE_EXECUTION_GATE",
                "value": "true"
            })
            
            
            # Add downward API env var for execution gate
            job["spec"]["template"]["spec"]["containers"][0]["env"].append({
                "name": "EXECUTION_GATE",
                "valueFrom": {
                    "fieldRef": {
                        "fieldPath": "metadata.annotations['execution_gate']"
                    }
                }
            })
            yaml_documents_custom.append(yaml.dump(job, default_flow_style=False))
        else:
            yaml_documents_default.append(yaml.dump(job, default_flow_style=False))

with open("jobs_custom.yaml", "w") as file:
    file.write("\n---\n".join(yaml_documents_custom))

with open("jobs_default.yaml", "w") as file:
    file.write("\n---\n".join(yaml_documents_default))

print("Generated 'jobs_custom.yaml' & 'jobs_default.yaml' without init containers or resource requests.")
