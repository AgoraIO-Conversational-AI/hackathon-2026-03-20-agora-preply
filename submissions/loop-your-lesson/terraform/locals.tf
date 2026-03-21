# Environment from workspace (dev/prod, default→prod for safety)

data "aws_caller_identity" "current" {}

locals {
  env    = terraform.workspace == "default" ? "prod" : terraform.workspace
  prefix = "${var.project_name}-${local.env}"

  ssm_prefix = "/${var.project_name}/${terraform.workspace}"

  # App secrets (manually created in SSM before terraform apply)
  app_secret_names = [
    "DATABASE_USERNAME",
    "DATABASE_PASSWORD",
    "SECRET_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "CLASSTIME_ADMIN_TOKEN",
    "CLASSTIME_ORG_ID",
    "CLASSTIME_SCHOOL_ID",
    "AGORA_APP_ID",
    "AGORA_APP_CERTIFICATE",
    "AGORA_CUSTOMER_ID",
    "AGORA_CUSTOMER_SECRET",
    "AVATAR_API_KEY",
    "AVATAR_ID",
    "AVATAR_VENDOR",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "THYMIA_API_KEY",
    "THYMIA_BASE_URL",
  ]

  # Temporal Cloud secrets (manually created in SSM)
  temporal_secret_names = [
    "TEMPORAL_HOST",
    "TEMPORAL_NAMESPACE",
    "TEMPORAL_API_KEY",
  ]

  # Infrastructure parameters (created by Terraform from module outputs)
  infrastructure_params = {
    DATABASE_HOST = module.database.endpoint
    DATABASE_PORT = "5432"
    DATABASE_NAME = module.database.database_name
    REDIS_URL     = "rediss://${module.redis.endpoint}:${module.redis.port}"
  }
}

# Write infrastructure params to SSM
resource "aws_ssm_parameter" "infrastructure" {
  for_each = local.infrastructure_params

  name      = "${local.ssm_prefix}/${each.key}"
  type      = "SecureString"
  value     = each.value
  overwrite = true

  tags = { ManagedBy = "terraform" }
}
