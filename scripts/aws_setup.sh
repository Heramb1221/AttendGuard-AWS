#!/bin/bash
# ============================================================
# AWS infrastructure bootstrap — REFERENCE SCRIPT, RUN STEP BY STEP.
#
# This script documents the exact AWS CLI commands used to provision
# AttendGuard's infrastructure. It is intentionally NOT meant to be run
# blindly end-to-end: several values (bucket suffix, RDS password, VPC/
# subnet IDs, key pair name) are specific to your AWS account and must be
# filled in first. Read every command before running it.
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (`aws configure`)
#   - An IAM user/role with permissions to create S3, RDS, EC2, IAM,
#     CodePipeline, CodeBuild, CodeDeploy resources
#
# Region used throughout: ap-south-1
# ============================================================
set -euo pipefail

REGION="ap-south-1"

# ---- 1. Choose a globally-unique S3 bucket name for reports ----
REPORTS_BUCKET="attendguard-reports-$(whoami)-$RANDOM"
echo "Reports bucket will be: $REPORTS_BUCKET"

aws s3api create-bucket \
    --bucket "$REPORTS_BUCKET" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"

aws s3api put-bucket-encryption \
    --bucket "$REPORTS_BUCKET" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block \
    --bucket "$REPORTS_BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "NOTE: If you ever need to configure CORS on this bucket, use boto3's"
echo "put_bucket_cors (NOT put_bucket_cors_configuration, which does not exist)."

# ---- 2. Create the CodePipeline artifact bucket (separate from reports) ----
PIPELINE_BUCKET="attendguard-pipeline-artifacts-$(whoami)-$RANDOM"
echo "Pipeline artifact bucket will be: $PIPELINE_BUCKET"

aws s3api create-bucket \
    --bucket "$PIPELINE_BUCKET" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"

# ---- 3. Create an RDS PostgreSQL instance (Free Tier: db.t3.micro) ----
# MANUAL STEP REQUIRED: choose a strong master password and export it first:
#   export RDS_MASTER_PASSWORD='<choose-a-strong-password>'
if [ -z "${RDS_MASTER_PASSWORD:-}" ]; then
    echo "ERROR: Set RDS_MASTER_PASSWORD before running this step." >&2
    exit 1
fi

aws rds create-db-instance \
    --db-instance-identifier attendguard-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 16.3 \
    --master-username attendguard_admin \
    --master-user-password "$RDS_MASTER_PASSWORD" \
    --allocated-storage 20 \
    --db-name attendguard \
    --region "$REGION" \
    --no-multi-az \
    --backup-retention-period 1 \
    --publicly-accessible

echo "RDS instance provisioning started. This takes several minutes."
echo "Check status with: aws rds describe-db-instances --db-instance-identifier attendguard-db --region $REGION"

# ---- 4. Launch the EC2 instance (Ubuntu, t3.micro) ----
# MANUAL STEP REQUIRED: replace the placeholders below with real values from
# your account (AMI ID for latest Ubuntu 22.04 in ap-south-1, your key pair
# name, and a security group that allows inbound 22 and 80).
#
# aws ec2 run-instances \
#     --image-id ami-REPLACE_WITH_UBUNTU_22_04_AMI_ID \
#     --instance-type t3.micro \
#     --key-name REPLACE_WITH_YOUR_KEY_PAIR_NAME \
#     --security-group-ids REPLACE_WITH_YOUR_SECURITY_GROUP_ID \
#     --iam-instance-profile Name=REPLACE_WITH_YOUR_EC2_INSTANCE_PROFILE_NAME \
#     --user-data file://deployment/ec2_user_data.sh \
#     --region "$REGION" \
#     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=attendguard-server}]'

echo ""
echo "============================================================"
echo "Manual steps still required (see instructions.md for full detail):"
echo "  1. Create IAM roles using the JSON policy documents in"
echo "     deployment/iam_policies/ (fill in bucket names first)."
echo "  2. Launch the EC2 instance (command above, with your AMI/key/SG/role)."
echo "  3. Create a CodeStar Connection to your GitHub repository."
echo "  4. Create the CodeBuild project referencing deployment/buildspec.yml."
echo "  5. Create the CodeDeploy application + deployment group targeting"
echo "     the EC2 instance by tag (Name=attendguard-server)."
echo "  6. Create the CodePipeline (Source -> Build -> Deploy) using the"
echo "     roles/policies above."
echo "  7. Copy .env.example to .env on the EC2 instance and fill in real"
echo "     values (RDS endpoint, password, S3 bucket name)."
echo "============================================================"
