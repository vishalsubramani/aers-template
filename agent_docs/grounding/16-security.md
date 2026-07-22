# Grounding — Security: appsec, identity, cryptography & data protection

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing anything that authenticates, authorizes, accepts external
input, fetches URLs, handles uploads/webhooks, stores or deletes sensitive data, touches crypto or
secrets, adds dependencies, or wires LLM tool use.
**Doctrine hooks:** PAT-01, PAT-16, PAT-17, PAT-18, PAT-19, PAT-20, AX-08, AX-12, AX-13, AX-21,
DD-14, DD-15, DD-16, DF-04, DF-06

## Design checklist

- [ ] Is every external input parsed and validated at one boundary into typed structures —
      including URLs the server will fetch and files users upload? *(PAT-01, AX-08)*
- [ ] Is authorization checked at each object access (not just endpoint-level roles),
      deny-by-default, with decisions logged? *(PAT-17)*
- [ ] Do all security controls fail closed — an errored check denies; a misconfigured process
      refuses to start? *(PAT-16)*
- [ ] Where do secrets come from, how do they rotate without a deploy, and what keeps them out of
      the repo, logs, and error reports? *(PAT-18, AX-13)*
- [ ] What are token/session TTLs, and what is the revocation story — rotation on privilege
      change, refresh-token reuse detection, server-side logout invalidation?
- [ ] Is every cryptographic operation a vetted library with safe defaults, with key IDs in the
      ciphertext and a rotation path designed in from day one? *(PAT-19)*
- [ ] Is every new field classified, with retention and deletion mechanics (including derived
      stores and backups) decided now, not bolted on? *(DD-14, DD-15)*
- [ ] What abuse cases does the threat model name (STRIDE over the data flows), and who owns each
      mitigation?
- [ ] Are dependencies pinned by lockfile and scanned (SCA, SAST, secrets scanning) as required CI
      checks? *(AX-21)*
- [ ] If an LLM reads untrusted content, what bounds the blast radius of injected instructions —
      tool scoping, least-privilege credentials, human confirmation for irreversible actions?

## Application security

- **OWASP Top 10** — a floor, not a ceiling: passing it says nothing about your business-logic
  authorization or specific abuse cases; use it to seed the threat model, never to close it.
- **SQL injection & command injection** — parameterize queries, always; invoke processes with
  argument arrays, never shell strings. Any concatenation of input into an interpreter is a
  review blocker *(PAT-01)*.
- **XSS (stored, reflected, DOM-based)** — encode output for the exact sink (HTML, attribute, JS,
  URL); CSP is the backstop, not the fix; framework auto-escaping dies at `innerHTML`-style APIs.
- **CSRF** — every cookie-authenticated state change needs anti-CSRF tokens plus
  `SameSite=Lax/Strict`; pure bearer-token APIs are immune, so decide by auth transport, not habit.
- **SSRF** — any user-influenced URL fetch can reach cloud metadata endpoints and internal
  services; default move: egress allowlist, block link-local/private ranges, resolve-then-pin
  against DNS rebinding *(PAT-01)*.
- **IDOR / broken object-level authorization** — the most common real breach: verify ownership on
  every object access; endpoint-level role checks are not object-level checks *(PAT-17)*.
- **Mass assignment** — never bind request bodies straight to models; explicit allowlists/DTOs so
  `is_admin` cannot ride along *(PAT-01, AX-08)*.
- **Path traversal** — canonicalize first, then verify the resolved path stays under the allowed
  root; denylist filters for `../` always lose.
- **Insecure deserialization** — never feed untrusted bytes to formats that construct arbitrary
  objects (pickle, Java serialization, unsafe YAML); use plain data formats plus schema
  validation *(PAT-01)*.
- **XXE** — XML parsers resolve external entities by default; disable DTDs and external entities
  wherever XML crosses a trust boundary.
- **Open redirects** — validate redirect targets against relative paths or an allowlist of hosts;
  they launder phishing links and leak OAuth authorization codes.
- **Clickjacking** — set CSP `frame-ancestors` (or `X-Frame-Options`) deny-by-default; exempt only
  pages designed for embedding.
- **ReDoS** — regexes with nested quantifiers on untrusted input hang the process; prefer
  linear-time engines (RE2-class) or bound input length before matching.
- **Prototype pollution** — deep-merging untrusted JS objects can poison `__proto__`; use
  null-prototype maps or vetted merge utilities *(PAT-01)*.
- **TOCTOU races** — check-then-act on files, balances, or quotas is exploitable; make check and
  act atomic (transactions, compare-and-set, `O_EXCL`) *(AX-12, DD-16)*.
- **File-upload handling** — validate type by content not extension, store outside the web root
  under generated names, cap size, never serve with user-controlled Content-Type.
- **Account enumeration, credential stuffing, brute force** — uniform errors and timing on
  login/reset; rate limits with backoff lockouts; stuffing defeats per-account lockout, so also
  limit per IP/device and check breached-password lists.
- **Session management** — rotate the session ID on login and any privilege change (fixation),
  invalidate server-side on logout, bound absolute lifetime *(PAT-17)*.
- **JWT pitfalls** — verify with a pinned algorithm and full validation, never the token's own
  `alg` header; short TTLs plus rotating refresh because stateless tokens cannot be revoked; keep
  them out of XSS-readable storage *(PAT-19)*.
- **Password storage** — argon2id or bcrypt with per-password salts via a maintained library;
  enforce length and breach-list checks, not composition rules *(PAT-19)*.
- **Threat modeling (STRIDE)** — run it at design time over the data-flow diagram; the deliverable
  is abuse cases with owned mitigations, not a shelf document.
- **SAST / DAST / SCA & secrets scanning** — wire into CI as required checks (`make security`);
  tune the noise or the gate rots into rubber-stamping *(AX-21)*.
- **Supply-chain security** — pin via lockfiles, verify provenance and signatures, watch for
  typosquats at install time; a new dependency is a plan-level decision *(AX-21, DF-04)*.
- **Pen tests & bug bounties** — point-in-time and incentive-driven; both find what scanners miss,
  neither substitutes for secure design; triage and pay fast or reports stop coming.
- **WAF** — a useful virtual patch and noise filter, never sufficient: attackers bypass patterns,
  so the underlying vulnerability still gets fixed in code.
- **DDoS protection** — absorb volumetric floods at the CDN/edge; application-layer floods need
  rate limits, caching, and cheap rejection before expensive work *(PAT-20)*.
- **Sandboxing untrusted input and code** — parse risky formats (images, archives, PDFs) and run
  untrusted code in isolated, resource-limited processes; assume the parser will be exploited.
- **Prompt injection & tool-use security** — the new SSRF: everything an LLM reads is attacker
  input; scope tool permissions per task, separate instructions from data, require confirmation
  for irreversible actions.
- **Secure defaults; fail closed** — a control that errors must deny; misconfiguration must yield
  the safe behavior or refuse to start; deny-by-default everywhere *(PAT-16, PAT-17)*.

## Identity & access

- **Authentication vs authorization** — establish identity once at the edge; check permission at
  every resource access; conflating them produces role-checked endpoints with IDOR inside
  *(PAT-17)*.
- **OAuth 2.0 flows** — authorization code + PKCE for anything user-facing (implicit is dead),
  client credentials for service-to-service, device flow for constrained devices; never the
  password grant.
- **OIDC: ID tokens vs access tokens** — ID tokens prove identity to the client only; APIs must
  reject them and validate access tokens with audience checks *(PAT-19)*.
- **Scopes vs fine-grained permissions** — scopes bound what a client may request; they never
  replace per-resource authorization — check both layers *(PAT-17)*.
- **Refresh-token rotation & reuse detection** — rotate on every use and revoke the whole family
  when a stale token replays; this is how short-TTL JWTs get revocation in practice.
- **SSO: SAML vs OIDC; SCIM** — prefer OIDC for new builds, tolerate SAML for enterprise buyers;
  deprovisioning is the point — wire SCIM so leavers actually lose access.
- **MFA** — default to WebAuthn/passkeys (phishing-resistant), TOTP as fallback, SMS last resort;
  harden enrollment and reset paths — they are the real attack target.
- **RBAC / ABAC / ReBAC** — start with roles; adopt attributes or relationship graphs (Zanzibar)
  only when sharing or hierarchy demands it — authz-model migrations are expensive, so the move
  needs an ADR *(AX-17, PAT-17)*.
- **Policy engines (OPA, Cedar)** — externalize authz when many services must share one policy;
  you gain testable, auditable policy and buy a latency/availability dependency on every check
  *(DF-04)*.
- **Service-to-service identity** — workloads authenticate with mTLS/SPIFFE or workload identity
  federation, not shared API keys; internal traffic is not trusted traffic *(PAT-18)*.
- **Short-lived credentials over static keys** — anything long-lived leaks eventually; issue
  minutes-to-hours credentials from identity, and treat every static key as rotation debt
  *(PAT-18)*.
- **IAM least privilege** — per-task roles via assume-role patterns with permission boundaries;
  wildcard actions or resources in a policy are a review blocker *(PAT-17)*.
- **Just-in-time access & break-glass** — standing admin access is the exposure; grant elevation
  on demand with expiry and audit, and pre-build an alarmed break-glass path so emergencies do
  not bypass everything.
- **API key hygiene & rotation** — scope keys per client, store only hashes server-side, support
  overlap-window rotation without downtime, monitor usage so a leak is detectable *(PAT-18)*.

## Cryptography & data protection

- **Encoding ≠ encryption ≠ hashing** — base64/hex transforms, it does not protect; "encoded"
  defended as security is a finding. Encryption for secrecy, hashing/HMAC for integrity.
- **Symmetric crypto: AES-GCM** — the default authenticated encryption; nonce reuse under one key
  is fatal (recovers auth key). Use random 96-bit nonces with bounded message counts, or
  XChaCha20-Poly1305 / AES-GCM-SIV *(PAT-19)*.
- **Asymmetric crypto** — prefer Ed25519 for signatures (misuse-resistant); ECDSA demands perfect
  nonces; RSA is legacy compat — OAEP/PSS only, never PKCS#1 v1.5 in new code *(PAT-19)*.
- **HMAC & signatures** — sign webhooks and artifacts so consumers verify origin; include a
  timestamp to stop replay; verify the signature before parsing the body.
- **Constant-time comparison** — compare MACs, tokens, and secrets with constant-time functions;
  `==` leaks the match prefix through timing.
- **CSPRNGs** — every token, nonce, session ID, and key comes from the OS CSPRNG;
  `Math.random`-class generators in a security context are a finding *(PAT-19)*.
- **TLS & certificate lifecycle** — TLS 1.2 floor, 1.3 preferred; automate issuance and renewal
  (short-lived certs) — manual certificate expiry is a top self-inflicted outage; alert on expiry.
- **Encryption at rest: disk vs field-level** — disk/volume encryption only defends stolen
  hardware; fields the application should not broadly read need field-level encryption under
  separate keys *(DD-14)*.
- **Encryption in transit, everywhere** — including internal service-to-service traffic; "trusted
  network" is a flat-network breach amplifier; use mTLS or mesh-provided TLS.
- **Envelope encryption; KMS / HSM** — encrypt data with data keys, wrap data keys with a KMS-held
  root key the application never sees; rotation and audit come with the service *(DF-06)*.
- **Key rotation strategy** — design rotation before the first byte is encrypted: key IDs in
  ciphertext headers, lazy or scheduled re-encryption; a system that cannot rotate keys cannot
  respond to compromise *(PAT-18)*.
- **Tokenization vs encryption** — tokenization swaps values for vault-held references, shrinking
  compliance scope (PCI); choose it when downstream systems need format-preserving stand-ins,
  not the real value.
- **Deterministic encryption tradeoffs** — equal plaintexts yield equal ciphertexts, enabling
  lookups but leaking distribution; restrict to high-entropy fields, or prefer blind-index
  (HMAC) lookup columns.
- **Crypto-shredding** — delete by destroying a per-subject key; the practical erasure path for
  backups and immutable stores — but only if per-subject keys were designed in upfront *(DD-15)*.
- **Secrets management** — vault-injected at runtime, dynamic short-lived credentials where
  possible; nothing in repos, logs, env dumps, or error reports — and scan CI for leaks
  *(PAT-18, AX-13)*.
- **Don't roll your own crypto** — includes protocols and composition, not just primitives:
  homegrown token formats, padding schemes, or verification logic are findings; use maintained
  libraries with safe defaults *(PAT-19)*.
- **Data classification; PII / PHI / PCI scopes** — classify every field at design time; regulated
  data draws compliance boundaries — segregate to minimize scope, keep it out of logs and traces
  *(DD-14)*.
- **Data residency & sovereignty** — where data may legally live constrains regions, replication,
  backups, and vendors; retrofitting residency is a re-architecture, so ask at design time
  *(DF-06, DD-14)*.
- **Privacy by design** — DSAR export, deletion, and consent mechanics are features designed with
  the data model; deletion must reach derived stores and backups *(DD-15, DD-17)*.
