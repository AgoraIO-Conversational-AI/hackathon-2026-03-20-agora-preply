variable "prefix" {
  description = "Resource naming prefix"
  type        = string
}

variable "domain_name" {
  description = "Custom domain name for ACM certificate (null to skip)"
  type        = string
  default     = null
}
