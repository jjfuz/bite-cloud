# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura para experimento de desempeño y escalabilidad
# del proyecto BITE-CLOUD.
#
# Elementos a desplegar en AWS:
# 1. Grupos de seguridad:
#    - reportes-alb-public        (puerto 80)
#    - reportes-ssh-access        (puerto 22, estilo laboratorios)
#    - reportes-backend-clients   (grupo compartido backend)
#    - reportes-reportes-service  (puerto 8000 desde ALB)
#    - reportes-rabbitmq-service  (puertos 5672 y 15672)
#    - reportes-database-service  (puerto 5432)
#
# 2. Balanceador:
#    - reportes-alb-reportes
#
# 3. Instancias EC2:
#    - reportes-rabbitmq
#    - reportes-manejador-reportes-1
#    - reportes-manejador-reportes-2
#    - reportes-manejador-cloud
#
# 4. Base de datos:
#    - reportes-app-db (Amazon RDS PostgreSQL)
#
# Arquitectura desplegada:
# ALB -> 2 nodos Django de reportes/scheduler -> RabbitMQ -> 1 cloud consumer
#                                                         -> 1 PostgreSQL RDS
#
# Consideraciones:
# - El nodo reportes-1 corre migraciones, broker init, seed de costos y scheduler.
# - El nodo reportes-2 solo atiende tráfico HTTP detrás del ALB.
# - El manejador cloud corre el subscriber/consumer que usa Moto para ASR 1
#   y PostgreSQL interno para ASR 2.
# - No se usa key pair.
# - No se crean roles IAM, porque el Learner Lab bloquea iam:CreateRole.
# ******************************************************************

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ------------------------------------------------------------------
# Variables
# ------------------------------------------------------------------

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_prefix" {
  description = "Prefix used for naming AWS resources"
  type        = string
  default     = "reportes"
}

variable "vpc_id" {
  description = "Optional VPC where the infrastructure will be deployed"
  type        = string
  default     = null
  nullable    = true
}

variable "subnet_ids" {
  description = "Optional subnet IDs used by the ALB, EC2 instances, and RDS"
  type        = list(string)
  default     = null
  nullable    = true
}

variable "repo_url" {
  description = "Public Git repository URL for the Django project"
  type        = string
  default     = "https://github.com/jjfuz/bite-cloud.git"
}

variable "repo_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "main"
}

variable "app_instance_type" {
  description = "Instance type for Django report nodes"
  type        = string
  default     = "t3.small"
}

variable "broker_instance_type" {
  description = "Instance type for the RabbitMQ broker"
  type        = string
  default     = "t2.nano"
}

variable "cloud_instance_type" {
  description = "Instance type for the cloud consumer/analyzer"
  type        = string
  default     = "t3.small"
}

variable "database_instance_class" {
  description = "Instance class for PostgreSQL RDS"
  type        = string
  default     = "db.t3.micro"
}

variable "database_allocated_storage" {
  description = "Allocated storage in GB for PostgreSQL RDS"
  type        = number
  default     = 20
}

variable "database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "bitedb"
}

variable "database_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "biteuser"
}

variable "database_password" {
  description = "PostgreSQL master password"
  type        = string
  default     = "password"
  sensitive   = true
}

variable "django_secret_key" {
  description = "Django secret key used in production"
  type        = string
  default     = "django-insecure-bite-cloud-2026"
  sensitive   = true
}

variable "rabbitmq_username" {
  description = "RabbitMQ application username"
  type        = string
  default     = "appuser"
}

variable "rabbitmq_password" {
  description = "RabbitMQ application password"
  type        = string
  default     = "AppPassword2026!"
  sensitive   = true
}

variable "scheduler_interval_seconds" {
  description = "Interval in seconds for the scheduler timer"
  type        = number
  default     = 30
}

# ------------------------------------------------------------------
# Provider
# ------------------------------------------------------------------

provider "aws" {
  region = var.region
}

# ------------------------------------------------------------------
# Locals
# ------------------------------------------------------------------

locals {
  project_name      = "${var.project_prefix}-arquisoft"
  active_vpc_id     = coalesce(var.vpc_id, data.aws_vpc.default.id)
  active_subnet_ids = var.subnet_ids != null ? var.subnet_ids : data.aws_subnets.default.ids

  app_dir  = "/opt/bite-cloud"
  app_user = "ubuntu"

  common_tags = {
    Project   = local.project_name
    ManagedBy = "Terraform"
  }
}

# ------------------------------------------------------------------
# Data sources
# ------------------------------------------------------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ------------------------------------------------------------------
# Security Groups
# ------------------------------------------------------------------

resource "aws_security_group" "alb_public" {
  name        = "${var.project_prefix}-alb-public"
  description = "Allow public HTTP traffic to the ALB"
  vpc_id      = local.active_vpc_id

  ingress {
    description = "HTTP from the internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-alb-public"
  })
}

resource "aws_security_group" "ssh_access" {
  name        = "${var.project_prefix}-ssh-access"
  description = "Allow SSH access to EC2 instances"
  vpc_id      = local.active_vpc_id

  ingress {
    description = "SSH from the internet"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-ssh-access"
  })
}

resource "aws_security_group" "backend_clients" {
  name        = "${var.project_prefix}-backend-clients"
  description = "Shared security group for backend nodes consuming internal services"
  vpc_id      = local.active_vpc_id

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-backend-clients"
  })
}

resource "aws_security_group" "reportes_service" {
  name        = "${var.project_prefix}-reportes-service"
  description = "Allow ALB traffic to Django report nodes"
  vpc_id      = local.active_vpc_id

  ingress {
    description     = "HTTP from ALB to report nodes"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_public.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-reportes-service"
  })
}

resource "aws_security_group" "rabbitmq_service" {
  name        = "${var.project_prefix}-rabbitmq-service"
  description = "Allow AMQP traffic to RabbitMQ"
  vpc_id      = local.active_vpc_id

  ingress {
    description     = "AMQP from backend clients"
    from_port       = 5672
    to_port         = 5672
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_clients.id]
  }

  ingress {
    description = "RabbitMQ management dashboard"
    from_port   = 15672
    to_port     = 15672
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-rabbitmq-service"
  })
}

resource "aws_security_group" "database_service" {
  name        = "${var.project_prefix}-database-service"
  description = "Allow PostgreSQL traffic from backend clients"
  vpc_id      = local.active_vpc_id

  ingress {
    description     = "PostgreSQL from backend clients"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_clients.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-database-service"
  })
}

# ------------------------------------------------------------------
# Load Balancer
# ------------------------------------------------------------------

resource "aws_lb" "alb_reportes" {
  name               = "${var.project_prefix}-alb-reportes"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_public.id]
  subnets            = local.active_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-alb-reportes"
  })
}

resource "aws_lb_target_group" "tg_backend_reportes" {
  name     = "${var.project_prefix}-tg-reportes"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = local.active_vpc_id

  load_balancing_algorithm_type = "least_outstanding_requests"

  health_check {
    enabled             = true
    path                = "/health/"
    protocol            = "HTTP"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    timeout             = 5
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-tg-reportes"
  })
}

resource "aws_lb_listener" "http_frontend" {
  load_balancer_arn = aws_lb.alb_reportes.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg_backend_reportes.arn
  }
}

# ------------------------------------------------------------------
# RDS PostgreSQL
# ------------------------------------------------------------------

resource "aws_db_subnet_group" "databases" {
  name       = "${var.project_prefix}-db-subnets"
  subnet_ids = local.active_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db-subnets"
  })
}

resource "aws_db_instance" "app_db" {
  identifier             = "${var.project_prefix}-app-db"
  engine                 = "postgres"
  instance_class         = var.database_instance_class
  allocated_storage      = var.database_allocated_storage
  db_name                = var.database_name
  username               = var.database_username
  password               = var.database_password
  db_subnet_group_name   = aws_db_subnet_group.databases.name
  vpc_security_group_ids = [aws_security_group.database_service.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false
  storage_type           = "gp3"

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-app-db"
    Role = "database"
  })
}

# ------------------------------------------------------------------
# EC2 - RabbitMQ broker
# ------------------------------------------------------------------

resource "aws_instance" "rabbitmq" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.broker_instance_type
  subnet_id                   = local.active_subnet_ids[0]
  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.rabbitmq_service.id,
    aws_security_group.ssh_access.id
  ]

  user_data = <<-EOT
              #!/bin/bash
              set -euxo pipefail
              export DEBIAN_FRONTEND=noninteractive

              apt-get update -y
              apt-get install -y rabbitmq-server

              systemctl enable rabbitmq-server
              systemctl restart rabbitmq-server

              rabbitmq-plugins enable rabbitmq_management

              rabbitmqctl add_user "${var.rabbitmq_username}" "${var.rabbitmq_password}" || true
              rabbitmqctl set_user_tags "${var.rabbitmq_username}" administrator
              rabbitmqctl set_permissions -p / "${var.rabbitmq_username}" ".*" ".*" ".*"
              EOT

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-rabbitmq"
    Role = "broker"
  })
}

# ------------------------------------------------------------------
# EC2 - Django report nodes
# ------------------------------------------------------------------

resource "aws_instance" "manejador_reportes" {
  count = 2

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.app_instance_type
  subnet_id                   = local.active_subnet_ids[count.index % length(local.active_subnet_ids)]
  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.reportes_service.id,
    aws_security_group.backend_clients.id,
    aws_security_group.ssh_access.id
  ]

  user_data = <<-EOT
              #!/bin/bash
              set -euxo pipefail
              export DEBIAN_FRONTEND=noninteractive

              retry() {
                local n=0
                local max=30
                local delay=15
                until "$@"; do
                  n=$((n+1))
                  if [ $n -ge $max ]; then
                    echo "Command failed after $${max} attempts: $*"
                    return 1
                  fi
                  sleep $delay
                done
              }

              apt-get update -y
              apt-get install -y python3-pip python3-venv git build-essential libpq-dev python3-dev curl

              mkdir -p /opt

              if [ ! -d "${local.app_dir}" ]; then
                git clone --branch ${var.repo_branch} ${var.repo_url} ${local.app_dir}
              else
                cd ${local.app_dir}
                git fetch origin
                git checkout ${var.repo_branch}
                git pull origin ${var.repo_branch}
              fi

              chown -R ubuntu:ubuntu ${local.app_dir}

              sudo -u ubuntu bash -lc "
              cd ${local.app_dir}
              python3 -m venv .venv
              ./.venv/bin/pip install --upgrade pip
              ./.venv/bin/pip install -r requirements.txt
              "

              cat > ${local.app_dir}/.env <<EOF
              DEBUG=False
              SECRET_KEY=${var.django_secret_key}
              ALLOWED_HOSTS=*
              DB_NAME=${var.database_name}
              DB_USER=${var.database_username}
              DB_PASSWORD=${var.database_password}
              DB_HOST=${aws_db_instance.app_db.address}
              DB_PORT=5432

              RABBITMQ_HOST=${aws_instance.rabbitmq.private_ip}
              RABBITMQ_PORT=5672
              RABBITMQ_VHOST=/
              RABBITMQ_USERNAME=${var.rabbitmq_username}
              RABBITMQ_PASSWORD=${var.rabbitmq_password}
              RABBITMQ_EXCHANGE=platform.jobs
              RABBITMQ_EXCHANGE_TYPE=topic
              RABBITMQ_DLX=platform.jobs.dlx
              RABBITMQ_HEARTBEAT=60
              RABBITMQ_BLOCKED_CONNECTION_TIMEOUT=30
              RABBITMQ_CONNECTION_ATTEMPTS=3
              RABBITMQ_RETRY_DELAY=3
              RABBITMQ_SOCKET_TIMEOUT=5

              AWS_USE_IAM_ROLE=False
              AWS_REGION=${var.region}
              AWS_CE_REGION=${var.region}
              AWS_DEFAULT_CURRENCY=USD
              AWS_EBS_RATE_GP3=0.08
              AWS_EBS_RATE_GP2=0.10
              AWS_EBS_RATE_IO1=0.125
              AWS_EBS_RATE_IO2=0.125
              AWS_EBS_RATE_ST1=0.045
              AWS_EBS_RATE_SC1=0.025
              AWS_EBS_RATE_STANDARD=0.05

              ORPHAN_EBS_SOURCE=moto
              FINANCIAL_REPORT_SOURCE=internal_db

              USE_FAKE_BROKER=False
              USE_FAKE_CLOUD_DATA=False
              EOF

              chown ubuntu:ubuntu ${local.app_dir}/.env

              cat > /etc/systemd/system/bite-gunicorn.service <<EOF
              [Unit]
              Description=BITE Django Gunicorn
              After=network.target

              [Service]
              User=ubuntu
              Group=ubuntu
              WorkingDirectory=${local.app_dir}
              EnvironmentFile=${local.app_dir}/.env
              Environment=PYTHONUNBUFFERED=1
              ExecStart=${local.app_dir}/.venv/bin/gunicorn monitoring.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile -
              Restart=always
              RestartSec=5

              [Install]
              WantedBy=multi-user.target
              EOF

              if [ "${count.index}" = "0" ]; then
                cat > /etc/systemd/system/bite-scheduler.service <<EOF
              [Unit]
              Description=BITE Scheduler
              After=network.target

              [Service]
              Type=oneshot
              User=ubuntu
              Group=ubuntu
              WorkingDirectory=${local.app_dir}
              EnvironmentFile=${local.app_dir}/.env
              Environment=PYTHONUNBUFFERED=1
              ExecStart=${local.app_dir}/.venv/bin/python manage.py run_scheduler
              EOF

                cat > /etc/systemd/system/bite-scheduler.timer <<EOF
              [Unit]
              Description=Run BITE Scheduler every ${var.scheduler_interval_seconds} seconds

              [Timer]
              OnBootSec=45sec
              OnUnitActiveSec=${var.scheduler_interval_seconds}s
              AccuracySec=1s
              Unit=bite-scheduler.service

              [Install]
              WantedBy=timers.target
              EOF
              fi

              systemctl daemon-reload

              if [ "${count.index}" = "0" ]; then
                retry sudo -u ubuntu bash -lc "cd ${local.app_dir} && ./.venv/bin/python manage.py migrate"
                retry sudo -u ubuntu bash -lc "cd ${local.app_dir} && ./.venv/bin/python manage.py broker_healthcheck"
                retry sudo -u ubuntu bash -lc "cd ${local.app_dir} && ./.venv/bin/python manage.py init_broker_topology"
                retry sudo -u ubuntu bash -lc "cd ${local.app_dir} && ./.venv/bin/python manage.py seed_raw_cost_data --clear --tenant-id tenant-demo --companies 50 --areas-per-company 3 --projects-per-company 5 --year 2026"
              fi

              retry sudo -u ubuntu bash -lc "cd ${local.app_dir} && ./.venv/bin/python manage.py collectstatic --noinput"

              systemctl enable bite-gunicorn
              systemctl restart bite-gunicorn

              if [ "${count.index}" = "0" ]; then
                systemctl enable bite-scheduler.timer
                systemctl restart bite-scheduler.timer
              fi
              EOT

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  depends_on = [
    aws_db_instance.app_db,
    aws_instance.rabbitmq
  ]

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-manejador-reportes-${count.index + 1}"
    Role = "manejador-reportes"
  })
}

resource "aws_lb_target_group_attachment" "attach_backend" {
  count            = 2
  target_group_arn = aws_lb_target_group.tg_backend_reportes.arn
  target_id        = aws_instance.manejador_reportes[count.index].id
  port             = 8000
}

# ------------------------------------------------------------------
# EC2 - Cloud consumer / subscriber / analyzer
# ------------------------------------------------------------------

resource "aws_instance" "manejador_cloud" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.cloud_instance_type
  subnet_id                   = local.active_subnet_ids[0]
  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.backend_clients.id,
    aws_security_group.ssh_access.id
  ]

  user_data = <<-EOT
              #!/bin/bash
              set -euxo pipefail
              export DEBIAN_FRONTEND=noninteractive

              apt-get update -y
              apt-get install -y python3-pip python3-venv git build-essential libpq-dev python3-dev curl

              mkdir -p /opt

              if [ ! -d "${local.app_dir}" ]; then
                git clone --branch ${var.repo_branch} ${var.repo_url} ${local.app_dir}
              else
                cd ${local.app_dir}
                git fetch origin
                git checkout ${var.repo_branch}
                git pull origin ${var.repo_branch}
              fi

              chown -R ubuntu:ubuntu ${local.app_dir}

              sudo -u ubuntu bash -lc "
              cd ${local.app_dir}
              python3 -m venv .venv
              ./.venv/bin/pip install --upgrade pip
              ./.venv/bin/pip install -r requirements.txt
              "

              cat > ${local.app_dir}/.env <<EOF
              DEBUG=False
              SECRET_KEY=${var.django_secret_key}
              ALLOWED_HOSTS=*
              DB_NAME=${var.database_name}
              DB_USER=${var.database_username}
              DB_PASSWORD=${var.database_password}
              DB_HOST=${aws_db_instance.app_db.address}
              DB_PORT=5432

              RABBITMQ_HOST=${aws_instance.rabbitmq.private_ip}
              RABBITMQ_PORT=5672
              RABBITMQ_VHOST=/
              RABBITMQ_USERNAME=${var.rabbitmq_username}
              RABBITMQ_PASSWORD=${var.rabbitmq_password}
              RABBITMQ_EXCHANGE=platform.jobs
              RABBITMQ_EXCHANGE_TYPE=topic
              RABBITMQ_DLX=platform.jobs.dlx
              RABBITMQ_HEARTBEAT=60
              RABBITMQ_BLOCKED_CONNECTION_TIMEOUT=30
              RABBITMQ_CONNECTION_ATTEMPTS=3
              RABBITMQ_RETRY_DELAY=3
              RABBITMQ_SOCKET_TIMEOUT=5

              AWS_USE_IAM_ROLE=False
              AWS_REGION=${var.region}
              AWS_CE_REGION=${var.region}
              AWS_DEFAULT_CURRENCY=USD
              AWS_EBS_RATE_GP3=0.08
              AWS_EBS_RATE_GP2=0.10
              AWS_EBS_RATE_IO1=0.125
              AWS_EBS_RATE_IO2=0.125
              AWS_EBS_RATE_ST1=0.045
              AWS_EBS_RATE_SC1=0.025
              AWS_EBS_RATE_STANDARD=0.05

              ORPHAN_EBS_SOURCE=moto
              FINANCIAL_REPORT_SOURCE=internal_db

              USE_FAKE_BROKER=False
              USE_FAKE_CLOUD_DATA=False
              EOF

              chown ubuntu:ubuntu ${local.app_dir}/.env

              cat > /etc/systemd/system/bite-cloud-consumer.service <<EOF
              [Unit]
              Description=BITE Cloud Consumer
              After=network.target

              [Service]
              User=ubuntu
              Group=ubuntu
              WorkingDirectory=${local.app_dir}
              EnvironmentFile=${local.app_dir}/.env
              Environment=PYTHONUNBUFFERED=1
              ExecStart=${local.app_dir}/.venv/bin/python manage.py run_cloud_consumer
              Restart=always
              RestartSec=10

              [Install]
              WantedBy=multi-user.target
              EOF

              systemctl daemon-reload
              systemctl enable bite-cloud-consumer
              systemctl restart bite-cloud-consumer
              EOT

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  depends_on = [
    aws_db_instance.app_db,
    aws_instance.rabbitmq
  ]

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-manejador-cloud"
    Role = "manejador-cloud"
  })
}

# ------------------------------------------------------------------
# Outputs
# ------------------------------------------------------------------

output "alb_reportes_dns" {
  description = "DNS name of the public load balancer"
  value       = aws_lb.alb_reportes.dns_name
}

output "manejadores_reportes_public_ips" {
  description = "Public IPs of the Django report nodes"
  value       = aws_instance.manejador_reportes[*].public_ip
}

output "rabbitmq_public_ip" {
  description = "Public IP of the RabbitMQ server"
  value       = aws_instance.rabbitmq.public_ip
}

output "manejador_cloud_public_ip" {
  description = "Public IP of the cloud consumer/analyzer"
  value       = aws_instance.manejador_cloud.public_ip
}

output "rabbitmq_management_url" {
  description = "RabbitMQ management dashboard URL"
  value       = "http://${aws_instance.rabbitmq.public_ip}:15672"
}

output "database_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.app_db.address
}