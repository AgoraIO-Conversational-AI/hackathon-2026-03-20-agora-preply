output "app_url" {
  description = "Application URL"
  value       = "https://${var.domain_name}"
}

output "alb_url" {
  description = "ALB direct URL (before DNS propagation)"
  value       = "http://${module.networking.alb_dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_backend_service_name" {
  description = "ECS backend service name"
  value       = module.ecs.backend_service_name
}

output "ecs_worker_service_name" {
  description = "ECS Temporal worker service name"
  value       = module.ecs.worker_service_name
}

output "database_endpoint" {
  description = "RDS endpoint"
  value       = module.database.endpoint
}

output "backend_log_group" {
  description = "CloudWatch log group for backend"
  value       = module.ecs.backend_log_group
}

output "worker_log_group" {
  description = "CloudWatch log group for Temporal worker"
  value       = module.ecs.worker_log_group
}

output "environment" {
  description = "Current environment"
  value       = local.env
}

output "route53_name_servers" {
  description = "Update GoDaddy DNS to point to these nameservers"
  value       = aws_route53_zone.main.name_servers
}

output "custom_domain_url" {
  description = "Custom domain URL"
  value       = "https://${var.domain_name}"
}
