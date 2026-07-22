# Grounding — Networking & the web platform

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing anything that crosses a network boundary — API surfaces,
proxies/load balancers, TLS and certificates, caching/CDN layers, browser-facing features,
realtime transports, or webhooks.
**Doctrine hooks:** AX-06, AX-09, AX-10, AX-14, AX-15, AX-18, DD-16, DD-17, PAT-01, PAT-04,
PAT-05, PAT-06, PAT-07, PAT-09, PAT-17, PAT-18, DF-03, DF-05

## Design checklist

- [ ] Does every hop have explicit timeout/retry/breaker, and does each downstream timeout nest
  inside its caller's? *(AX-09, PAT-05)*
- [ ] Are all network-triggered mutations (POST bodies, webhook deliveries) idempotent under
  retry? *(AX-10, PAT-06)*
- [ ] Does every response declare explicit caching, and does every cache layer (browser, CDN,
  proxy) have a named invalidation story and staleness bound? *(PAT-09, DD-17, DF-05)*
- [ ] What are the DNS TTLs and the certificate rotation/expiry-alerting story for failover and
  cutover? *(PAT-18, AX-14)*
- [ ] Which hop in the chain loses multiplexing or reintroduces head-of-line blocking (e.g., H2
  at the edge, H1 to origin)?
- [ ] Are cookies, CORS, and security headers deny-by-default — and is CORS never mistaken for
  authorization? *(PAT-17)*
- [ ] Can any instance serve any request (no sticky sessions), so deploys, autoscaling, and
  failover don't strand state?
- [ ] Are read-modify-write HTTP APIs protected against lost updates with ETag/If-Match?
  *(AX-10, DD-16)*
- [ ] For realtime features, is the transport chosen by need (SSE vs WebSocket vs polling) with
  heartbeat, reconnect, and resume designed in? *(DF-03, AX-09)*
- [ ] If organic search or link previews matter, do crawlers receive rendered content, verified
  with fetch-as-bot evidence? *(AX-18)*

## Networking

- **OSI vs TCP/IP mental models** — use layers to localize faults (DNS? TCP? TLS? HTTP?)
  during debugging; in design conversations the distinction that matters is L4 vs L7, not layer
  trivia.
- **DNS: record types, TTLs, caching, negative caching, "propagation"** — failover speed is
  bounded by TTL and resolvers that ignore it; lower TTLs before cutovers; negative caching
  delays brand-new records — "propagation" is just caches expiring.
- **Anycast** — cheap geo-routing and DDoS absorption, but route flaps break long-lived TCP
  connections mid-stream; use it for DNS and stateless edge, not stateful sessions.
- **TCP: handshake, slow start, congestion control, Nagle vs delayed ACK, TIME_WAIT** — new
  connections pay handshake plus slow start, so pool and reuse; Nagle with delayed ACK stalls
  small RPC writes ~40 ms; connection churn exhausts ports via TIME_WAIT.
- **UDP; QUIC** — QUIC gives TLS and multiplexing without transport head-of-line blocking, but
  middleboxes still block or throttle UDP — always keep a TCP/H2 fallback path.
- **TCP vs UDP tradeoffs** — pick UDP only when late data is worthless (media, telemetry) and
  you own loss handling; "we'll add reliability on UDP" is rebuilding TCP badly *(AX-01)*.
- **HTTP/1.1 keep-alive → HTTP/2 multiplexing → HTTP/3** — H2 removes the six-connection limit
  but concentrates failure onto one connection; internal hops still speaking H1 to origins
  reintroduce queuing — audit the whole chain, not just the edge.
- **Head-of-line blocking** — application-layer (H1 serial requests) and transport-layer (one
  lost TCP packet stalls every H2 stream) are different problems; tail latency on lossy
  networks is the actual argument for H3.
- **TLS: handshake, session resumption, ALPN, SNI** — handshakes cost round trips: require
  TLS 1.3 and resumption for latency; ALPN negotiates H2/H3; SNI is plaintext and drives
  routing and cert selection — multi-tenant designs depend on it.
- **mTLS** — the default for service-to-service authentication; the hard part is automated cert
  issuance and rotation, not the handshake — no automation, no mTLS *(PAT-17, PAT-18)*.
- **Certificates: chains, expiry, rotation, pinning** — expiry is a top self-inflicted outage:
  automate rotation and alert on expiry windows *(PAT-18, AX-14)*; serve the full chain; pin
  only with a tested rotation story, or you brick clients.
- **Forward vs reverse proxies** — forward controls egress, reverse controls ingress (TLS
  termination, routing, buffering); a proxy idle timeout shorter than upstream keep-alive
  causes racy 502s — align them explicitly *(AX-09)*.
- **Slow clients & proxy buffering** *(added)* — reverse-proxy request buffering shields
  origins from slow clients (slowloris), but response buffering silently breaks streaming
  (SSE, chunked) — disable it per streaming route and test through the real edge.
- **Load balancing: L4 vs L7; round-robin, least-connections, consistent hashing, EWMA** — L7
  buys routing, retries, and observability at CPU/TLS cost; round-robin misbehaves under uneven
  request cost — prefer least-connections or EWMA; consistent hashing only for cache locality.
- **Sticky sessions** — they pin state to instances and break deploys, autoscaling, and
  failover; externalize session state and design stickiness away — treat any new dependence on
  it as a review finding.
- **NAT; bandwidth-delay product; MTU** — NAT idle timeouts silently drop quiet long-lived
  connections (send keepalives); throughput caps at window/RTT on long fat pipes; tunnel/VPN
  MTU mismatch hangs only large payloads — a classic misleading symptom.
- **CDNs: how they actually work** — pull-through caches keyed by URL plus varied headers:
  normalize cache keys, set explicit TTLs, and treat cache poisoning and personalized-content
  leaks as design risks; every cached object needs an invalidation story *(PAT-09, DD-17)*.

## Web platform

- **HTTP semantics: methods, safety, idempotency, status codes** — GET must be safe (crawlers
  and prefetchers will call it); PUT/DELETE idempotent by contract; POST needs idempotency keys
  *(AX-10, PAT-06)*; status codes are the interface retries and caches key off *(AX-06)*.
- **HTTP caching: Cache-Control, ETag / If-None-Match, stale-while-revalidate** — set explicit
  Cache-Control on every response (heuristic caching is a bug source); ETags make revalidation
  cheap; stale-while-revalidate hides origin latency behind a stated staleness bound
  *(PAT-09, DF-05)*.
- **Conditional requests & optimistic concurrency (If-Match)** — any read-modify-write API over
  HTTP needs ETag/If-Match to prevent lost updates; last-write-wins is a decision to record,
  never a default *(AX-10, DD-16)*.
- **Cookies: Secure, HttpOnly, SameSite** — default Secure + HttpOnly + SameSite=Lax; an auth
  cookie readable by JS or sent cross-site is a finding, not a preference; scope Domain/Path as
  narrowly as possible *(PAT-17)*.
- **CORS (what preflight actually is)** — a browser-enforced gate, not server auth: preflight
  only asks permission; never treat CORS as access control, and never reflect arbitrary origins
  with credentials enabled *(PAT-17)*.
- **CSP, HSTS, SRI, security-header family** — ship the family by default; CSP is the XSS
  backstop (roll out report-only first); HSTS with preload is effectively irreversible — treat
  enabling it like a one-way migration *(AX-15)*.
- **Browser event loop: microtasks vs macrotasks** — long tasks freeze the UI, and microtask
  storms starve rendering entirely — chunk work or move it to a worker; promise-vs-timer
  ordering bugs come from this split.
- **Rendering pipeline: reflow vs repaint** — interleaving layout reads with writes forces
  synchronous reflow (layout thrashing) — batch reads, then writes; animate transform/opacity,
  never layout properties.
- **Service workers & web workers** — web workers move CPU off the main thread; a service
  worker is a programmable proxy whose stale cached code is a self-inflicted outage — version
  it and test the update path *(AX-15, PAT-09)*.
- **localStorage / sessionStorage / IndexedDB (and their limits)** — localStorage is
  synchronous and evictable; treat all browser storage as a rebuildable cache of the server,
  never source of truth, and never for tokens JS shouldn't read *(DD-17, PAT-17)*.
- **WebSockets vs Server-Sent Events vs long polling** — pick by need, not fashion: SSE for
  server-to-client streams (plain HTTP, auto-reconnect); WebSockets only for true
  bidirectional; either way design heartbeat, reconnect, and resume-from-last-event
  *(DF-03, AX-09)*.
- **Webhooks: signatures, replay protection, retries, idempotent handlers** — verify HMAC
  signatures with timestamp tolerance, dedupe by delivery ID, ack fast and process via queue —
  senders retry, so handlers must be idempotent *(PAT-01, AX-10, PAT-06, PAT-07)*.
- **preload / prefetch / preconnect** — preconnect to known third-party origins; preload only
  late-discovered critical-path assets; overuse steals bandwidth from the critical path —
  measure before and after *(AX-18)*.
- **Compression (gzip/brotli)** *(added)* — compress text responses at the edge and precompress
  static assets, but never compress secrets alongside attacker-controlled input in one response
  (BREACH-class leaks).
- **SEO mechanics under CSR vs SSR** — if organic search or link unfurling matters, client-only
  rendering is a business risk: crawlers see empty shells — SSR or prerender those routes and
  verify with fetch-as-bot evidence *(AX-18)*.
