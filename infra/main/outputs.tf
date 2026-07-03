output "api_url" {
  description = "URL pública del endpoint de predicción (API Gateway)"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "function_url" {
  description = "Lambda Function URL directa (sin auth, puede tener restricciones en cuentas nuevas)"
  value       = aws_lambda_function_url.predict.function_url
}

output "models_bucket" {
  description = "Bucket S3 donde viven los modelos entrenados"
  value       = aws_s3_bucket.models.bucket
}
