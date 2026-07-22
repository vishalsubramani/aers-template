# Grounding — Runtime: concurrency, memory & OS literacy

Part of the grounding library (`agent_docs/grounding/README.md`). Doctrine and ADRs are law;
this file is awareness. Cited IDs (AX/DD/PAT/DF) point at `.agents/doctrine/`.

**Load when:** designing or reviewing concurrent code, choosing threads vs async vs processes,
sizing pools or container limits, writing shutdown/signal handling, debugging leaks, hangs, or
tail latency, or scheduling background/cron work.
**Doctrine hooks:** AX-01, AX-09, AX-10, AX-11, AX-12, AX-14, AX-18, AX-22, PAT-05, PAT-07,
PAT-09, PAT-13, PAT-15, PAT-16, PAT-20, DD-16, DF-03

## Design checklist

- [ ] Who owns each piece of mutable shared state — a lock, an actor, a single writer, or the
      database — and is it written down? *(AX-12)*
- [ ] Is each workload CPU-bound or IO-bound, and do the pool/worker model and its sizing match?
- [ ] Does every blocking wait have a timeout and a cancellation path that actually propagates?
      *(AX-09, PAT-05)*
- [ ] What is bounded — queues, caches, listener sets, connections, spawned tasks? Anything
      unbounded is a leak or an overload amplifier. *(PAT-20, PAT-09)*
- [ ] What happens on SIGTERM — does the process drain and exit within the orchestrator's grace
      window, and are exit codes meaningful? *(AX-11)*
- [ ] Are container/cgroup memory, CPU, and FD limits known, and is the runtime configured to
      respect them rather than discover them via OOM kill?
- [ ] Where the contract says "durable," is the write actually fsync'd, not just in the page
      cache?
- [ ] Is any performance claim backed by a profile or flame graph from a warmed-up process?
      *(AX-18)*
- [ ] Do scheduled jobs survive overlap, missed runs, and DST — locked or idempotent, UTC,
      alerted? *(AX-10, PAT-07)*

## Concurrency & parallelism

- **Concurrency is not parallelism** — concurrency structures overlapping waits; parallelism
  needs extra cores. A single-threaded async service still saturates one CPU — restructuring
  alone buys no speedup for CPU-bound work. *(AX-18)*
- **Processes vs threads vs coroutines** — pick the simplest isolation that works: processes
  isolate faults and memory; threads share memory (and its bugs); coroutines are cheap but
  reshape the whole call stack. *(AX-01, AX-12)*
- **Context-switch cost** — thousands of OS threads thrash on switches and stack memory; beyond
  roughly a thousand concurrent waits, use an event loop or virtual threads instead.
- **Event loops & non-blocking IO** — one blocking call on the loop stalls every request; review
  for sync file IO, CPU-heavy work, and hidden blocking DNS/crypto calls on the loop thread.
- **async/await; promises/futures; callbacks** — async is viral and two-colors the codebase; a
  forgotten `await` silently drops errors and ordering. Choose sync or async per service
  boundary, deliberately. *(DF-03, AX-11)*
- **Green threads / virtual threads** — blocking-style code at event-loop cost, but pinning
  (native calls, monitors) can freeze carriers, and they don't excuse unbounded task counts.
  *(PAT-20)*
- **Goroutines & channels (CSP)** — every spawned goroutine needs a written exit story; blocked
  sends/receives nobody completes are the canonical leak, and an unbuffered-by-default channel
  design hides an unbounded queue decision.
- **Actor model (Erlang/Akka)** — mailboxes give one-owner state for free *(AX-12)*, but they
  are queues: ask what bounds them and what happens when an actor dies mid-message. *(PAT-20)*
- **Shared memory vs message passing** — default to immutability and message passing; share
  mutable memory only inside one declared owner. *(AX-12)*
- **Mutexes, semaphores, condition variables, barriers** — keep critical sections tiny and never
  do IO under a lock; condition-variable wait discipline lives in 02's Monitor Object entry.
- **Read–write locks** — pattern trade-offs in 02's Read–Write Lock; the runtime gotcha is the
  upgrade path — taking read then write deadlocks, so take the write lock up front if you might
  write. *(AX-12)*
- **Atomics & compare-and-swap** — fine for single-word flags and counters; two atomics composed
  are not atomic. Reach for them only after a lock is a measured bottleneck. *(AX-18)*
- **The ABA problem** — CAS reports "unchanged" when a value changed and changed back; recycled
  pointers need tags/epochs — one more reason not to hand-roll lock-free code.
- **Lock-free & wait-free structures** — use a vetted library implementation or a lock;
  hand-rolled lock-free code is unreviewable and its bugs are unreproducible. *(AX-01)*
- **Memory models & happens-before** — without a synchronization edge, another thread may see
  stale or half-constructed values regardless of source order; establish happens-before with
  locks/atomics, never with `sleep`.
- **Memory barriers** — implicit in locks and atomics; an explicit fence in application code is
  a red flag demanding a proof and a comment.
- **False sharing & cache lines** — independent hot counters on one cache line serialize cores;
  pad or shard per-thread state — but only after a profile shows it. *(AX-18)*
- **Race conditions vs data races** — not the same: data races (unsynchronized access) are
  undefined behavior even when "benign"; race conditions (bad interleavings, check-then-act)
  survive full synchronization — make the check-and-act one atomic step. *(AX-12)*
- **Deadlocks** — application mutexes and database row locks form one wait graph: the global
  acquisition order must span both (04 covers the database side). *(AX-12, DD-16)*
- **Livelock & starvation** — retry loops can spin forever making no progress; add jittered
  backoff, and check whether one work class can starve another under contention. *(PAT-05)*
- **Priority inversion** — a low-priority holder blocks a high-priority waiter; suspect it
  wherever priorities meet a shared lock in a hot path.
- **Thread safety & reentrancy** — document every shared type as thread-safe or not;
  thread-safe is not callback-reentrant — user callbacks invoked under your lock deadlock when
  they call back in.
- **Thread pool sizing** — CPU-bound: about core count; IO-bound: cores × (1 + wait/compute);
  separate pools per workload class so slow IO can't starve fast work, and bound the queue.
  *(PAT-20)*
- **Work stealing** — excellent for many small CPU tasks; blocking inside a work-stealing pool
  starves the entire runtime — keep blocking work on a dedicated executor.
- **Structured concurrency & cancellation propagation** — spawn children in a scope that awaits
  and cancels them; fire-and-forget tasks are leaks with worse stack traces, and every await
  needs a timeout/cancellation path. *(AX-09)*
- **The GIL** — Python threads never parallelize CPU-bound work; use processes or native
  extensions for CPU, threads/async only for IO.
- **Thread-local storage** — silently wrong when work hops threads (pools, async); prefer
  explicit context passing, and treat TLS in long-lived pools as a hidden-global leak risk.

## Memory & runtimes

- **Stack vs heap** — stack allocation is near-free and self-cleaning but finite: unbounded
  recursion is a crash — give recursive algorithms an explicit depth limit or make them
  iterative.
- **Value vs reference semantics** — know per language whether assignment copies or aliases;
  aliased mutable defaults (mutable default args, shared slices/maps) are classic corruption
  sources. *(AX-12)*
- **Memory leaks in GC languages** — GC only frees the unreachable: event listeners, closures
  capturing large scopes, and unbounded caches leak forever — every cache gets a size bound and
  eviction. *(PAT-09)*
- **Garbage collection (mark-sweep, generational, concurrent)** — GC pauses are a tail-latency
  source; before tuning collector flags, reduce allocation rate and heap pressure — with a
  measurement on both sides. *(AX-18, AX-22)*
- **Reference counting & cycles** — refcounting leaks cycles (parent↔child); break them with
  weak references, and don't rely on deterministic destruction timing in hybrid collectors.
- **Weak references** — right for caches and observer lists that must not extend lifetimes;
  wrong unless the entry vanishing mid-use is handled.
- **RAII; ownership & borrowing** — tie resource lifetime to scope (`defer`/`with`/`using`/
  `Drop`); any manually paired acquire/release in review is a leak waiting on the early-return
  path.
- **Use-after-free, double free, buffer overflows** — in unsafe languages these are exploits,
  not just crashes; run sanitizers in CI and treat every `unsafe`/FFI block as a security
  review surface.
- **Fragmentation; arena allocation; object pools** — long-lived processes grow with a flat
  live-set via fragmentation; arenas and pools fix hot allocation paths, but only with profile
  evidence. *(AX-18)*
- **JIT vs AOT; warmup** — JIT runtimes are slow for the first N requests: warm up before
  benchmarking, and gate readiness so cold instances don't take full traffic on deploy or
  scale-out. *(PAT-15, AX-18)*
- **Escape analysis** — the compiler stack-allocates what provably doesn't escape; hand
  "optimizations" (extra indirection, captured closures) can defeat it — measure, don't guess.
  *(AX-18)*
- **Profiling (CPU, allocations, heap dumps)** — the profile decides, intuition doesn't; find
  growth by diffing two heap snapshots over time, not by staring at one. *(AX-18)*
- **Flame graphs** — the default artifact for "where does the time go": width is cost; use
  differential flame graphs to prove a fix moved the needle. *(AX-18)*
- **The OOM killer** — the kernel SIGKILLs your process with no cleanup (exit 137); set runtime
  heap limits below the container limit and alert on kill events. *(AX-14)*
- **File-descriptor & connection leaks** — "too many open files" surfaces far from the leak:
  close in `finally`/`defer`, pool connections with hard limits, and graph FD counts as a
  standing metric. *(AX-14, PAT-13)*

## OS & systems literacy

- **Syscalls; user space vs kernel space** — the syscall boundary is the expensive one: chatty
  unbuffered reads/writes are a hidden tax — batch and buffer; `strace` shows what a process
  actually asks the kernel.
- **Everything is a file; file descriptors; pipes** — sockets, pipes, and devices all consume
  the FD limit; a full pipe blocks the writer — undrained subprocess stdout is a classic hang.
- **Signals (SIGTERM vs SIGKILL; PID 1; zombies)** — handle SIGTERM by draining within the
  orchestrator's grace window; SIGKILL is unhandleable. As PID 1 in a container, forward
  signals and reap children or accumulate zombies.
- **Exit codes** — zero is the only success; 128+N means death by signal N (137 = SIGKILL/OOM).
  Automation and scripts must check codes and fail loudly. *(AX-11)*
- **fork/exec; copy-on-write** — forking a large-heap process is cheap until pages are written
  (or a GC touches them); fork-without-exec in threaded runtimes deadlocks — prefer
  spawn/posix_spawn.
- **Virtual memory, paging, swap, page cache** — memory stats lie: "free" memory is mostly page
  cache, and a swapping service has already blown its latency SLO — alert on paging activity,
  not memory percent. *(AX-22)*
- **mmap** — page faults are invisible IO: latency appears with no syscall in traces; mmap-heavy
  stores interact badly with cgroup memory pressure.
- **Blocking vs non-blocking IO; epoll/kqueue/io_uring** — thread-per-connection dies around
  10k sockets; build on a runtime that wraps these primitives rather than coding to them
  directly. *(AX-01)*
- **fsync and what "durable" means** — a completed `write()` sits in the page cache; durability
  requires fsync, and rename-based atomic writes need the directory fsync'd too — verify your
  storage layer actually syncs where the contract says "durable."
- **IOPS vs throughput; random vs sequential IO** — cloud disks cap IOPS separately from MB/s:
  many small random reads exhaust IOPS while throughput looks idle — batch or fix the access
  pattern before buying bigger disks. *(AX-18)*
- **inodes; hard links vs symlinks** — disks fail "full" with free bytes when small files
  exhaust inodes; symlinks are path-traversal hazards — any path or scope check must resolve
  them first.
- **cgroups & namespaces** — containers are processes with limits, not VMs: runtimes that read
  host CPU/memory counts mis-size pools and heaps — configure container-aware limits
  explicitly. *(PAT-16)*
- **ulimits** — default FD/process limits are low; a service opening sockets at scale raises
  them and asserts the limit at startup rather than discovering it in an incident. *(PAT-16)*
- **Load average** — it counts runnable plus uninterruptible (IO-waiting) tasks, not CPU
  percent; load far above cores with idle CPU means IO or lock contention — check iowait before
  blaming CPU.
- **NUMA & CPU affinity** — cross-socket memory access and cache-hostile migrations matter on
  large boxes only; a tuning knob for databases and latency-critical services, never a default.
  *(AX-18)*
- **strace, tcpdump, ss, htop as reflexes** — observe before hypothesizing: what is it
  syscalling, what's on the wire, what state are its sockets in, what's eating CPU and memory.
  *(AX-18)*
- **Cron jobs** — assume any run can overlap, be skipped, or fire strangely across DST: lock or
  make idempotent, schedule in UTC, alert on missed runs — this is why distributed schedulers
  exist. *(AX-10, PAT-07)*
- **Log rotation** — unrotated logs fill disks and take the node down, and a deleted-but-open
  file frees nothing; log to stdout and let the platform rotate, or reopen on rotation signals.
  *(PAT-13)*
