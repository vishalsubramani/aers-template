"""AERS assurance layer — additive, non-control-plane verification tooling.

This package is deliberately OUTSIDE the protected control-plane surface
(`scripts/aers/**`). It reuses the existing engine read-only and adds the
external-verifier protocol, adversarial benchmark, compliance assessment,
assurance case, isolation truth model, structured threat model, and
evaluator-health suite. It never issues VERIFIED and never mutates policies,
hooks, schemas, or contracts.
"""
