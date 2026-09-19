from kubernetes import client, config

def get_scheduling_order():
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()
        
    v1 = client.CoreV1Api()
    
    # Get all pods in the default namespace
    pods = v1.list_namespaced_pod(namespace="default").items
    
    scheduled_pods = []
    for pod in pods:
        annotations = pod.metadata.annotations
        # Only process pods that have been bound by your scheduler
        if annotations and "bound_at" in annotations:
            bound_at = annotations["bound_at"]
            
            try:
                # Name format: ml-job-1-light-custom-96jq8
                parts = pod.metadata.name.split('-')
                job_num = parts[2]   # '1'
                job_type = parts[3]  # 'light', 'heavy', 'io', or 'slow'
                
                # Store as (timestamp, "number(type)")
                scheduled_pods.append((bound_at, f"{job_num}({job_type})"))
            except IndexError:
                continue

    # Sort by the 'bound_at' timestamp string
    scheduled_pods.sort()
    
    # Extract the formatted strings
    order_list = [job[1] for job in scheduled_pods]
    
    if order_list:
        print("Final Scheduling Order:")
        print(", ".join(order_list))
    else:
        print("No pods found with the 'bound_at' annotation.")

if __name__ == "__main__":
    get_scheduling_order()