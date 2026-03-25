---
last_updated: 2026-03-24T18:02:21Z
---

# Team Wisdom

Reusable patterns and heuristics learned through work. NOT transcripts — each entry is a distilled, actionable insight.

## Patterns

<!-- Append entries below. Format: **Pattern:** description. **Context:** when it applies. -->

**Pattern:** Split early archive migrations into three seams: route-faithful transport helpers, legacy-specific typed parsing/helpers, and focused compatibility tests around both. **Context:** First delivery slices where backend names and payload quirks must stay stable while the SDK surface is still being layered. 
