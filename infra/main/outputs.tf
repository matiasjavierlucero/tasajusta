output "api_url" {
  description = "URL pública del endpoint de predicción"
  value       = aws_lambda_function_url.predict.function_url
}

output "models_bucket" {
  description = "Bucket S3 donde viven los modelos entrenados"
  value       = aws_s3_bucket.models.bucket
}
