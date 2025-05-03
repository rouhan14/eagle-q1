# provider configuration for us-east-1
provider "aws" {
  region = var.aws_region
}

# DynamoDB Table
resource "aws_dynamodb_table" "summarization_results" {
  provider = aws

  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "summary_id"

  attribute {
    name = "summary_id"
    type = "S"
  }

  tags = {
    Name        = "CSV Summarization Results"
    Environment = var.environment
  }
}

# SNS Topic (ensure it's created in the correct region)
resource "aws_sns_topic" "summarization_events" {
  provider = aws

  name = var.sns_topic_name
}

# Optional: S3 Bucket for storing the original CSV files
resource "aws_s3_bucket" "csv_storage" {
  provider = aws

  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket_ownership_controls" "csv_storage" {
  provider = aws

  bucket = aws_s3_bucket.csv_storage.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "csv_storage" {
  depends_on = [aws_s3_bucket_ownership_controls.csv_storage]
  provider   = aws
  bucket     = aws_s3_bucket.csv_storage.id
  acl        = "private"
}

# IAM Role for the microservice
resource "aws_iam_role" "summarization_service_role" {
  provider = aws

  name = "csv-summarization-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

# IAM Policy for DynamoDB access
resource "aws_iam_policy" "dynamodb_access" {
  provider = aws

  name        = "csv-summarization-dynamodb-access"
  description = "Allow access to DynamoDB table for CSV summarization service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.summarization_results.arn
      }
    ]
  })
}

# IAM Policy for SNS publishing
resource "aws_iam_policy" "sns_publish" {
  provider = aws

  name        = "csv-summarization-sns-publish"
  description = "Allow publishing to SNS topic for CSV summarization service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "sns:Publish"
        Effect   = "Allow"
        Resource = aws_sns_topic.summarization_events.arn
      }
    ]
  })
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "dynamodb_attachment" {
  provider = aws

  role       = aws_iam_role.summarization_service_role.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

resource "aws_iam_role_policy_attachment" "sns_attachment" {
  provider = aws

  role       = aws_iam_role.summarization_service_role.name
  policy_arn = aws_iam_policy.sns_publish.arn
}
