# Control-Plane Code Instructions

This directory is security-critical. Ordinary feature implementers may read but never modify it. Changes require
an approved R3 control-plane specification, independent ownership, adversarial tests, private eval comparison,
and activation in a later run. Preserve stdlib-only portability and fail-closed behavior. Never add a code path
that can issue `VERIFIED` locally.
