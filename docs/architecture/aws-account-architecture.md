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

## IAM / SSO baseline

- Use **AWS IAM Identity Center** integrated with corporate IdP (Google Workspace/Okta/Azure AD).
- No long-lived IAM users in workload accounts (break-glass only in Management with strict controls).
- Role sets (minimum):
  - `Admin` (limited group)
  - `PlatformEngineer`
  - `Developer`
  - `ReadOnly`
  - `BillingReadOnly` (Management only)

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

## 6) Secrets, Observability, Backup/DR, Cost Controls

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

## 7) Phased Rollout Plan

### Phase 0 (Week 0-1): Foundation
- Create AWS Organization + 4 baseline accounts
- Enable IAM Identity Center and initial permission sets
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

## 8) Decision Log (Alternatives Considered)

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

## 9) Approval Ask

Approve the **4-account baseline now** with **Dev + Prod runtime model**, and defer dedicated **Staging** account until defined growth/compliance triggers are met.
