resource "aws_lambda_function" "kavak" {
  function_name = "${var.project}-kavak"
  role          = aws_iam_role.lambda_kavak.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:latest"

  image_config {
    command = ["etl.lambda_kavak.handler"]
  }

  memory_size = 512
  timeout     = 600

  environment {
    variables = {
      MINIO_BUCKET = aws_s3_bucket.datalake.bucket
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_kavak_logs]
}

resource "aws_iam_role" "lambda_kavak" {
  name = "${var.project}-lambda-kavak-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_kavak_logs" {
  role       = aws_iam_role.lambda_kavak.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_kavak_s3" {
  name = "write-datalake"
  role = aws_iam_role.lambda_kavak.id

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

resource "aws_cloudwatch_log_group" "kavak" {
  name              = "/aws/lambda/${aws_lambda_function.kavak.function_name}"
  retention_in_days = 7
}
