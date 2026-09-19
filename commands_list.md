# Kubernetes and Docker Commands for Custom Scheduler Setup

### I need to build the scheduler and the train images before running the setup_cluster.sh as it only loads those images into minikube

minikube delete --all --purge

docker build --no-cache -t micksempar/custom-scheduler:latest -f Dockerfile-scheduler-python .

docker build -t micksempar/ml-training:latest -f Dockerfile-ml .

bash setup_cluster.sh
python Trial_generate.py

-------------------------------

kubectl apply -f jobs_default.yaml
python metrics2.py --scheduler default  

kubectl apply -f jobs_custom.yaml
python metrics2.py --scheduler custom  
 
------------------------------------

kubectl get pods -n kube-system

kubectl delete deployment custom-scheduler -n kube-system

docker build --no-cache -t micksempar/custom-scheduler:latest -f Dockerfile-scheduler-python .

minikube image load micksempar/custom-scheduler:latest

kubectl apply -f custom-scheduler-deployment.yaml
=========================================

python job_order.py

python GA.py

=========================================


--------------------------------------------------------
## Create Kubernetes Cluster
```sh
kind create cluster --name ml-cluster --config kind-config.yaml
minikube start --driver=docker --cpus=4 --memory=7800

```

## check and delete Taints for 
```sh
kubectl describe node ml-cluster-control-plane | grep -i taint
kubectl taint nodes --all node-role.kubernetes.io/control-plane- 

kubectl describe node minikube | grep -i taint


```


## Build and Push Custom Scheduler Docker Image
```sh
kubectl delete deployment custom-scheduler -n kube-system

docker build --no-cache -t micksempar/custom-scheduler:latest -f Dockerfile-scheduler-python .


docker push micksempar/custom-scheduler:latest
```
## Build and Push Train.py
```sh
docker build -t micksempar/ml-training:latest -f Dockerfile-ml .
docker push micksempar/ml-training:latest
```
## Load the images to kind 
```sh

kind load docker-image micksempar/ml-training:latest --name ml-cluster
kind load docker-image micksempar/custom-scheduler:latest --name ml-cluster

minikube image load micksempar/custom-scheduler:latest
minikube image load micksempar/ml-training:latest


```

kubectl apply -f redis.yaml



## Apply Kubernetes Configurations
```sh
kubectl apply -f custom-scheduler-rbac.yaml
kubectl apply -f custom-scheduler-secret.yaml
```

## Patch Service Account for Custom Scheduler
```sh
kubectl patch serviceaccount custom-scheduler -n kube-system -p '{"secrets": [{"name": "custom-scheduler-token"}]}'
```



## Deploy Custom Scheduler
```sh
kubectl apply -f custom-scheduler-deployment.yaml
```

## Verify Custom Scheduler is Running
```sh
kubectl get pods -n kube-system
kubectl logs -n kube-system deployment/custom-scheduler -f
kubectl rollout restart deployment/custom-scheduler -n kube-system
```

python Trial_generate.py
---

## Run Jobs with Custom Scheduler
```sh
Python3 final_generate_jobs.py
kubectl apply -f jobs_custom.yaml
python3 metrics.py --scheduler custom  

python metrics2.py --scheduler custom  

python3 metrics2.py --scheduler custom  

```

## Before running with other scheduler 
```sh
REDIS_POD=$(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it "$REDIS_POD" -- redis-cli FLUSHALL


```



## Cleanup and Run Jobs with Default Scheduler
```sh
kubectl delete -f jobs_custom.yaml
kubectl apply -f jobs_default.yaml
python3 metrics.py --scheduler default  

python metrics2.py --scheduler default  

python3 metrics2.py --scheduler default  

```

## PLOTTTTTTTTT Metrics
python plot_metrics.py   --custom metrics_custom.json   --default metrics_default.json   --reversed metrics_reversed.json   --outdir figs

python plot_metrics2.py   --custom metrics_custom.json   --default metrics_default.json   --outdir figs




## Compare Metrics
```sh
python3 compare_metrics.py  


## Compare orderrrrrrrr
```sh


kubectl get pods -n default -o json > pod_metadata.json


python3 analyze_jct_by_category.py
python analyze_jct_by_category.py



kubectl get pods -n default -o name | while read pod; do
  echo "==== $pod ====" >> train_logs.txt
  kubectl logs $pod -n default >> train_logs.txt
done


python3 compare_order.py 
python compare_order.py 

```

kubectl delete jobs --all
kubectl get pods

# Setup the clusterrrrrrrrrr

bash setup_cluster.sh




# multi fig plotsssssss

python plot_metrics2_multi.py --custom metrics_custom*.json --default metrics_default*.json --outdir Multi_figs

python plot_metrics2_multi.py --custom metrics_custom*.json --outdir Multi_figs
