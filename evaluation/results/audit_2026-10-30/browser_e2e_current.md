# Browser E2E terminal capture summary

Date: 2026-10-30 (Asia/Tokyo)  
Repository: `下游气象应用` at `2026-10-30 批次`, tested with preserved untracked capture specs.  
Provider: local scripted test double.  
Spec: `apps/web/tests/graphguard-security.spec.ts` through `scripts/e2e.ps1`, using isolated Weather/Web/GraphGuard/mock ports documented in `下游气象应用/docs/TESTING.md`.

| Mode | Passed | Skipped | Failed | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Observe | 6 | 1 | 0 | One mode-inapplicable assertion skipped |
| Enforce | 7 | 0 | 0 | All seven mode assertions executed |
| Offline | 2 | 5 | 0 | Five online-only assertions skipped |

Skipped cases are not counted as passes. These are controlled browser integration results with a scripted provider; they do not validate production Qwen, Tianqing, network, or deployment infrastructure.

This file records the terminal-observed summary because Playwright's report directory is reused by each mode. The primary durable behavioral evidence remains the assertions/specification plus the mode-specific terminal result above; it is not a substitute for a raw immutable CI log.
