output "vpc_id" {
  value = aws_default_vpc.default.id
}

output "subnet_ids" {
  value = [aws_default_subnet.az1.id, aws_default_subnet.az2.id]
}

output "alb_dns_name" {
  value = aws_lb.backend.dns_name
}

output "alb_zone_id" {
  value = aws_lb.backend.zone_id
}

output "target_group_arn" {
  value = aws_lb_target_group.backend.arn
}

output "ecs_tasks_security_group_id" {
  value = aws_security_group.ecs_tasks.id
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "certificate_arn" {
  description = "ACM certificate ARN"
  value       = var.domain_name != null ? aws_acm_certificate.alb[0].arn : null
}

output "certificate_validation_records" {
  description = "DNS validation records for ALB ACM certificate"
  value = var.domain_name != null ? {
    for dvo in aws_acm_certificate.alb[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}
}
