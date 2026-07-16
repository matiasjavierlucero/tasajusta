variable "aws_region" {
  default = "us-east-1"
}

variable "account_id" {
  default = "966940665955"
}

variable "project" {
  default = "tasajusta"
}

variable "database_url" {
  description = "Supabase DATABASE_URL para que Lambda consulte el dólar blue"
  sensitive   = true
}

variable "groq_api_key" {
  description = "API key de Groq para el agente conversacional"
  sensitive   = true
}
