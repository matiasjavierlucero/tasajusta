resource "aws_s3_bucket" "models" {
  bucket = "${var.project}-models-${var.account_id}"
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Data lake — bronze/silver/gold para cuando migremos el ETL a S3 real
resource "aws_s3_bucket" "datalake" {
  bucket = "${var.project}-datalake-${var.account_id}"
}
