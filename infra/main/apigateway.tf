# [ENTREVISTA] API Gateway HTTP API v2 es más simple y barato que REST API (v1).
# Soporta el mismo payload format 2.0 que Lambda Function URLs, así Mangum funciona sin cambios.
# Lambda Function URLs tienen una restricción en cuentas nuevas de AWS; HTTP API no.

resource "aws_apigatewayv2_api" "api" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }
}

# [ENTREVISTA] AWS_PROXY integration: API Gateway pasa el request completo al Lambda
# sin transformarlo. Mangum recibe el evento v2.0 y lo convierte a ASGI para FastAPI.
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.predict.invoke_arn
  payload_format_version = "2.0"
}

# Ruta catch-all: cualquier método + cualquier path → integración Lambda
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Stage $default con auto_deploy: despliega automáticamente cuando cambia la config.
# En HTTP API, no hay concepto de "deploy manual" como en REST API.
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

# [ENTREVISTA] Lambda necesita un permiso explícito para que API Gateway lo invoque.
# Principal: apigateway.amazonaws.com, Action: lambda:InvokeFunction (no lambda:InvokeFunctionUrl).
# SourceArn limita el permiso a este API específico (principio de mínimo privilegio).
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predict.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
