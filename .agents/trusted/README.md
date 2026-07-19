# External Trusted Components

This directory contains contracts and examples only. Production implementations must live outside the
author agent's writable trust domain.

Required external components:
- private verifier image/workflow and hidden checks
- signing/attestation identity
- immutable evidence store
- release controller and credentials
- memory curator approval identity
- private evaluation holdouts

Do not mistake a file labeled "trusted" inside the same writable repository for a trust boundary.
