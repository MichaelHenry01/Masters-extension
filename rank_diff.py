import yaml

# Path to your specific YAML file
yaml_file = "jobs_custom.yaml"

jobs_list = []

with open(yaml_file, "r") as f:
    # Use safe_load_all to handle multiple "---" documents
    documents = yaml.safe_load_all(f)
    
    for doc in documents:
        if not doc:
            continue
            
        name = doc["metadata"]["name"]
        
        # Access the environment variables list
        envs = doc["spec"]["template"]["spec"]["containers"][0]["env"]
        
        # FIX: Use e.get("value") so it returns None instead of crashing if "value" is missing
        features = {e["name"]: e.get("value") for e in envs}
        
        # Parse features as numbers
        # These keys exist as literal values in your YAML
        matrix = int(features["MATRIX_SIZE"])
        time = int(features["TRAIN_TIME"])
        gradient = int(features["GRADIENT_UPDATE_SIZE"])
        partitions = int(features["MODEL_PARTITIONS"])
        checkpoint = int(features["CHECKPOINT_FREQUENCY"])
        loss = float(features["LOSS_REDUCTION_RATE"])
        
        # Calculation: (matrix * gradient * partitions * checkpoint) / loss
        difficulty = (time * matrix * gradient * partitions) / (loss * checkpoint)
        
        jobs_list.append({
            "job": name,
            "difficulty": difficulty
        })

# Sort jobs by difficulty (easiest first)
jobs_sorted = sorted(jobs_list, key=lambda x: x["difficulty"])

# Print Ranking
print(f"{'Rank':<5} | {'Job Name':<30} | {'Difficulty Score'}")
print("-" * 65)
for i, j in enumerate(jobs_sorted, 1):
    print(f"{i:02d}    | {j['job']:<30} | {j['difficulty']:,.2f}")