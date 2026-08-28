# План работы ИИ

## Текущая цель

Реализовать Stage `FS-010`: безопасно принять локальный PNG/JPEG, применить EXIF orientation,
получить bounded grayscale/threshold intermediate и показать либо экспортировать диагностический
результат. Lifecycle: `in_progress`.

## Связанные требования

- SPEC: `specs/system.spec.md`.
- IDs: FR-IMPORT-001, SEC-INPUT-001, AC-SYS-006, AC-SYS-010, AC-SYS-012.
- Stage contract: `prompts/STAGES.md`, heading `FS-010`.

## Stage identity и dependency DAG

- Stage ID: `FS-010`.
- Completed prerequisite: FS-009 implementation `74f1008`, 215 tests and reviewer GO.
- DAG: `FS-009 → FS-010`; no cycle/forward dependency.
- Entry gate: satisfied; 25 MiB/40 MP policy exists in `docs/SECURITY.md`, Pillow 12.3.0
  format/security/API/license contracts reviewed from official sources, current lockfile is clean.

## Runnable vertical slice и live product scenario

- Entry: user supplies a local PNG/JPEG and explicit preprocessing options.
- Path: encoded-size check → allowlisted header decode → pixel-budget check → EXIF transpose →
  grayscale → optional bounded denoise/contrast → threshold/invert → preview/export.
- Observable result: typed raster intermediate with dimensions, format, transform provenance and
  pixel counts, or a controlled validation failure without payload logging.

## Scope / non-goals / invariants

- Scope: safe local PNG/JPEG decode, first-frame policy, EXIF orientation, grayscale, optional
  denoise/autocontrast, threshold/invert, typed result, diagnostic CLI/view and export safety.
- Non-goals: Canny/edge detection FS-011, contours FS-012, remote URLs, skeleton/routing.
- Encoded payload is capped at 25 MiB before decoder work; decoded dimensions are capped at 40 MP
  before `load()` and rechecked after orientation.
- Actual decoder format, not extension, must be PNG or JPEG; animated/multiframe input is rejected.
- Truncated/corrupt/spoofed input and invalid options fail explicitly; no decoder/algorithm retry or
  silent fallback; source bytes and payload are never logged.
- Existing output is never overwritten without an explicit flag.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Confirm FS-009 prerequisite and review Pillow/security/license contracts | completed |
| 2 | Add pinned Pillow dependency and typed raster/application boundaries | in_progress |
| 3 | Implement safe decode and deterministic preprocessing pipeline | pending |
| 4 | Add diagnostic CLI/preview and safe export | pending |
| 5 | Add unit/integration/component/E2E negative and success evidence | pending |
| 6 | Run full/static/frozen/overlay/security-review gates and synchronize docs | pending |

## Acceptance / PASS

- [ ] PNG/JPEG valid fixtures preserve oriented dimensions and deterministic grayscale/threshold.
- [ ] Encoded-size and decoded-pixel limits reject before unsafe work; actual format allowlist wins
  over extension and corrupt/truncated/multiframe inputs fail typed.
- [ ] Optional denoise, contrast, threshold and invert are independent and recorded in provenance.
- [ ] CLI preview/export completes a real local-file vertical slice without implicit overwrite.
- [ ] Unit/integration/component/E2E, full/static/frozen/overlay and security review gates pass.

## Deferred

- Threshold boundary/Canny (`FS-011`), contours (`FS-012`) and remote input.

## Условие завершения

После terminal evidence FS-010 активировать только FS-011 и не начинать FS-012. Merge/push/PR
выполняются только по отдельному разрешению пользователя.
