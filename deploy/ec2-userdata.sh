#!/bin/bash
# EC2 bootstrap script — runs on first launch via user-data
yum update -y
yum install -y docker git

systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Install Docker Compose v2
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Symlink for standalone usage
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Create app directory
mkdir -p /home/ec2-user/stock-sentinel/nginx
chown -R ec2-user:ec2-user /home/ec2-user/stock-sentinel
