#!/bin/bash
# Create an IAM user for GitHub Actions CI/CD
# This user has permissions to push to ECR only.
#
# Usage: bash deploy/create-iam-user.sh

set -e

AWS_REGION="us-east-1"
USER_NAME="github-actions-stock-sentinel"

echo "=== Creating IAM user for GitHub Actions ==="

# Create user
aws iam create-user --user-name $USER_NAME 2>/dev/null || echo "User already exists"

# Create policy
cat > /tmp/github-actions-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": [
        "arn:aws:ecr:us-east-1:178801185941:repository/stock-sentinel-backend",
        "arn:aws:ecr:us-east-1:178801185941:repository/stock-sentinel-frontend"
      ]
    }
  ]
}
EOF

aws iam put-user-policy \
  --user-name $USER_NAME \
  --policy-name StockSentinelECRPush \
  --policy-document file:///tmp/github-actions-policy.json

# Create access keys
echo ""
echo "--- Access Keys (save these!) ---"
aws iam create-access-key --user-name $USER_NAME --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text

echo ""
echo "Add these as GitHub Secrets:"
echo "  AWS_ACCESS_KEY_ID = <first value above>"
echo "  AWS_SECRET_ACCESS_KEY = <second value above>"
