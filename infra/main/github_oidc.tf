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

# Permiso mínimo: leer y escribir en el datalake (bronze + silver del ETL)
resource "aws_iam_role_policy" "github_etl_s3" {
  name = "datalake-readwrite"
  role = aws_iam_role.github_etl.id

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

output "github_etl_role_arn" {
  description = "ARN del rol OIDC para GitHub Actions — pegalo en el workflow y en GitHub vars"
  value       = aws_iam_role.github_etl.arn
}
