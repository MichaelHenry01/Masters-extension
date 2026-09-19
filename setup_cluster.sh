#!/usr/bin/env bash
set -e

minikube start --driver=docker --cpus=4 --memory=7800
minikube image load micksempar/custom-scheduler:latest
minikube image load micksempar/ml-training:latest
kubectl apply -f redis.yaml
kubectl apply -f custom-scheduler-rbac.yaml
kubectl apply -f custom-scheduler-secret.yaml
kubectl patch serviceaccount custom-scheduler -n kube-system -p '{"secrets": [{"name": "custom-scheduler-token"}]}'
kubectl apply -f custom-scheduler-deployment.yaml
kubectl get pods -n kube-system
kubectl get pods
