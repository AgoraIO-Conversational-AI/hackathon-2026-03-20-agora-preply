output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.main.arn
}

output "backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "worker_service_name" {
  value = aws_ecs_service.temporal_worker.name
}

output "backend_log_group" {
  value = aws_cloudwatch_log_group.backend.name
}

output "worker_log_group" {
  value = aws_cloudwatch_log_group.temporal_worker.name
}
