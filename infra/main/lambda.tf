#  Lambda con container image: sin límite de 250MB de zip,
# mismo Dockerfile que podría correr en ECS/EKS si necesitamos escalar.

resource "aws_lambda_function" "predict" {
  function_name = "${var.project}-predict"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"

  # IMPORTANTE: corré primero `terraform apply -target=aws_ecr_repository.api`,
  # después buildá y pusheá la imagen, y recién entonces `terraform apply` completo.
  image_uri = "${aws_ecr_repository.api.repository_url}:latest"

  memory_size = 1024  # más vCPU → cold start más rápido con LightGBM
  timeout     = 90    # cold start + descarga modelo S3 puede tomar ~40s

  environment {
    variables = {
      MODELS_BUCKET = aws_s3_bucket.models.bucket
      DATABASE_URL  = var.database_url
      GROQ_API_KEY  = var.groq_api_key
      # MINIO_ENDPOINT no seteado → boto3 usa el IAM role del Lambda
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_logs]
}

# Function URL: URL pública directa sin API Gateway (gratis, más simple)
resource "aws_lambda_function_url" "predict" {
  function_name      = aws_lambda_function.predict.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["Content-Type"]
  }
}

# [ENTREVISTA] Resource-based policy: le dice a AWS quién puede invocar este Lambda.
# Sin esto, Function URL devuelve 403 aunque authorization_type sea NONE.
# Principal "*" = cualquiera puede invocar. function_url_auth_type = "NONE" es requerido
# para que el permiso aplique solo a Function URL (no a otras formas de invocación).
resource "aws_lambda_permission" "public_url" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.predict.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_cloudwatch_log_group" "predict" {
  name              = "/aws/lambda/${aws_lambda_function.predict.function_name}"
  retention_in_days = 7  # sin retención definida, CloudWatch guarda logs para siempre (cuesta plata)
}
