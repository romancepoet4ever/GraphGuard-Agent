# Current static-check and build gates

Date: 2026-10-30 (Asia/Tokyo)

| Repository/scope | Command family | Result | Boundary |
| --- | --- | --- | --- |
| GraphGuard-Agent Python | `ruff check src api sdk/python/graphguard tests evaluation` with generated/result/build exclusions | **FAIL: 384 findings** | Existing repository-wide debt; do not claim an all-project Ruff pass |
| GraphGuard-Agent web console | `npm run build` | PASS | Vite built 3,543 modules; large-bundle warning (~1.43 MB JS) remains |
| interrogation backend | `ruff check app src tests` | **FAIL: 699 findings** | Dominant categories include UP006, I001, BLE001, UP035 and UP037 |
| interrogation frontend | `npm run lint` | PASS | Frontend lint only |
| interrogation frontend | `npm run build` | PASS | Vite built 3,010 modules; >500 kB chunk warning remains |
| 下游气象应用 Python | `ruff check .` | PASS | Current full repository scope |
| 下游气象应用 web | `tsc --noEmit --incremental false` | PASS | One strict cast in a pre-existing untracked capture spec was minimally corrected to `as unknown as ...` before the passing rerun |
| 下游气象应用 web | Next.js 15.5.22 production build | PASS | Static pages generated; generated `next-env.d.ts` was restored to its prior tracked content |

The Vite sandbox attempts encountered Windows realpath restrictions and were rerun outside that restriction. The rows above are current terminal-observed gate results, not historical V3 log claims.
