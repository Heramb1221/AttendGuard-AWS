#!/bin/bash
# EC2 user-data script: run ONCE automatically when the instance first
# boots (paste into the "User data" field when launching the instance).
# It prepares the instance to receive CodeDeploy deployments; it does NOT
# deploy the application itself — that's CodePipeline/CodeDeploy's job.
set -euo pipefail

exec > /var/log/user-data.log 2>&1
echo "Starting EC2 bootstrap at $(date)"

apt-get update -y
apt-get install -y ruby-full wget python3-pip python3-venv nginx ubuntu-advantage-tools

mkdir -p /var/log/attendguard
chown ubuntu:ubuntu /var/log/attendguard

# Install the CodeDeploy agent (ap-south-1 region bucket).
cd /home/ubuntu
wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install
chmod +x ./install
./install auto

systemctl enable codedeploy-agent
systemctl start codedeploy-agent

echo "EC2 bootstrap complete at $(date)"
