# Grounding — Algorithms & CS foundations

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** choosing a data structure or algorithm for a hot path, reviewing
performance-sensitive or input-processing code (parsers, regex, hashing, sorting), sizing
caches/indexes/limits, or designing anything that streams, samples, shards, or rate-limits.
**Doctrine hooks:** AX-01, AX-16, AX-18, AX-19, AX-21, PAT-01, PAT-09, PAT-20, DF-02, DF-04, DD-17

## Design checklist

- [ ] Is the hot path's complexity stated and measured at realistic sizes, not assumed from
      Big-O? *(AX-18)*
- [ ] Could the stdlib or an existing dependency replace this hand-rolled algorithm? *(AX-21, DF-04)*
- [ ] Where can untrusted input force worst-case behavior — hash collisions, regex backtracking,
      recursion depth, adversarial sort order? *(PAT-01)*
- [ ] Is every collection, queue, and cache bounded, with defined behavior at the bound? *(PAT-20)*
- [ ] Where output order is user-visible, is sort stability required and the tiebreaker explicit?
- [ ] If approximate answers (sketches, sampling) are used, is the error bound part of the
      contract consumers see? *(AX-06)*
- [ ] What happens when the data outgrows memory — streaming/external variant, spill, or an
      explicit stated limit?
- [ ] Are boundary conditions (empty, one element, off-by-one edges, duplicates) covered by
      tests? *(AX-16)*
- [ ] If precomputation or caching trades memory for time, who owns invalidation? *(PAT-09, DD-17)*

## Complexity and memory

- **Big-O and amortized analysis** — asymptotics hide constants and amortized spikes: one O(n)
  resize inside an "O(1)" append can blow a latency SLO; measure at realistic n before
  optimizing *(AX-18, AX-22)*.
- **Space–time tradeoffs** — precomputation and caching buy latency with memory plus an
  invalidation liability; name the source of truth and staleness bound before trading
  *(PAT-09, DD-17)*.
- **Arrays vs linked lists** — cache locality makes contiguous arrays win most real benchmarks
  despite equal Big-O; a pointer-chasing structure needs a measured justification, not a
  textbook one *(AX-18, AX-01)*.

## Core data structures

- **Hash tables** — attacker-chosen keys degrade to O(n) via collisions (use a seeded/SipHash
  map for untrusted keys), and a load-factor-triggered resize mid-request is a latency spike —
  pre-size known workloads *(PAT-01)*.
- **Balanced trees (BST, red-black/AVL)** — justified only when you need ordered iteration or
  range queries with guaranteed bounds; otherwise a hash map or sorted array is simpler and
  faster *(AX-01)*.
- **B-tree/B+tree** — databases love them because fan-out matches page/IO size; this is why
  index key order and random-UUID primary keys govern write amplification and range-scan cost
  *(DF-02, DD-04)*.
- **Heaps & priority queues** — the default for top-K, schedulers, and timer wheels; arbitrary
  update/removal is not O(log n) unless you also maintain a position index or use lazy deletion.
- **Tries** — the move for shared-prefix key sets (autocomplete, routing tables, IP longest-prefix
  match); per-node overhead is the trap — reach for compressed/radix variants first.
- **Skip lists** — probabilistic stand-in for balanced trees that is far simpler under
  concurrency (Redis sorted sets); expect equal asymptotics but worse cache behavior than
  arrays *(AX-01)*.

## Graphs

- **BFS/DFS** — BFS gives shortest hop counts at frontier-memory cost; recursive DFS overflows
  on deep graphs, so write it iteratively — and without a visited set, any cycle loops forever.
- **Topological sort** — the default for dependency ordering (builds, migrations, DAG jobs);
  "no valid order exists" doubles as your cycle detector *(AX-04)*.
- **Dijkstra and A*** — Dijkstra silently breaks on negative edge weights; A* is Dijkstra plus
  an admissible heuristic, and an inadmissible heuristic returns wrong paths without erroring.
- **Union-find** — near-O(1) connectivity and grouping (dedupe clusters, partition detection)
  with path compression and union by rank; beats repeated traversal for incremental
  connectivity questions.

## Sorting and searching

- **Sorting (quicksort, mergesort, heapsort, Timsort) and stability** — use the library sort:
  Timsort exploits existing runs and is stable; quicksort's O(n²) on adversarial input matters
  for untrusted data; multi-key ordering needs stability stated *(AX-21)*.
- **Binary search** — the off-by-one graveyard: pin the invariant (lower vs upper bound), mind
  midpoint overflow, and verify the data is actually sorted; prefer stdlib bisect over
  hand-rolling *(AX-21, AX-16)*.

## Algorithmic techniques

- **Two pointers, sliding window, prefix sums** — turn O(n²) subarray and range scans into O(n)
  or O(1)-per-query; prefix sums are the default for repeated range aggregations over static data.
- **Recursion, stack depth, tail calls** — mainstream runtimes do not guarantee tail-call
  elimination; input-driven depth (parsers, tree walks) is a crash/DoS vector — use an explicit
  stack or depth cap *(PAT-01)*.
- **Dynamic programming: memoization vs tabulation** — memoize first (it mirrors the natural
  recursion); switch to tabulation to bound stack depth or shrink memory to a rolling window.
- **Greedy algorithms** — only correct with an exchange argument or matroid structure behind
  them; plausible greedy on scheduling/change-making returns quietly suboptimal answers — test
  against brute force on small inputs *(AX-16)*.
- **Backtracking** — exponential by default; viable only with aggressive pruning and good
  ordering, and it needs a hard time/node budget whenever the input is untrusted *(PAT-01)*.

## Strings and matching

- **String matching (KMP, Rabin–Karp)** — only past naive-search scale; Rabin–Karp's rolling
  hash fits multi-pattern search and content chunking, but hash hits must be verified to kill
  false positives.
- **Edit distance** — O(n·m) time and memory blows up on user-sized inputs (fuzzy match,
  diffing); band the distance or cap input length before exposing it to external data.
- **Regex engines: backtracking vs automata** — backtracking engines (PCRE, Python, JS) are
  ReDoS-prone on nested quantifiers; untrusted input wants an automata engine (RE2-class) or a
  hard match timeout *(PAT-01)*.

## Streaming and approximate algorithms

- **Bloom filters** — cheap "definitely absent" gate before an expensive lookup; false positives
  only, and no deletes without the counting variant — size for the target false-positive rate.
- **Count-min sketch, HyperLogLog** — bounded-memory frequency and cardinality estimates for
  streams; the error bound belongs in the consumer-facing contract, not a code comment *(AX-06)*.
- **Reservoir sampling** — uniform sample from a stream of unknown length in O(k) memory; the
  default for "sample the events/logs" without a second pass or a full count.
- **Top-K and streaming algorithms** — exact top-K needs full counts plus a heap; at scale use
  space-saving or sketch-backed approximations and label results approximate *(AX-06)*.
- **External sorting** — data bigger than RAM means chunked sort-merge; also the mental model
  for database spills — a huge ORDER BY without an index is an external sort you didn't plan
  *(DF-02)*.

## Applied structures in systems

- **Consistent hashing** — the default for spreading keys over a changing node set; `hash % n`
  reshuffles nearly everything on membership change — use virtual nodes to even out load.
- **Geospatial indexing (geohash, quadtrees, H3, R-trees)** — never hand-roll proximity search;
  use the database's spatial index *(DF-02, AX-21)*, and mind grid-cell adjacency gotchas at
  cell boundaries and poles.
- **Rate-limiter algorithms** — token bucket vs sliding window is a product choice (burst
  tolerance vs smoothness); state atomicity under concurrency and whether limits are per-node
  or global *(PAT-20)*.
- **LRU/LFU eviction** — every bounded cache needs a designed eviction policy; LRU is O(1) via
  hashmap-plus-list but scan-vulnerable — consider segmented or frequency-aware variants
  *(PAT-09)*.
