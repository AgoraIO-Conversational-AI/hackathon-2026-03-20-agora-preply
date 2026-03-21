# DNS and SSL for loopyourlesson.com
#
# After apply:
# 1. Get nameservers: terraform output route53_name_servers
# 2. Update GoDaddy DNS to use these nameservers
# 3. Wait for DNS propagation (15 min - 48 hours)
# 4. Certificate validates automatically once DNS propagates

# Route53 hosted zone
resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = { Name = "${local.prefix}-zone" }
}

# DNS records for certificate validation
resource "aws_route53_record" "cert_validation" {
  for_each = module.networking.certificate_validation_records

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

# Wait for certificate validation
resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = module.networking.certificate_arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# A record: loopyourlesson.com -> ALB
resource "aws_route53_record" "apex" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = module.networking.alb_dns_name
    zone_id                = module.networking.alb_zone_id
    evaluate_target_health = true
  }
}

# A record: www.loopyourlesson.com -> ALB
resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = module.networking.alb_dns_name
    zone_id                = module.networking.alb_zone_id
    evaluate_target_health = true
  }
}
