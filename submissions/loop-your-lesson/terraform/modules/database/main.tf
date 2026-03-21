# Database: RDS PostgreSQL 16

resource "aws_db_subnet_group" "main" {
  name       = "${var.prefix}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.prefix}-db-subnet-group" }
}

resource "aws_db_instance" "postgres" {
  identifier = "${var.prefix}-db"

  engine         = "postgres"
  engine_version = "16"

  instance_class    = var.instance_class
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "preplydb_${replace(var.env, "-", "_")}"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false

  maintenance_window      = "Mon:03:00-Mon:04:00"
  backup_window           = "02:00-03:00"
  backup_retention_period = 1

  skip_final_snapshot       = true
  deletion_protection       = false
  multi_az                  = false
  performance_insights_enabled = false

  tags = { Name = "${var.prefix}-db" }
}
