# Preply Loop Infrastructure
#
# Architecture: ALB → ECS Fargate (backend + worker) → RDS + ElastiCache
#
# Before first apply:
#   1. aws s3 mb s3://preply-loop-terraform-state --region us-east-1
#   2. Create SSM parameters (see scripts/setup-ssm.sh)
#   3. terraform init && terraform workspace new dev && terraform apply

# Read database credentials from SSM
data "aws_ssm_parameter" "db_username" {
  name            = "${local.ssm_prefix}/DATABASE_USERNAME"
  with_decryption = true
}

data "aws_ssm_parameter" "db_password" {
  name            = "${local.ssm_prefix}/DATABASE_PASSWORD"
  with_decryption = true
}

# Networking: VPC, ALB, Security Groups, ACM Certificate
module "networking" {
  source      = "./modules/networking"
  prefix      = local.prefix
  domain_name = var.domain_name
}

# Database: RDS PostgreSQL 16
module "database" {
  source = "./modules/database"

  prefix            = local.prefix
  env               = local.env
  subnet_ids        = module.networking.subnet_ids
  security_group_id = module.networking.rds_security_group_id
  db_username       = data.aws_ssm_parameter.db_username.value
  db_password       = data.aws_ssm_parameter.db_password.value
}

# Redis: ElastiCache
module "redis" {
  source = "./modules/redis"

  prefix                  = local.prefix
  vpc_id                  = module.networking.vpc_id
  subnet_ids              = module.networking.subnet_ids
  allowed_security_groups = [module.networking.ecs_tasks_security_group_id]
}

# ECR: Container registry
module "ecr" {
  source = "./modules/ecr"
  prefix = local.prefix
}

# IAM: ECS roles
module "iam" {
  source = "./modules/iam"

  prefix       = local.prefix
  aws_region   = var.aws_region
  project_name = var.project_name
}

# ECS: Fargate cluster (backend + Temporal worker)
module "ecs" {
  source = "./modules/ecs"

  prefix             = local.prefix
  aws_region         = var.aws_region
  subnet_ids         = module.networking.subnet_ids
  security_group_id  = module.networking.ecs_tasks_security_group_id
  target_group_arn   = module.networking.target_group_arn
  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn
  ecr_repository_url = module.ecr.repository_url

  environment = [
    { name = "DEBUG", value = "False" },
    { name = "ALLOWED_HOSTS", value = "*" },
    { name = "DJANGO_SETTINGS_MODULE", value = "config.settings.production" },
    { name = "CSRF_TRUSTED_ORIGINS", value = "https://${var.domain_name},https://www.${var.domain_name}" },
  ]

  # App secrets + infrastructure params + Temporal secrets from SSM
  secrets = concat(
    [
      for name in local.app_secret_names : {
        name      = name
        valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.ssm_prefix}/${name}"
      }
    ],
    [
      for name in keys(local.infrastructure_params) : {
        name      = name
        valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.ssm_prefix}/${name}"
      }
    ],
    [
      for name in local.temporal_secret_names : {
        name      = name
        valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.ssm_prefix}/${name}"
      }
    ]
  )

  depends_on = [module.database, module.networking, aws_ssm_parameter.infrastructure]
}
