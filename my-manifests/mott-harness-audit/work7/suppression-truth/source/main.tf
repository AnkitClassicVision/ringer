terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = ["533267039664"]
}

locals {
  name      = "mott-booking-gateway"
  image_uri = "${data.aws_ecr_repository.eyecloud_fargate_runner.repository_url}:${var.image_tag}"

  mott_secret_arns = [
    data.aws_secretsmanager_secret.eyecloud_login.arn,
    data.aws_secretsmanager_secret.audit_db_master_key.arn,
    data.aws_secretsmanager_secret.tailscale_authkey.arn,
    # REQUIRED: the task definition injects this as ECP_SHIM_BEARER via valueFrom, so the
    # ECS EXECUTION role must be able to read it. Omitting it fails the task at pull time
    # with ResourceInitializationError / AccessDeniedException on GetSecretValue, before the
    # container ever starts. The former read/write bearer entries pointed at secrets that do
    # not exist, so removing them left this real secret ungranted and took the service down.
    data.aws_secretsmanager_secret.bland_bearer.arn,
  ]

  gateway_environment = [
    { name = "CONDUCTOR_AGENT_ID", value = "bland" },
    { name = "CONDUCTOR_AUDIT_TABLE", value = aws_dynamodb_table.conductor_audit.name },
    { name = "CONDUCTOR_BLAND_BEARER_SECRET_ID", value = data.aws_secretsmanager_secret.bland_bearer.name },
    { name = "CONDUCTOR_CONTROL_TABLE", value = aws_dynamodb_table.conductor_control.name },
    { name = "CONDUCTOR_ENABLED", value = "1" },
    { name = "CONDUCTOR_FORWARD_TIMEOUT", value = "28s" },
    { name = "CONDUCTOR_GATEWAY_PORT", value = "8433" },
    { name = "CONDUCTOR_SECRET_ID", value = var.conductor_core_secret_name },
    { name = "CONDUCTOR_SIGNER_PORT", value = "8432" },
    { name = "CVC_HOURS_JSON", value = var.mott_hours_json },
    { name = "ECP_ALLOW_SELF_SIGNED_TLS", value = "1" },
    { name = "ECP_APPT_TYPE_MAP", value = var.mott_appt_type_map },
    { name = "ECP_CLI", value = "/usr/local/bin/eyecloud-pro-pp-cli" },
    { name = "ECP_DEFAULT_APPT_TYPE", value = var.mott_default_appt_type },
    { name = "ECP_GATEWAY_HOSTNAME", value = "mott-booking-gateway" },
    { name = "ECP_LOGIN_URL", value = "https://web.opticalpos.com/pos/login/me" },
    { name = "ECP_REQUIRE_EGRESS_PROXY", value = "1" },
    { name = "ECP_SESSION_REFRESH_S", value = "1800" },
    { name = "ECP_SESSION_WARM_ENABLED", value = "1" },
    { name = "ECP_SHIM_HOST", value = "127.0.0.1" },
    { name = "ECP_SHIM_PORT", value = "8431" },
    { name = "ECP_SMS_SUPPRESSION_TABLE", value = aws_dynamodb_table.sms_suppression.name },
    # Owner decision 2026-07-26: expose new-patient registration through the shim/CLI
    # path. The CLI default-denies patient creation unless this is explicitly set, and
    # it is the LAST guard on that route, since going shim-side skips the conductor's
    # audit record, verb grant, kill switch and post-write verification. The caller must
    # also send confirm:true per request or the CLI runs dry and creates nothing.
    # Set this to "0" to switch new-patient creation off without a code change.
    { name = "EYECLOUD_PRO_APPT_ALLOW_PATIENT_CREATE", value = "1" },
    { name = "ECP_SHIM_TEST_LAST_PREFIX", value = "PA" },
    # Mott runs live patients, not a test cohort. With this on, bland_gateway.py
    # rejects every patient id outside ECP_SHIM_TEST_PATIENTS (which is unset, so it
    # defaults to a single CVC test id) and filters patient-search down to last names
    # starting with ECP_SHIM_TEST_LAST_PREFIX. Both make ordinary Mott lookups fail.
    { name = "ECP_SHIM_TEST_MODE", value = "0" },
    { name = "ECP_STORE_ID", value = var.mott_store_id },
    # Without this the container falls back to the "cvc" default and Mott traffic
    # carries the other practice's tenant identity.
    { name = "ECP_TENANT_ID", value = "mott" },
    { name = "TS_EXIT_NODE", value = var.ts_exit_node },
    { name = "TS_HOSTNAME", value = "mott-booking-gateway" },
  ]

  gateway_secrets = [
    { name = "ECP_LOGIN_PASSWORD", valueFrom = "${data.aws_secretsmanager_secret.eyecloud_login.arn}:${var.login_secret_password_key}::" },
    { name = "ECP_LOGIN_USERNAME", valueFrom = "${data.aws_secretsmanager_secret.eyecloud_login.arn}:${var.login_secret_username_key}::" },
    { name = "ECP_SHIM_BEARER", valueFrom = data.aws_secretsmanager_secret.bland_bearer.arn },
    { name = "EYECLOUD_PRO_DB_MASTER_KEY", valueFrom = data.aws_secretsmanager_secret.audit_db_master_key.arn },
    { name = "EYECLOUD_PRO_MOTT_DB_MASTER_KEY", valueFrom = data.aws_secretsmanager_secret.audit_db_master_key.arn },
    { name = "EYECLOUD_PRO_PASSWORD", valueFrom = "${data.aws_secretsmanager_secret.eyecloud_login.arn}:${var.login_secret_password_key}::" },
    { name = "EYECLOUD_PRO_USERNAME", valueFrom = "${data.aws_secretsmanager_secret.eyecloud_login.arn}:${var.login_secret_username_key}::" },
    { name = "TS_AUTHKEY", valueFrom = data.aws_secretsmanager_secret.tailscale_authkey.arn },
  ]
}

resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/ecs/${local.name}"
  retention_in_days = 30
}

resource "aws_dynamodb_table" "conductor_audit" {
  name         = "${local.name}-conductor-audit"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled                 = true
    recovery_period_in_days = 35
  }
}

# STOP compliance. Until this existed, a patient replying STOP was acknowledged and then
# forgotten, so the next campaign would text them again. The gateway route fails closed
# with 503 when ECP_SMS_SUPPRESSION_TABLE is unset, because a suppression that was not
# recorded is worse than a visible error: it reads as opted-out when the patient is not.
# Point-in-time recovery is on: losing this table means re-contacting people who asked
# not to be contacted.
resource "aws_dynamodb_table" "sms_suppression" {
  name         = "${local.name}-sms-suppression"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  point_in_time_recovery {
    enabled                 = true
    recovery_period_in_days = 35
  }
}

resource "aws_dynamodb_table" "conductor_control" {
  name         = "${local.name}-conductor-control"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }
}

data "aws_iam_policy_document" "execution_secrets" {
  statement {
    sid       = "InjectMottScopedSecrets"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = local.mott_secret_arns
  }

  statement {
    sid       = "DecryptPhiKeyForMottSecretInjection"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [data.aws_kms_alias.phi.target_key_arn]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "mott-booking-gateway-secrets"
  role   = data.aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

data "aws_iam_policy_document" "task_conductor" {
  statement {
    sid    = "MottConductorTables"
    effect = "Allow"
    actions = [
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:PutItem",
      "dynamodb:GetItem",
    ]
    resources = [
      aws_dynamodb_table.conductor_control.arn,
      aws_dynamodb_table.conductor_audit.arn,
      aws_dynamodb_table.sms_suppression.arn,
    ]
  }

  statement {
    sid     = "MottConductorSecrets"
    effect  = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      data.aws_secretsmanager_secret.conductor_core.arn,
      # REQUIRED: the conductor resolves its Bland bearer AT RUNTIME from the secret named by
      # CONDUCTOR_BLAND_BEARER_SECRET_ID, so the TASK role (not just the execution role) needs
      # read access. Without it the signer never reports healthy and the entrypoint aborts with
      # "FATAL: conductor gateway/signer did not become healthy". The removed write-bearer entry
      # pointed at a secret that does not exist, so dropping it left this real secret ungranted.
      data.aws_secretsmanager_secret.bland_bearer.arn,
    ]
  }

  statement {
    sid       = "MottConductorKms"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [data.aws_kms_alias.phi.target_key_arn]
  }
}

resource "aws_iam_role_policy" "task_conductor" {
  name   = "mott-booking-gateway-conductor"
  role   = data.aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_conductor.json
}

resource "aws_ecs_task_definition" "gateway" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "1024"
  execution_role_arn       = data.aws_iam_role.execution.arn
  task_role_arn            = data.aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      environment = local.gateway_environment
      essential   = true
      healthCheck = {
        command = [
          "CMD-SHELL",
          "python3 -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8431/health', timeout=2)\"",
        ]
        interval    = 30
        retries     = 3
        startPeriod = 90
        timeout     = 5
      }
      image = local.image_uri
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
          awslogs-group         = aws_cloudwatch_log_group.gateway.name
        }
      }
      mountPoints = []
      name        = local.name
      portMappings = [
        {
          containerPort = 443
          hostPort      = 443
          protocol      = "tcp"
        }
      ]
      secrets        = local.gateway_secrets
      systemControls = []
      volumesFrom    = []
    }
  ])
}

resource "aws_lb_target_group" "gateway" {
  name        = "${local.name}-tg"
  target_type = "ip"
  vpc_id      = data.aws_vpc.selected.id
  port        = 443
  protocol    = "HTTPS"

  health_check {
    enabled             = true
    protocol            = "HTTPS"
    path                = "/health"
    port                = "traffic-port"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }
}

resource "aws_acm_certificate" "mott" {
  domain_name       = "mott-booking-gw.mail.mybcat.com"
  validation_method = "DNS"
}

resource "aws_route53_record" "mott_certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.mott.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  }

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "mott" {
  certificate_arn = aws_acm_certificate.mott.arn
  validation_record_fqdns = [
    for record in aws_route53_record.mott_certificate_validation : record.fqdn
  ]
}

resource "aws_lb_listener_certificate" "mott" {
  listener_arn    = data.aws_lb_listener.https.arn
  certificate_arn = aws_acm_certificate_validation.mott.certificate_arn
}

resource "aws_lb_listener_rule" "mott" {
  listener_arn = data.aws_lb_listener.https.arn
  priority     = var.listener_rule_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gateway.arn
  }

  condition {
    host_header {
      values = ["mott-booking-gw.mail.mybcat.com"]
    }
  }
}

resource "aws_route53_record" "mott" {
  zone_id = var.route53_zone_id
  name    = "mott-booking-gw.mail.mybcat.com"
  type    = "A"

  alias {
    name                   = data.aws_lb.shared.dns_name
    zone_id                = data.aws_lb.shared.zone_id
    evaluate_target_health = true
  }
}

resource "aws_ecs_service" "gateway" {
  name            = local.name
  cluster         = data.aws_ecs_cluster.stack2.arn
  task_definition = aws_ecs_task_definition.gateway.arn
  desired_count   = 1
  # EyeCloud permits a single session; 100% minimum healthy caused a 36-hour deployment outage.
  #
  # Both numbers are load-bearing and neither is sufficient alone. minimum_healthy_percent = 0
  # PERMITS ECS to stop the old task first; maximum_percent = 100 is what FORBIDS it from
  # running two. maximum_percent defaults to 200, and on 2026-07-25 that default let the
  # lane-9 deploy run two tasks from 20:09:19 to 20:13:31. Two containers meant two EyeCloud
  # logins on an account that allows one session. The shim survived because it retries with a
  # forced relogin; the conductor did not, because it resolves its session once at boot. Result:
  # reads were perfect and every /sign returned 502 upstream_error for the life of that task.
  # Do not raise this above 100 while the EyeCloud account is single-session.
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  launch_type                        = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [data.aws_security_group.task.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.gateway.arn
    container_name   = local.name
    container_port   = 443
  }

  depends_on = [aws_lb_listener_rule.mott]
}
