#!/bin/bash
# AWS Infrastructure Setup for Stock Sentinel
# Run this script once to create the required AWS resources.
# Prerequisites: AWS CLI configured with admin access
#
# Usage: bash deploy/setup-aws.sh

set -e

AWS_REGION="us-east-1"
ACCOUNT_ID="178801185941"
KEY_NAME="stock-sentinel-key"
INSTANCE_TYPE="t3.small"
SECURITY_GROUP_NAME="stock-sentinel-sg"

echo "=== Stock Sentinel AWS Setup ==="
echo "Account: $ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo ""

# 1. Create ECR repositories
echo "--- Creating ECR repositories ---"
aws ecr create-repository \
  --repository-name stock-sentinel-backend \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null || echo "Backend repo already exists"

aws ecr create-repository \
  --repository-name stock-sentinel-frontend \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null || echo "Frontend repo already exists"

echo "ECR repos created."

# 2. Create SSH key pair
echo ""
echo "--- Creating SSH key pair ---"
if [ ! -f ~/.ssh/$KEY_NAME.pem ]; then
  aws ec2 create-key-pair \
    --key-name $KEY_NAME \
    --region $AWS_REGION \
    --query 'KeyMaterial' \
    --output text > ~/.ssh/$KEY_NAME.pem
  chmod 400 ~/.ssh/$KEY_NAME.pem
  echo "Key pair created: ~/.ssh/$KEY_NAME.pem"
else
  echo "Key pair already exists locally."
fi

# 3. Create security group
echo ""
echo "--- Creating security group ---"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)

SG_ID=$(aws ec2 create-security-group \
  --group-name $SECURITY_GROUP_NAME \
  --description "Stock Sentinel - HTTP, HTTPS, SSH" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION \
  --query 'GroupId' \
  --output text 2>/dev/null) || SG_ID=$(aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --query "SecurityGroups[0].GroupId" --output text --region $AWS_REGION)

# Allow SSH
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0 \
  --region $AWS_REGION 2>/dev/null || true

# Allow HTTP
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 80 --cidr 0.0.0.0/0 \
  --region $AWS_REGION 2>/dev/null || true

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 443 --cidr 0.0.0.0/0 \
  --region $AWS_REGION 2>/dev/null || true

echo "Security group: $SG_ID"

# 4. Create IAM role for EC2 (to pull from ECR)
echo ""
echo "--- Creating IAM role for EC2 ---"
cat > /tmp/ec2-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name StockSentinelEC2Role \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json \
  2>/dev/null || echo "Role already exists"

aws iam attach-role-policy \
  --role-name StockSentinelEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly \
  2>/dev/null || true

aws iam create-instance-profile \
  --instance-profile-name StockSentinelEC2Profile \
  2>/dev/null || echo "Instance profile already exists"

aws iam add-role-to-instance-profile \
  --instance-profile-name StockSentinelEC2Profile \
  --role-name StockSentinelEC2Role \
  2>/dev/null || true

echo "IAM role configured."

# 5. Launch EC2 instance
echo ""
echo "--- Launching EC2 instance ---"

# Amazon Linux 2023 AMI (us-east-1)
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text \
  --region $AWS_REGION)

USER_DATA=$(cat << 'EOF'
#!/bin/bash
yum update -y
yum install -y docker git
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Install AWS CLI v2 (already on AL2023)
# Clone project structure
mkdir -p /home/ec2-user/stock-sentinel/nginx
chown -R ec2-user:ec2-user /home/ec2-user/stock-sentinel
EOF
)

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --iam-instance-profile Name=StockSentinelEC2Profile \
  --user-data "$USER_DATA" \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":30,"VolumeType":"gp3"}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=stock-sentinel}]" \
  --region $AWS_REGION \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance launched: $INSTANCE_ID"
echo "Waiting for instance to be running..."

aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --region $AWS_REGION)

echo ""
echo "========================================="
echo "  SETUP COMPLETE"
echo "========================================="
echo ""
echo "EC2 Instance: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "SSH: ssh -i ~/.ssh/$KEY_NAME.pem ec2-user@$PUBLIC_IP"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Add these GitHub Secrets (Settings > Secrets > Actions):"
echo "   AWS_ACCESS_KEY_ID     = <your IAM user access key>"
echo "   AWS_SECRET_ACCESS_KEY = <your IAM user secret key>"
echo "   EC2_HOST              = $PUBLIC_IP"
echo "   EC2_SSH_KEY           = <contents of ~/.ssh/$KEY_NAME.pem>"
echo ""
echo "2. SSH into the instance and copy the production files:"
echo "   ssh -i ~/.ssh/$KEY_NAME.pem ec2-user@$PUBLIC_IP"
echo "   # Then run: deploy/setup-ec2.sh"
echo ""
echo "3. Push to main branch to trigger deployment!"
echo "========================================="
