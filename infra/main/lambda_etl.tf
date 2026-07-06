# Lambda dedicada para el ETL de MercadoLibre.
# Usa la misma imagen ECR que la Lambda de predicción pero con handler distinto.
# Timeout alto (10 min) porque pagina ~200 requests contra la API de ML.

resource "aws_iam_role" "lambda_etl" {
  name = "${var.project}-lambda-etl-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_etl_logs" {
  role       = aws_iam_role.lambda_etl.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_etl_s3" {
  name = "write-datalake"
  role = aws_iam_role.lambda_etl.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.datalake.arn,
        "${aws_s3_bucket.datalake.arn}/*",
      ]
    }]
  })
}

resource "aws_lambda_function" "etl_ml" {
  function_name = "${var.project}-etl-ml"
  role          = aws_iam_role.lambda_etl.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:latest"

  image_config {
    command = ["etl.lambda_etl_ml.handler"]
  }

  memory_size = 512
  timeout     = 600  # 10 min — pagina ~200 requests contra ML API

  environment {
    variables = {
      MINIO_BUCKET = aws_s3_bucket.datalake.bucket
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_etl_logs]
}

resource "aws_cloudwatch_log_group" "etl_ml" {
  name              = "/aws/lambda/${aws_lambda_function.etl_ml.function_name}"
  retention_in_days = 7
}
