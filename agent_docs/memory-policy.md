# Memory Policy

Memory is not a scratchpad that becomes truth. Working notes and run traces remain external and expire.
A durable lesson moves through `proposal → quarantine → independent reproduction → regression eval → curator
approval → signed activation → review/expiry`. Most tasks should create no durable lesson. Never free-rewrite
`AGENTS.md`; propose small attributable deltas.

Activation is what makes a lesson reachable: context packets recall active records by deterministic scope
association (glob intersection with the task's write scope, plus one hop through `links`), capped and
fail-closed on hash or status mismatch. Write lessons with recall in mind: a tight `scope` puts the lesson
in front of exactly the future tasks it should influence; `links` connect related lessons so they surface
together.
