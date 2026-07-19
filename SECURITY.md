# Security Policy

Report vulnerabilities through the organization's private security channel. Never place credentials,
customer data, exploit details, or private evaluator content in public issues.

## Agent threat model

Assume the agent can be induced to pursue task completion against policy, that every input can contain
prompt injection, and that repository-local checks can be modified or gamed if writable. Security is
therefore enforced with least privilege, isolation, scoped identities, egress denial, protected paths,
external verification, immutable evidence, and limited authority.

A session may autonomously hold at most two of these capabilities:
1. Read untrusted input
2. Access sensitive data or systems
3. Cause external state change or exfiltration

Tasks requiring all three must be decomposed into separate trust domains or safe-stopped.
