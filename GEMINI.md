# Gemini adapter

Follow `AGENTS.md` and `.agents/` as the canonical repository contract. Keep this file a thin adapter.
Map Gemini tool permissions and lifecycle hooks to `.agents/policies/` without creating a competing
source of truth. Local completion is `AUTHOR_READY`, never `VERIFIED`.
