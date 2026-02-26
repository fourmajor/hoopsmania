# AWS Account Architecture Proposal (Hoops Mania)

Owner: AI Employee **cloudwire**  
Status: Proposed (review)  
Related issue: #129

## 1) Executive Recommendation

Adopt a **4-account AWS Organizations baseline now**:

1. **Management (Org payer/root)** — billing + org administration only
2. **Security/Log Archive** — centralized CloudTrail, Config snapshots, Security Hub findings, immutable logs
3. **Development** — all active engineering dev/test workloads
4. **Production** — live customer workloads

### Dev/Prod/Test decision

- **Now:** Use **Dev + Prod** only, with test environments isolated inside Dev by account-level and VPC-level controls.
- **When to add Stage/Test account:** Add a dedicated **Staging** account once either condition is met:
  - >10 engineers or parallel release trains create frequent integration collisions, or
  - Compliance / enterprise customer requirements need prod-like pre-release validation in a separate account.

This keeps operating overhead low today while preserving a clean growth path.

---

## 2) Organization Structure (OUs)

Recommended OUs:

- **Foundation OU**
  - Management account
  - Security/Log Archive account
- **Workloads OU**
  - Development account
  - Production account

Optional future OUs:
- **Sandbox OU** (experiments)
- **Staging OU** (pre-prod hardening)

---

## 3) IAM / SSO Baseline + SCP Guardrails

## IAM / access baseline (solo-founder friendly)

- Use **AWS IAM Identity Center** with its built-in identity store (no paid corporate IdP required).
- Treat external IdP federation (Google Workspace/Okta/Azure AD) as **optional later**, not a prerequisite.
- For a solo founder, start with 2 users in Identity Center:
  - day-to-day user (least privilege)
  - emergency break-glass admin user (hardware MFA + vault-stored recovery)
- No long-lived IAM users in workload accounts (break-glass only in Management with strict controls).
- Permission sets (minimum):
  - `Admin` (limited use)
  - `PlatformEngineer`
  - `Developer`
  - `ReadOnly`
  - `BillingReadOnly` (Management only)
- If Identity Center rollout must be delayed, temporary fallback is acceptable:
  - one tightly-scoped IAM user in Management account only
  - mandatory MFA + access key disabled by default
  - migrate to Identity Center before production cutover.

### Low-cost AWS-native access options (no corporate IdP)

1. **Preferred now:** IAM Identity Center + built-in identity store (included with AWS Organizations)
2. **Short-term bootstrap:** Management-account IAM user + MFA, then migrate to Identity Center
3. **Do not conflate with workforce auth:** Amazon Cognito is for app/customer sign-in and should not replace admin/workforce account access controls

## SCP guardrails (minimum)

Apply at OU level, then tune per account:

- Deny disabling/deleting CloudTrail, Config, GuardDuty, Security Hub
- Deny leaving organization
- Restrict unsupported regions (allowlist only required regions)
- Deny root user API actions except account/billing recovery essentials
- Require encryption defaults (EBS/RDS/S3) via policy and detective controls
- Block public S3 ACL/policy except approved exception path

---

## 4) Networking and Environment Isolation

- Separate VPCs per environment account (Dev vs Prod), no shared mutable runtime infrastructure.
- Prefer private subnets for app/data tiers; public exposure only through managed edge (ALB/API Gateway/CloudFront).
- Use Transit Gateway only when multi-VPC complexity justifies it; otherwise keep simple VPC peering or isolated VPCs.
- Centralize DNS governance with Route 53 hosted zones and delegated subdomains per environment.
- Enforce egress controls (NAT + domain/IP policy where needed).

Isolation principle: **account boundary is the strongest default security and blast-radius boundary**.

---

## 5) CI/CD Deployment Account-Role Strategy

- CI pipeline runs in Development tooling context (e.g., GitHub Actions OIDC).
- Use OIDC federation from GitHub to assume AWS roles (no static AWS keys in GitHub secrets).
- Separate deploy roles per target account:
  - `gha-deploy-dev` in Development account
  - `gha-deploy-prod` in Production account (stricter permissions + manual approval gate)
- Enforce branch/environment protections:
  - `main` -> prod deploy role only with approval
  - feature branches -> dev deploy role
- Keep infra and app deploy permissions scoped to least privilege (separate roles where possible).

---

## 6) Infrastructure as Code (IaC) Baseline

Treat **all foundation and workload infrastructure as code** (accounts, IAM/Identity Center assignments, SCPs, networking, CI roles, logging, backup policies).

### IaC tool options considered

1. **AWS CDK (preferred)**
   - Pros: strong AWS service coverage, high-level constructs, native TypeScript/Python workflows, easier policy composition and reuse
   - Cons: requires discipline to review synthesized CloudFormation output

2. **Terraform (HCL)**
   - Pros: multi-cloud portability, large ecosystem, familiar in many teams
   - Cons: extra provider/state management overhead for a mostly AWS-native stack

3. **Raw CloudFormation**
   - Pros: fully native, no additional framework abstraction
   - Cons: lower developer ergonomics and more verbose templates for complex stacks

### Decision

Use **AWS CDK as the default IaC framework** for Hoops Mania, with these controls:
- Source all infra from version-controlled repositories (no ad-hoc console-only resources except emergency break-glass actions).
- Enforce `cdk diff` + PR review before apply.
- Use environment/account-specific stacks for Dev vs Prod, with least-privilege deploy roles per account.
- Periodically detect and reconcile drift against declared stacks.

---

## 7) Secrets, Observability, Backup/DR, Cost Controls

## Secrets

- Use AWS Secrets Manager + SSM Parameter Store (hierarchical path per env).
- KMS CMKs per account with least-privilege key policies.
- Automatic rotation for DB/API credentials where feasible.

## Logging/Monitoring

- Org-level CloudTrail to Security/Log Archive account.
- AWS Config enabled in all accounts/regions in scope.
- CloudWatch metrics/logs + alarms baseline (latency, error rate, saturation, spend anomalies).
- Security Hub + GuardDuty centralized in Security account.

## Backup/DR

- AWS Backup plans per workload class (daily/weekly retention tiers).
- Cross-account backup copy for critical production data (Prod -> Security/Backup vault).
- Define RTO/RPO tiers:
  - Tier 1 (core game/backend): RTO <= 4h, RPO <= 1h
  - Tier 2 (internal tools): RTO <= 24h, RPO <= 24h

## Cost controls

- Mandatory tags: `Environment`, `Service`, `Owner`, `CostCenter`.
- Budgets + anomaly detection per account.
- Monthly rightsizing review + savings plan review after baseline usage stabilizes.

---

## 8) Phased Rollout Plan

### Phase 0 (Week 0-1): Foundation
- Create AWS Organization + 4 baseline accounts
- Enable IAM Identity Center (built-in identity store) and initial permission sets
- Turn on centralized CloudTrail/Config/GuardDuty/Security Hub
- Apply baseline SCPs

### Phase 1 (Week 1-2): Dev migration
- Stand up Dev account networking and CI OIDC role
- Move active dev workloads into Dev account
- Validate tagging, budgets, and alarms

### Phase 2 (Week 2-4): Prod hardening + cutover
- Stand up Prod account infra with stricter controls
- Configure prod deploy approvals and backup policies
- Migrate/launch production workloads

### Phase 3 (Ongoing): Maturity triggers
- Add Staging account if release/compliance triggers are met
- Expand SCP and detection controls from observed gaps
- Quarterly access + cost governance review

---

## 9) Decision Log (Alternatives Considered)

1. **Single account for everything**
   - Pros: simplest setup
   - Rejected: weak isolation, high blast radius, difficult governance

2. **Dev + Prod only (selected now)**
   - Pros: strong baseline isolation with manageable ops overhead
   - Cons: less pre-prod realism vs dedicated staging
   - Decision: best current fit for team size/speed

3. **Dev + Staging + Prod from day one**
   - Pros: cleaner promotion path, better pre-prod parity
   - Rejected for now: extra operational burden too early

4. **Full multi-account landing zone (6+ accounts immediately)**
   - Pros: enterprise-grade separation
   - Rejected for now: over-engineered for current Hoops Mania stage

---

## 10) Approval Ask

Approve the **4-account baseline now** with **Dev + Prod runtime model**, and defer dedicated **Staging** account until defined growth/compliance triggers are met.

---

## 11) Operational Readiness Guardrails (Recommended Additions)

To keep rollout practical and auditable, adopt these minimum controls alongside the 4-account decision:

### Account boundary controls

- Keep **Security/Log Archive** account read-only from workload accounts (no workload deploy roles trusted into Security).
- Maintain a dedicated **break-glass admin role** in Management account with MFA, hardware-key requirement, and emergency-only runbook use.
- Add explicit deny on cross-account `iam:PassRole` except approved CI/CD deploy roles.

### CI/CD trust hardening

- For GitHub OIDC trust policies, require at minimum:
  - repository allowlist (`token.actions.githubusercontent.com:sub`)
  - expected audience (`sts.amazonaws.com`)
  - branch/environment binding (`refs/heads/main` for prod)
- Separate infra and app deployment roles in Prod so app pipelines cannot mutate org/security controls.

### Network isolation baseline

- Default deny inbound via security groups/NACLs; expose only through approved edge services.
- Prefer VPC endpoints (PrivateLink/Gateway endpoints) for AWS service access to reduce internet egress.
- Record and review any approved Dev↔Prod connectivity exceptions quarterly.

### Observability + DR verification

- Define service-level alert thresholds (e.g., p95 latency, 5xx, queue depth) and route to on-call.
- Enable immutable log retention policy in Security/Log Archive and test log access during incident drills.
- Run **quarterly backup restore tests** and at least **one game-day failover simulation per half** for Tier 1 systems.

### Rollout realism / exit criteria

- Phase exit gates should require:
  - successful least-privilege validation of deploy roles
  - passing backup restore test for at least one Tier 1 data store
  - dashboard + alert coverage for critical services
  - documented rollback rehearsal evidence

These additions keep the proposal lightweight while making security, resilience, and rollout readiness enforceable in practice.

