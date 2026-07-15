# AttendGuard — Detailed Deployment & Operations Guide

This guide assumes you are deploying AttendGuard for the very first time and
have never used the AWS services involved. Follow the sections in order.
Every step that requires manual action in the AWS Console or manual
decision-making is explicitly marked **MANUAL STEP**.

---

## 1. Prerequisites

- An AWS account (Free Tier eligible) with billing set up.
- AWS CLI v2 installed locally and configured: `aws configure` (needs an
  IAM user's access key, secret key, default region `ap-south-1`).
- Python 3.12 installed locally (for running the app and tests before deploy).
- Git and a GitHub account with this project pushed to a repository.
- **MANUAL STEP**: Decide on a strong RDS master password and a strong
  Flask `SECRET_KEY`. Do not reuse passwords from other systems.

---

## 2. Local Setup (Do This First — Verify Before Touching AWS)

```bash
git clone <your-repo-url>
cd attendguard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` and set at minimum:
```
SECRET_KEY=<a long random string>
```
Leave `DB_HOST`, `DB_NAME`, etc. blank for now — the app will fall back to
a local SQLite file so you can verify everything works before RDS exists.

```bash
flask init-db
flask seed-db
python -m pytest tests/ -v      # all tests should pass
python run.py
```

Visit `http://127.0.0.1:5000`, log in with `faculty@example.edu` /
`ChangeMe123!`, and confirm the dashboard loads. Stop the server
(`Ctrl+C`) once verified.

---

## 3. IAM Configuration

**MANUAL STEP**: In the IAM console (or via CLI), create three roles:

### 3a. EC2 Instance Role
1. IAM → Roles → Create role → Trusted entity: EC2.
2. Attach an inline policy using
   `deployment/iam_policies/ec2_instance_role_policy.json` as a starting
   point — **replace the placeholder bucket ARNs** with your actual bucket
   names from Section 4.
3. Name it `attendguard-ec2-role`.
4. Create an **instance profile** from this role (the console does this
   automatically when you create the role).

### 3b. CodeBuild Service Role
1. IAM → Roles → Create role → Trusted entity: CodeBuild.
2. Attach `deployment/iam_policies/codebuild_service_role_policy.json`
   (replace placeholder bucket names).
3. Name it `attendguard-codebuild-role`.

### 3c. CodePipeline Service Role
1. IAM → Roles → Create role → Trusted entity: CodePipeline.
2. Attach `deployment/iam_policies/codepipeline_service_role_policy.json`
   (replace placeholder bucket names).
3. Name it `attendguard-codepipeline-role`.

---

## 4. S3 Buckets

Run the relevant section of `scripts/aws_setup.sh` (read it first — do not
run the whole file blindly):

```bash
export RDS_MASTER_PASSWORD='<your-strong-password>'
bash scripts/aws_setup.sh
```

This creates two buckets:
- `attendguard-reports-...` — stores exported attendance CSVs.
- `attendguard-pipeline-artifacts-...` — used internally by CodePipeline.

**MANUAL STEP**: Note down both bucket names. You'll need the reports
bucket name for `.env` (`S3_REPORTS_BUCKET`) and both names for the IAM
policies in Section 3 and the CodePipeline/CodeBuild setup in Section 8.

---

## 5. RDS Setup

The same `scripts/aws_setup.sh` run above also starts provisioning the RDS
instance (`attendguard-db`, PostgreSQL, `db.t3.micro`, Free Tier eligible).

**MANUAL STEP**: RDS provisioning takes 5-10 minutes. Check status with:
```bash
aws rds describe-db-instances \
    --db-instance-identifier attendguard-db \
    --region ap-south-1 \
    --query 'DBInstances[0].DBInstanceStatus'
```
Wait until this returns `"available"`. Then retrieve the endpoint:
```bash
aws rds describe-db-instances \
    --db-instance-identifier attendguard-db \
    --region ap-south-1 \
    --query 'DBInstances[0].Endpoint.Address'
```

**MANUAL STEP**: In the RDS console, edit the security group attached to
this instance to allow inbound PostgreSQL (port 5432) traffic **only** from
your EC2 instance's security group (created in Section 6) — not from
`0.0.0.0/0`.

---

## 6. EC2 Setup

**MANUAL STEP**: Before launching, gather:
- The latest Ubuntu 22.04 LTS AMI ID for `ap-south-1` (find it in EC2 →
  Launch Instance → search "Ubuntu 22.04").
- An existing EC2 key pair name, or create a new one in the console.

### 6a. Security Group
Create a security group `attendguard-ec2-sg` allowing:
- Inbound TCP 22 (SSH) from your IP only.
- Inbound TCP 80 (HTTP) from `0.0.0.0/0`.
- Outbound: allow all (default).

### 6b. Launch the Instance
```bash
aws ec2 run-instances \
    --image-id <ubuntu-22.04-ami-id> \
    --instance-type t3.micro \
    --key-name <your-key-pair-name> \
    --security-group-ids <attendguard-ec2-sg-id> \
    --iam-instance-profile Name=attendguard-ec2-role \
    --user-data file://deployment/ec2_user_data.sh \
    --region ap-south-1 \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=attendguard-server}]'
```

The user-data script installs the CodeDeploy agent automatically. Wait a
couple of minutes, then verify it's running:
```bash
aws ec2 describe-instances --filters "Name=tag:Name,Values=attendguard-server" \
    --region ap-south-1 --query 'Reservations[0].Instances[0].State.Name'
```

**MANUAL STEP**: SSH into the instance and place your production `.env`
file at `/home/ubuntu/attendguard/.env` (this directory is created by the
first CodeDeploy deployment, so you may need to `mkdir -p` it manually
before the first deploy, or copy it in right after). Fill in the real RDS
endpoint, password, and S3 bucket name — never commit this file to git.

---

## 7. Load Balancer (Optional — Skipped for Free Tier)

A single `t3.micro` behind Nginx is sufficient for a capstone
demonstration and keeps costs at zero. If you want to add an Application
Load Balancer later for HTTPS/scaling, that is a Future Improvement noted
in README.md — it is intentionally out of scope here to stay within Free
Tier limits (ALB is not part of the always-free tier).

---

## 8. CI/CD Pipeline Setup

### 8a. Connect GitHub
1. Developer Tools → Settings → Connections → Create connection → GitHub.
2. **MANUAL STEP**: Authorize the connection in the popup and select your
   repository. Note the connection ARN.

### 8b. CodeBuild Project
1. CodeBuild → Create build project, name `attendguard-build`.
2. Source: your GitHub repo (via the connection above), branch `main`.
3. Environment: Ubuntu, Standard runtime, `aws/codebuild/standard:7.0`.
4. Service role: `attendguard-codebuild-role` (created in Section 3b).
5. Buildspec: use `deployment/buildspec.yml` from the repo (choose "Use a
   buildspec file").

### 8c. CodeDeploy Application
1. CodeDeploy → Create application, name `attendguard-app`, platform EC2/On-Premises.
2. Create a deployment group `attendguard-deployment-group`:
   - Service role: `attendguard-ec2-role` needs `codedeploy` trust — for
     simplicity, create a separate small role for CodeDeploy itself with
     the AWS-managed `AWSCodeDeployRole` policy attached, trusted by
     `codedeploy.amazonaws.com`.
   - Environment configuration: Amazon EC2 instances, tag `Name` =
     `attendguard-server`.
   - Deployment settings: `CodeDeployDefault.AllAtOnce` (single instance,
     no need for staged rollout).

### 8d. CodePipeline
1. CodePipeline → Create pipeline, name `attendguard-pipeline`.
2. Service role: `attendguard-codepipeline-role`.
3. Artifact store: the `attendguard-pipeline-artifacts-...` bucket from
   Section 4.
4. Source stage: GitHub (via CodeStar connection), your repo, branch `main`.
5. Build stage: CodeBuild project `attendguard-build`.
6. Deploy stage: CodeDeploy application `attendguard-app`, deployment group
   `attendguard-deployment-group`.
7. Save and let it run automatically on creation.

---

## 9. Running Locally (Recap)

```bash
source venv/bin/activate
python run.py
```

## 10. Running on AWS

Once the pipeline above completes successfully (check CodePipeline console
for a green checkmark on all three stages), the app is live at:
```
http://<your-ec2-public-ip>/
```
Every subsequent `git push origin main` triggers a fresh Source → Build →
Deploy cycle automatically — no manual server work required.

---

## 11. Testing

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

To manually test the fraud-detection flow end-to-end:
1. Log in as faculty, create a course session with your current GPS
   coordinates as the classroom center.
2. Log in as a student (a different browser/incognito window), open the
   session, and mark attendance — you should see "Present" with trust
   score 100.
3. Log in as a second student **on the same browser/device** (or the same
   browser profile) and mark attendance for the same session — this
   should trigger `DUPLICATE_DEVICE` and appear flagged in the faculty
   session-detail view.

## 12. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `RuntimeError: SECRET_KEY environment variable is not set` | `.env` missing/not loaded | Confirm `.env` exists and `SECRET_KEY` is set |
| 502 Bad Gateway from Nginx | gunicorn not running | `systemctl status attendguard` on EC2, check `/var/log/attendguard/error.log` |
| CodeDeploy `ValidateService` hook fails | App didn't start in time | SSH into EC2, check `systemctl status attendguard`, and `journalctl -u attendguard` |
| S3 export fails with `AccessDenied` | EC2 IAM role missing `s3:PutObject` on reports bucket | Re-check `ec2_instance_role_policy.json` has the correct bucket ARN |
| RDS connection times out from EC2 | Security group not allowing port 5432 from EC2's SG | Edit RDS security group inbound rules |
| `psycopg2` install fails locally | Missing `libpq-dev` (Linux) or Postgres client libs | `sudo apt-get install libpq-dev python3-dev` (Ubuntu) or use `psycopg2-binary` (already in requirements.txt) |

## 13. Cleanup (Avoid Ongoing Charges)

When you're done demonstrating the project:

```bash
# Delete the RDS instance (skip final snapshot for a capstone/demo project)
aws rds delete-db-instance --db-instance-identifier attendguard-db \
    --skip-final-snapshot --region ap-south-1

# Terminate the EC2 instance
aws ec2 terminate-instances --instance-ids <your-instance-id> --region ap-south-1

# Empty and delete both S3 buckets
aws s3 rm s3://<reports-bucket-name> --recursive
aws s3api delete-bucket --bucket <reports-bucket-name> --region ap-south-1
aws s3 rm s3://<pipeline-artifacts-bucket-name> --recursive
aws s3api delete-bucket --bucket <pipeline-artifacts-bucket-name> --region ap-south-1
```

**MANUAL STEP**: Also delete the CodePipeline, CodeBuild project,
CodeDeploy application/deployment group, and the three IAM roles via the
console, since these are not covered by the CLI commands above.
