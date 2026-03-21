# Terraform state in S3
# Create bucket before first init: aws s3 mb s3://preply-loop-terraform-state --region us-east-1

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "preply-loop-terraform-state"
    key          = "terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "preply-loop"
      Environment = local.env
      ManagedBy   = "terraform"
    }
  }
}
