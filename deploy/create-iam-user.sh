#!/bin/bash
# Create an IAM user for GitHub Actions CI/CD.
# This user has permissions to manage ECR, EC2, and IAM for Stock Sentinel.
#
# THIS IS THE ONLY SCRIPT YOU NEED TO RUN LOCALLY.
# Everything else is done via GitHub Actions.
#
# Usage: bash deploy/create-iam-user.sh

set -e

USER_NAME="github-actions-stock-sentinel"

echo "=== Creating IAM user for GitHub Actions ==="

aws iam create-user --user-name $USER_NAME 2>/dev/null || echo "User already exists"

cat > /tmp/github-actions-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECR",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:CreateRepository",
        "ecr:DescribeRepositories",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImageScanningConfiguration"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeImages",
        "ec2:DescribeVpcs",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeKeyPairs",
        "ec2:CreateKeyPair",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAM",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:CreateInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:PassRole",
        "iam:GetRole",
        "iam:GetInstanceProfile"
      ],
      "Resource": [
        "arn:aws:iam::178801185941:role/StockSentinelEC2Role",
        "arn:aws:iam::178801185941:instance-profile/StockSentinelEC2Profile"
      ]
    }
  ]
}
EOF

aws iam put-user-policy \
  --user-name $USER_NAME \
  --policy-name StockSentinelFullAccess \
  --policy-document file:///tmp/github-actions-policy.json

echo ""
echo "--- Access Keys (save these!) ---"
aws iam create-access-key --user-name $USER_NAME \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text

echo ""
echo "==========================================="
echo "  Add these as GitHub Secrets:"
echo "  https://github.com/Liming0987/stock-sentinel/settings/secrets/actions"
echo ""
echo "  AWS_ACCESS_KEY_ID     = <first value above>"
echo "  AWS_SECRET_ACCESS_KEY = <second value above>"
echo ""
echo "  Then go to Actions > 'Setup AWS Infrastructure' > Run workflow"
echo "==========================================="
