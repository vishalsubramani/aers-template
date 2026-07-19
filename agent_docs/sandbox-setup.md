# Sandbox Setup

Full autonomy requires an ephemeral workspace, no production credentials, deny-by-default egress, no host
Docker socket, no cloud metadata access, no shared SSH agent, minimal filesystem mounts, resource limits,
and an immutable base image. Merely detecting that execution occurs "in a container" is insufficient.

Author verification fails closed when it cannot prove network isolation. Local development may request a
clearly marked degraded report, but degraded evidence cannot become `VERIFIED`.
