#!/bin/bash
# Set up GitHub OIDC → IAM Role for GitHub Actions CI/CD.
# No long-lived access keys. GitHub assumes a role via OIDC federation.
#
# THIS IS THE ONLY SCRIPT YOU NEED TO RUN LOCALLY.
# Everything else is done via GitHub Actions.
#
# Prerequisites: AWS CLI configured with admin access.
# Usage: bash deploy/setup-iam-role.sh

set -e

ACCOUNT_ID="178801185941"
GITHUB_ORG="Liming0987"
GITHUB_REPO="stock-sentinel"
ROLE_NAME="StockSentinelGitHubActions"
EC2_ROLE_NAME="StockSentinelEC2Role"

echo "=== Setting up GitHub OIDC → IAM Role ==="

# 1. Create the GitHub OIDC identity provider (idempotent)
echo "--- Creating OIDC provider ---"
if ! aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com 2>/dev/null; then

  THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list $THUMBPRINT
  echo "OIDC provider created"
else
  echo "OIDC provider already exists"
fi

# 2. Create the IAM role for GitHub Actions
echo ""
echo "--- Creating GitHub Actions role ---"
cat > /tmp/gh-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document file:///tmp/gh-trust-policy.json \
  2>/dev/null || echo "Role already exists"

# 3. Attach permissions policy
echo ""
echo "--- Attaching permissions ---"
cat > /tmp/gh-permissions.json << EOF
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
        "ec2:DescribeSubnets",
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
        "iam:GetRole",
        "iam:AttachRolePolicy",
        "iam:CreateInstanceProfile",
        "iam:GetInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::${ACCOUNT_ID}:role/${EC2_ROLE_NAME}",
        "arn:aws:iam::${ACCOUNT_ID}:instance-profile/StockSentinelEC2Profile"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name StockSentinelDeploy \
  --policy-document file:///tmp/gh-permissions.json

echo ""
echo "==========================================="
echo "  SETUP COMPLETE"
echo "==========================================="
echo ""
echo "  Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "  Add this as a GitHub Secret:"
echo "  https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "  AWS_ROLE_ARN = arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "  You can delete AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY secrets."
echo "  No access keys needed — GitHub authenticates via OIDC."
echo "==========================================="
