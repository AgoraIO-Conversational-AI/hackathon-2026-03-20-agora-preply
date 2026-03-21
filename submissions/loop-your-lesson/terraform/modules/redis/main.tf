# ElastiCache Redis (single cache.t4g.micro node)

resource "aws_security_group" "redis" {
  name        = "${var.prefix}-redis-sg"
  description = "Allow Redis from ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.prefix}-redis-sg" }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.prefix}-redis"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.prefix}-redis" }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.prefix}-redis"
  description          = "${var.prefix} Redis for SSE streaming and caching"
  engine_version       = "7.1"
  node_type            = "cache.t4g.micro"
  num_cache_clusters   = 1

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  automatic_failover_enabled = false
  multi_az_enabled           = false

  tags = { Name = "${var.prefix}-redis" }
}
