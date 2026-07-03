terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  #  Backend remoto en S3: el estado vive en la nube, no en tu máquina.
  # Dos personas pueden colaborar y ninguna pisa el estado del otro (DynamoDB hace el locking).
  backend "s3" {
    bucket         = "tasajusta-tf-state-966940665955"
    key            = "main/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tasajusta-tf-lock"
  }
}

provider "aws" {
  region = var.aws_region
}
