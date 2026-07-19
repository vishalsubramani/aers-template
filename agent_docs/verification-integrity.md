# Verification Integrity

Verification runs against the exact candidate commit in a clean export or immutable image. The author cannot
write private tests, verifier configuration, evaluator thresholds, or signing policy. Public checks give useful
feedback but are not the entire oracle. A deterministic audit precedes any LLM reviewer. Auditor output is JSON
schema-validated; text matching is never an approval mechanism.

Private tests and signing identity belong in an external trust domain. Execute untrusted candidate code with
minimal privileges and expose only bounded results; otherwise the code may read or exfiltrate the oracle.
