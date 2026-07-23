# Grounding — Infrastructure & delivery: cloud, containers, CI/CD, IaC

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** provisioning cloud resources or networks, writing Dockerfiles or Kubernetes
manifests, designing CI/CD pipelines, planning a rollout/rollback or feature-flag strategy,
authoring Terraform/IaC, or deciding managed vs self-hosted.
**Doctrine hooks:** AX-01, AX-06, AX-09, AX-10, AX-13, AX-14, AX-15, AX-16, AX-17, AX-18, AX-20,
AX-21, AX-22, DD-10, DD-11, DD-15, PAT-02, PAT-05, PAT-14, PAT-15, PAT-16, PAT-18, PAT-20, DF-04,
DF-06

## Design checklist

- [ ] Which failure domain (AZ, region, account) must this survive, and does the topology
      actually span it? *(AX-22)*
- [ ] Is the artifact built once, digest-addressed, and promoted unchanged through every
      environment, varying only config? *(AX-13, AX-15)*
- [ ] Is rollback real — are data migrations expand–contract sequenced so the previous
      version still runs? *(AX-15, DD-10, DD-11)*
- [ ] How do secrets reach build and runtime — OIDC federation and a secret store, never
      long-lived keys, CI variables, or state files? *(PAT-18, AX-13)*
- [ ] What deployment strategy fits this risk tier, and does automation (SLO burn), not a
      human on a dashboard, trigger rollback? *(AX-22, AX-14)*
- [ ] Are requests/limits, probes, PDBs, and termination grace set from measurement rather
      than left at defaults? *(PAT-15, AX-18)*
- [ ] Where do retries live — mesh, client, or app — and is there exactly one layer with a
      budget? *(PAT-05, PAT-20)*
- [ ] Does every infra change flow through reviewed code (pipeline defs, IaC plans, GitOps),
      with console/kubectl drift detected and alerted?
- [ ] What is the blast radius boundary — account, state file, cluster — and does this change
      stay inside one?
- [ ] Has managed vs self-hosted been answered honestly, with lock-in concentrated behind
      adapters rather than avoided everywhere? *(DF-06, PAT-02)*
- [ ] Supply chain: are images scanned, signed, SBOM-inventoried, and provenance-verified at
      deploy admission? *(AX-21)*
- [ ] What does this design cost — NAT/egress, load balancers, idle environments, oversized
      instances — and will anyone see the bill before month-end?

## Cloud

- **Regions, availability zones, edge locations** — AZ outages are routine, region outages
  rare-but-real; state which your availability target survives before picking topology, and
  spread replicas accordingly *(AX-22)*.
- **Shared responsibility model** — the provider secures the substrate; config, identities,
  and data are yours. Most cloud breaches are customer misconfiguration — review IAM and
  exposure, not the vendor's SOC 2.
- **VPCs, subnets, route tables, gateways** — private subnets by default; anything reaching
  the internet should be a deliberate, reviewable route-table entry, not an accident of the
  default VPC.
- **Security groups vs NACLs** — security groups (stateful) are the primary control; NACLs
  are a stateless coarse backstop. Duplicating rules in both doubles the drift surface.
- **NAT gateways** — per-GB processing turns chatty private-subnet egress (image pulls,
  telemetry) into surprise bills; route high-volume same-cloud traffic through VPC/gateway
  endpoints instead.
- **Peering, PrivateLink, transit gateways** — peering is non-transitive, so hub-and-spoke
  needs a transit gateway; prefer PrivateLink to expose one service without merging two
  networks' trust domains.
- **Object vs block vs file storage** — default to object unless you need POSIX or a boot
  volume; block ties data to instance lifecycle, and shared file systems become hidden
  coupling between services.
- **Object-store semantics: consistency, storage classes, lifecycle rules, presigned URLs,
  multipart uploads** — lifecycle rules delete data (treat as DD-15 policy); scope and
  expire presigned URLs; clean up orphaned multipart parts; class transitions carry
  retrieval costs *(DD-15)*.
- **Compute spectrum: bare metal → VM → container → serverless** — pick the highest
  abstraction the workload tolerates; moving right trades control and runtime limits for
  less undifferentiated ops *(DF-06)*.
- **Serverless cold starts & concurrency limits** — latency-sensitive paths need provisioned
  concurrency or a warm tier; account concurrency caps are a shared quota one runaway
  function can exhaust.
- **Spot / preemptible instances** — only for interruption-tolerant, checkpointable work
  that handles the termination notice and drains; never for singleton stateful nodes,
  always with an on-demand fallback.
- **Instance right-sizing** — size from measured utilization, not guesses; chronic low CPU
  means downsize, and autoscaling beats permanent oversizing for spiky load *(AX-18)*.
- **Managed vs self-hosted: honest TCO** — price on-call, upgrades, backups, and expertise,
  not just the invoice *(DF-06)*.
- **Vendor lock-in vs velocity** — take managed velocity by default; concentrate lock-in
  behind ports/adapters rather than paying a portability tax everywhere for a migration
  that never happens *(PAT-02, DF-04)*.
- **Service quotas & limit increases** — quotas fail launches at the worst moment; check
  quotas for every new resource type at plan time — increases take tickets and days.
- **Well-Architected pillars** — use as an infra-ADR review checklist (security,
  reliability, cost, performance, operations); its value is naming the pillar the design
  silently sacrificed.
- **Landing zones & account structure** — accounts/projects are the strongest blast-radius,
  IAM, and billing boundary; separate prod from non-prod at account level, not by tag.
- **Egress and cross-AZ traffic costs** — data transfer is billed asymmetrically; any
  design moving bulk data across zones, regions, or to the internet needs a costed traffic
  path before approval.

## Containers & orchestration

- **Images vs containers; the OCI standard** — images are immutable artifacts, containers
  disposable processes; never patch a running container, and build OCI-compliant so
  registries and runtimes stay swappable.
- **Docker layer caching; multi-stage builds** — order Dockerfiles least- to most-changing
  (deps before source) or the cache never hits; multi-stage keeps build toolchains out of
  the runtime image.
- **Minimal / distroless base images** — smaller CVE surface and pull time; the cost is no
  shell for debugging — plan ephemeral debug containers instead of reverting to fat images.
- **Never `:latest` in prod; tag immutability, digests** — deploy by immutable tag or
  digest so rollback and audit reference an exact artifact; mutable tags make "what is
  running?" unanswerable *(AX-15)*.
- **Image scanning & SBOMs** — scan in CI, gate on severity with an exception process; keep
  an SBOM per artifact — the next Log4j question is "where is it running?" *(AX-21)*.
- **PID 1, signal handling, init shims** — a naive PID 1 ignores SIGTERM and orphans
  zombies, making every deploy a SIGKILL; use tini or exec-form entrypoints and handle
  SIGTERM *(AX-09)*.
- **Resource requests vs limits; CPU throttling** — requests schedule, limits enforce; CPU
  limits throttle (tail-latency spikes), memory limits OOM-kill. Set requests from
  measurement; consider omitting CPU limits for latency-sensitive services *(AX-18)*.
- **Kubernetes workloads: Pod, Deployment, StatefulSet, DaemonSet, Job, CronJob** — match
  object to lifecycle; a StatefulSet is a prompt to ask whether that state belongs in a
  managed store instead *(DF-06)*.
- **Services (ClusterIP/NodePort/LoadBalancer), Ingress, Gateway API** — ClusterIP is the
  internal default; each LoadBalancer costs money — consolidate HTTP behind one
  Ingress/Gateway with TLS termination decided explicitly.
- **ConfigMaps & Secrets** — Secrets are base64, not encryption: encrypt etcd and prefer
  external secret stores with rotation; remember pods need restart/reload to see config
  changes *(PAT-18, AX-13, PAT-16)*.
- **Startup vs readiness vs liveness probes** — liveness that checks dependencies causes
  cluster-wide restart storms; keep liveness dumb, readiness dependency-aware, and use
  startup probes for slow boots *(PAT-15)*.
- **QoS classes & eviction** — requests==limits earns Guaranteed; BestEffort is evicted
  first under node pressure. Don't leave critical workloads Burstable by accident.
- **HPA / VPA / KEDA; cluster autoscaling** — scale on a metric that tracks load, not CPU
  by reflex; HPA and VPA conflict on the same resource; pod autoscaling without cluster
  autoscaling just pends *(PAT-20)*.
- **PodDisruptionBudgets** — without a PDB, node drains take all replicas at once; too
  strict and upgrades wedge. Every multi-replica service gets one, sized against real
  replica count.
- **Rolling-update knobs: maxSurge / maxUnavailable** — these set capacity during rollout;
  defaults can drop 25% of capacity mid-deploy at peak — derive them from measured headroom.
- **Affinity, anti-affinity, taints, tolerations, topology spread** — spread replicas
  across zones or one AZ outage takes the service; taints repel but don't attract — pair
  tolerations with affinity for dedicated (GPU) nodes.
- **Operators & CRDs** — an operator is software you now operate: upgrades, RBAC, failure
  modes. Prefer managed services or plain manifests unless the reconciliation logic earns
  it *(AX-01, DF-04)*.
- **Helm charts: values, templating pitfalls** — text-templating YAML invites whitespace
  and unvalidated-values bugs; always `helm template` and diff in CI, pin chart versions,
  schema-validate values *(PAT-16)*.
- **Kustomize** — prefer overlay patches to heavy templating for environment variance; keep
  base/overlay drift small and reviewable or you recreate environment-parity bugs.
- **GitOps: reconciliation loops (Argo/Flux)** — git is desired state and reconcilers
  revert manual hotfixes; the emergency-change procedure must go through git too, or
  incidents fight the controller *(AX-15)*.
- **Service mesh: mTLS, traffic policy** — buys mTLS and policy at real operational cost;
  mesh retries multiply app retries — put retries and budgets at exactly one layer
  *(PAT-05, PAT-20, AX-01)*.
- **Graceful termination: preStop hooks, drain windows** — pods receive traffic after
  SIGTERM; use preStop sleep plus a termination grace period longer than the slowest
  in-flight request *(AX-09)*.
- **Cluster upgrades & API deprecations** — Kubernetes removes APIs on a cadence; scan
  manifests for deprecated versions before upgrades, and design workloads (PDBs, surge
  nodes) so node upgrades are routine, not events.

## CI/CD & release engineering

- **Pipelines as code** — pipeline definitions live versioned and reviewed in the repo;
  click-configured CI is invisible drift and unauditable change.
- **Build once, promote the same artifact everywhere** — rebuilding per environment means
  prod runs an untested binary; promote one digest-addressed artifact through stages,
  varying only configuration *(AX-13)*.
- **Reproducible & hermetic builds** — pin toolchains and inputs so two builds of one
  commit match; network-fetching builds break at 2am and void provenance claims.
- **Build caching (local, remote, layer) & dependency caching** — key caches on
  input/lockfile hashes; a stale or poisoned cache is a correctness and supply-chain risk —
  caching must stay an optimization, never load-bearing.
- **Test sharding & parallelism in CI** — shard by measured timing, not file count;
  parallel runs expose shared-state assumptions (ports, databases, fixtures) — isolate
  resources per shard *(AX-16)*.
- **Merge queues** — covered in `03-writing-code.md`; the pipeline-side move is making the
  queue's post-merge test the required check, so semantic conflicts never reach main.
- **Ephemeral preview environments** — per-PR environments catch integration issues before
  merge; enforce TTLs, teardown, and seeded data or they become expensive snowflakes.
- **Environment parity (dev/stage/prod)** — most "worked in staging" failures are parity
  gaps in data scale, config, or versions; document known deltas and keep the deploy
  mechanism identical *(AX-13)*.
- **Secrets in CI (OIDC federation)** — mint short-lived cloud credentials per job via
  OIDC; long-lived keys in CI variables are a top exfiltration target *(PAT-18)*.
- **Supply-chain integrity: provenance, SLSA, artifact signing** — sign artifacts and emit
  provenance at build, verify at deploy admission; an unverified path from build to prod is
  the gap attackers use *(AX-21)*.
- **Deployment strategies: rolling, blue-green, canary, shadow traffic** — rolling is the
  default; blue-green buys instant cutover at 2x cost; canary bounds blast radius; shadow
  validates without user exposure — choose per risk tier *(AX-15)*.
- **Progressive delivery; automated rollback on SLO burn** — canaries are judged by machine
  against SLO and guardrail metrics with automatic rollback, not by a human watching
  dashboards *(AX-22, AX-14)*.
- **Rollbacks vs roll-forward** — rollback is only real if data changes are backward
  compatible; a deploy paired with a one-way migration has no rollback — the plan must say
  so *(AX-15, DD-10)*.
- **Expand–contract sequencing with deploys** — the deploy-order half of `04-data-storage.md`'s
  expand→migrate→contract: expand ships before dependent code; contract only after all consumers
  migrate and the rollback window closes *(DD-11)*.
- **Feature flag taxonomy: release / ops / experiment / permission** — each kind has a
  different lifetime and owner; conflating them is how "temporary" flags become permanent
  unowned config *(PAT-14)*.
- **Flag hygiene: expiry, cleanup, kill switches** — every flag has an owner, expiry, and
  removal ticket; test both states of load-bearing flags; exercise kill switches regularly
  or they won't work *(PAT-14, AX-20)*.
- **Dark launches** — run new code paths in prod without exposing results; validates load
  and behavior, but dark-launched writes need idempotency and isolation from real data
  *(AX-10)*.
- **A/B testing: guardrail metrics, sample size, peeking** — pre-register sample size and
  guardrails; peeking at running experiments inflates false positives — use fixed horizons
  or sequential methods, and check guardrails before shipping winners.
- **SemVer & CalVer; breaking-change discipline** — version numbers are promises: breaking
  change means major bump plus deprecation window; use CalVer only where compatibility
  promises aren't the point *(AX-06)*.
- **Changelogs & release notes** — generate from conventional commits or PR labels, or they
  rot; a consumer must answer "what changed and does it break me?" without reading diffs.
- **Dependency hell: diamonds, transitive pins, lockfiles, update cadence** — commit
  lockfiles always; small frequent automated update PRs beat yearly big-bang upgrades where
  diamond conflicts surface all at once *(AX-21)*.

## Infrastructure as code

- **Declarative vs imperative provisioning** — declarative desired-state is the default;
  imperative scripts drift immediately and cannot be plan-reviewed. Console changes are
  incidents-in-waiting.
- **Terraform: state, locking, drift detection, plan review** — remote state with locking is
  non-negotiable; every apply follows a reviewed plan — a `-/+` destroy-and-recreate on a
  stateful resource is data loss in disguise.
- **Terraform modules & workspaces** — pin module versions; use workspaces only for small
  config deltas and separate roots for divergent environments, or one plan's blast radius
  spans them all *(AX-17)*.
- **State security** — state files hold secrets in plaintext (passwords, keys); encrypt
  state at rest, restrict access like a secret store, never commit it *(PAT-18)*.
- **Importing existing resources** — import before managing, or the first apply tries to
  recreate what exists; after import, iterate until the plan is empty before changing
  anything.
- **Policy as code (OPA/Sentinel); static IaC scanning** — gate applies in CI on policies
  that catch public buckets and open security groups; guardrail policies are protected
  files, not suggestions.
- **Blast radius: small stacks, targeted applies** — one giant state file makes every apply
  risk everything; split stacks by lifecycle and team. Targeted applies are for
  emergencies only — they hide drift.
- **CDK / Pulumi: real-language IaC** — buys abstraction and unit-testable infra, costs
  plan opacity and another toolchain; review the synthesized diff, not just the source
  *(AX-01)*.
- **Immutable infrastructure; pets vs cattle** — replace, don't patch: SSH-fixing a server
  forks it from its definition. Anything needing in-place care is a pet — name it,
  document it, eliminate it *(AX-15)*.
- **Golden images (Packer) vs config management (Ansible)** — bake slow, stable layers into
  images for deterministic fast boot; convergent config management on live hosts drifts —
  prefer bake-and-replace.
- **Config drift and its detection** — run scheduled drift detection with alerting; drift
  means either an emergency change to backport into code or an access hole to close.
