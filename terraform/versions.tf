terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
  }

  # Bucket and region are passed at init time: see README "Deploy".
  # use_lockfile gives state locking in S3 itself, so no DynamoDB lock table is needed.
  backend "s3" {
    key          = "serverless-sales-pipeline/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "serverless-sales-pipeline"
      ManagedBy = "terraform"
    }
  }
}
