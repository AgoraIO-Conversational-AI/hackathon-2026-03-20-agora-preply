#!/bin/bash
# Deploy: build Docker image, push to ECR, redeploy ECS services
set -e

REGION="${AWS_REGION:-us-east-1}"
TF_DIR="$(dirname "$0")/../terraform"

echo "Reading Terraform outputs..."
ECR_URL=$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)
CLUSTER=$(terraform -chdir="$TF_DIR" output -raw ecs_cluster_name)
BACKEND_SVC=$(terraform -chdir="$TF_DIR" output -raw ecs_backend_service_name)
WORKER_SVC=$(terraform -chdir="$TF_DIR" output -raw ecs_worker_service_name)

echo "ECR: $ECR_URL"
echo "Cluster: $CLUSTER"

echo "Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URL"

echo "Building and pushing Docker image (ARM64)..."
docker buildx build --platform linux/arm64 -t "$ECR_URL:latest" --push .

echo "Resolving latest task definitions..."
BACKEND_TD=$(aws ecs list-task-definitions --family-prefix "${CLUSTER%-cluster}-backend" --status ACTIVE --sort DESC --region "$REGION" --query 'taskDefinitionArns[0]' --output text)
WORKER_TD=$(aws ecs list-task-definitions --family-prefix "${CLUSTER%-cluster}-temporal-worker" --status ACTIVE --sort DESC --region "$REGION" --query 'taskDefinitionArns[0]' --output text)

echo "Backend TD: $BACKEND_TD"
echo "Worker TD:  $WORKER_TD"

echo "Redeploying backend service..."
aws ecs update-service --cluster "$CLUSTER" --service "$BACKEND_SVC" --task-definition "$BACKEND_TD" --force-new-deployment --region "$REGION" > /dev/null

echo "Redeploying Temporal worker..."
aws ecs update-service --cluster "$CLUSTER" --service "$WORKER_SVC" --task-definition "$WORKER_TD" --force-new-deployment --region "$REGION" > /dev/null

APP_URL=$(terraform -chdir="$TF_DIR" output -raw app_url)
echo ""
echo "Deploy triggered. Services will roll out in ~2 minutes."
echo "App: $APP_URL"
echo "Logs: aws logs tail /ecs/$CLUSTER --follow --region $REGION"
