# Grounding — AI & LLM engineering

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing anything that calls an LLM — prompts, RAG pipelines, agent
tools, evals, model selection or routing, streaming endpoints, or LLM cost/observability work
**Doctrine hooks:** AX-06, AX-08, AX-09, AX-11, AX-13, AX-14, AX-15, AX-16, AX-18, AX-21, PAT-01,
PAT-05, PAT-08, PAT-09, PAT-13, PAT-17, PAT-20, DD-14, DD-17, DF-02, DF-04

## Design checklist

- [ ] What is the context/token budget per request, and what drops first when it overflows?
- [ ] Is every model output parsed and validated at the boundary before it touches state or
      triggers an action (PAT-01, AX-08)?
- [ ] Which tools can the model invoke, at what privilege, and which actions require a human
      (PAT-17)?
- [ ] What untrusted content reaches the prompt, and how is injection contained?
- [ ] Does a versioned golden eval suite gate every prompt or model change (AX-16)?
- [ ] How do tests absorb non-determinism — property and schema assertions, not exact strings
      (AX-16)?
- [ ] What happens on a provider 429 or outage — timeout, bounded retry, fallback model, or
      documented degraded mode (AX-09, PAT-05, PAT-08)?
- [ ] Are prompts and exact model versions pinned, versioned, and rolled back with the code
      (AX-06, AX-15)?
- [ ] Is PII redacted before prompts leave the trust boundary and before traces are written
      (DD-14, PAT-13)?
- [ ] Is every RAG/vector index a rebuildable projection with a pinned embedding model version
      (DD-17)?
- [ ] Is cost per interaction traced and budgeted, with caching and routing weighed (AX-14,
      AX-18)?

## Context and prompting

- **Context window budgeting** — treat context as a hard per-request budget: rank inputs and
  decide what drops first; silent tail truncation of instructions or evidence is a correctness
  bug, not graceful degradation.
- **Prompt caching** — order prompts stable-prefix-first (system, tools, reference docs before
  volatile turns) or cache hits vanish; it is still a cache — name its invalidation and staleness
  story *(PAT-09, AX-18)*.
- **Prompt versioning & management** — prompts are behavior: keep them in the repo, review diffs,
  and pin the prompt+model pair per release so rollback restores both together *(AX-06, AX-15)*.
- **Structured outputs & schema enforcement** — request schema-constrained output and still
  validate: model output is untrusted external input, parsed into typed structures at the edge
  before anything interior trusts it *(PAT-01, AX-08)*.
- **Tool / function calling design** — few, narrow, intention-revealing tools with typed
  parameters beat one generic executor; every tool is both public interface and attack surface,
  so export the minimum *(AX-05, PAT-17)*.
- **Truncation & max-output handling** — check the finish/stop reason on every call; truncated
  JSON or a half-emitted plan parsed as success is silent corruption, and errors belong in the
  interface *(AX-11)*.

## Retrieval and grounding (RAG)

- **Chunking & embedding models** — chunk along semantic structure with overlap and tune size via
  retrieval evals; pin the embedding model version — changing it invalidates the entire index
  *(DD-17)*.
- **Hybrid search & reranking** — dense embeddings miss exact identifiers, codes, and names;
  combine with keyword/BM25 and rerank the union. Retrieval quality, not the generator, is the
  usual RAG failure to debug first *(AX-18)*.
- **Citation grounding** — require answers to cite retrieved passages and mechanically verify the
  citations exist; claims without a source default to "not found," never to model recall.
- **Vector index tradeoffs** — ANN indexes trade recall against latency, memory, and cost:
  measure recall@k on your own data before choosing, and keep the index a rebuildable projection
  of source documents *(DF-02, DD-17)*.
- **Hallucination mitigation & grounding** — assume fluent-but-wrong by default: constrain
  answers to supplied evidence, make "I don't know" a valid output, and route high-stakes claims
  through retrieval or a verifier step.

## Evals and testing

- **Evals: golden datasets & regression suites** — every prompt, model, or retrieval change runs
  against a versioned golden set in CI; without one, prompt tweaks are unreviewed behavior
  changes shipped blind *(AX-16)*.
- **LLM-as-judge caveats** — judges drift, favor their own model family and verbose style, and
  are position-sensitive; calibrate against human labels, randomize candidate order, and never
  let a judge grade its own outputs unchecked.
- **Non-determinism (temperature, seeds)** — pin temperature 0 and seeds where supported, but
  still write tests that assert properties and schemas rather than exact strings; exact-match LLM
  tests are flakes waiting to fire *(AX-16)*.
- **Guardrails & output validation** — layer cheap deterministic checks (schema, allowlists,
  length and policy filters) around the model; a guardrail is code at the boundary, not another
  prompt asking the model to behave *(PAT-01)*.

## Security and privacy

- **Prompt injection defense** — anything the model reads (docs, tool output, web content) can
  steer it; segregate instructions from data, treat retrieved text as untrusted, and never derive
  privileges or policy from model output.
- **Least-privilege tool access & human-in-the-loop** — grant each agent the minimum tool scope
  its task needs, deny by default, and require human confirmation before irreversible or
  externally visible actions *(PAT-17, AX-15)*.
- **Data privacy in prompts; PII redaction** — prompts flow to third parties, logs, and traces:
  classify fields at design time, redact PII before sending and before tracing, and verify
  provider retention/training terms *(DD-14, PAT-13)*.

## Cost, routing, and model choice

- **Model routing (cheap-first)** — default traffic to the cheapest model that passes evals and
  escalate on complexity or confidence signals; routes are configuration, and each route needs
  its own eval gate *(AX-13, AX-18)*.
- **Fine-tuning vs RAG vs prompting** — try prompting first; add RAG when knowledge is dynamic or
  needs citations; fine-tune only for style/format/latency after evals prove prompting
  insufficient — it is the least reversible option *(DF-04, AX-17)*.
- **Fallback models & provider redundancy** — providers have incidents and deprecations: define a
  fallback model or provider with its own passing evals, or a documented degraded mode — not a
  hard 500 *(AX-09, PAT-08)*.
- **429s, rate limits & token buckets** — you are now the client on your own list: honor
  retry-after, bound retries with backoff and jitter, budget tokens-per-minute client-side, and
  shed or queue at admission instead of hammering *(PAT-05, PAT-20)*.
- **Model/version pinning & upgrade canaries** — pin exact model versions; provider "same-model"
  updates shift behavior, so upgrades go through evals and staged rollout like any dependency
  bump *(AX-21, AX-15)*.

## Operations and agent patterns

- **Streaming UX & partial results** — stream for perceived latency, but never act on partial
  output: plan for mid-stream failure with clean retry/recovery, and validate only the completed
  message *(AX-09)*.
- **LLM observability: tracing prompts, cost per interaction** — trace every call with prompt and
  model version, token counts, latency, outcome, and cost — PII-redacted; per-interaction cost is
  a first-class metric, not a monthly invoice surprise *(AX-14, PAT-13, DD-14)*.
- **Agent patterns: planner–executor, reflection, tool protocols (MCP)** — separate planning from
  execution so tools stay narrow; cap reflection loops with iteration and cost budgets; treat
  tool protocols (MCP) as versioned contracts, not bespoke glue *(AX-06)*.
