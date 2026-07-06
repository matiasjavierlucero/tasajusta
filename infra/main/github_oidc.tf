# [ENTREVISTA] OIDC permite que GitHub Actions asuma roles de IAM sin credenciales long-lived.
# GitHub emite un JWT por run; AWS lo valida contra el proveedor OIDC y entrega credenciales
# temporales. Si el token se filtra, expira solo — no hay secreto que rotar.

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]

  # Thumbprint del cert TLS de GitHub — AWS lo usa para validar los JWTs
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_etl" {
  name                 = "${var.project}-github-etl"
  max_session_duration = 21600  # 6 horas — el scraper completo puede tardar 3-5h

  # Trust policy: solo workflows del repo matiasjavierlucero/tasajusta pueden asumir este rol
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # repo:owner/repo:* — limita a cualquier branch/tag/PR del repo
          "token.actions.githubusercontent.com:sub" = "repo:matiasjavierlucero/tasajusta:*"
        }
      }
    }]
  })
}

# ETL: leer/escribir datalake (bronze+silver+gold) y escribir modelos entrenados
resource "aws_iam_role_policy" "github_etl_s3" {
  name = "datalake-and-models-readwrite"
  role = aws_iam_role.github_etl.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.datalake.arn,
          "${aws_s3_bucket.datalake.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.models.arn,
          "${aws_s3_bucket.models.arn}/*",
        ]
      },
    ]
  })
}

output "github_etl_role_arn" {
  description = "ARN del rol OIDC para GitHub Actions — pegalo en el workflow y en GitHub vars"
  value       = aws_iam_role.github_etl.arn
}

# Rol separado para deploy: ECR push + Lambda update.
# El rol ETL no tiene estos permisos — Principle of Least Privilege.
resource "aws_iam_role" "github_deploy" {
  name                 = "${var.project}-github-deploy"
  max_session_duration = 3600

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          # Solo el branch master puede asumir este rol — nadie deployea desde una feature branch
          "token.actions.githubusercontent.com:sub" = "repo:matiasjavierlucero/tasajusta:ref:refs/heads/master"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "ecr-push-and-lambda-update"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # GetAuthorizationToken siempre es Resource = "*" — no aplica a un repo específico
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
        ]
        Resource = aws_ecr_repository.api.arn
      },
      {
        Effect   = "Allow"
        Action   = "lambda:UpdateFunctionCode"
        Resource = aws_lambda_function.predict.arn
      },
    ]
  })
}

output "github_deploy_role_arn" {
  description = "Pegalo en GitHub → Settings → Variables → Actions como AWS_DEPLOY_ROLE_ARN"
  value       = aws_iam_role.github_deploy.arn
}
