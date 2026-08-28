# План работы ИИ

## Текущая цель

Реализовать Stage `FS-011`: получить два явно разных edge intermediate — project-owned boundary
бинарной маски и OpenCV Canny — с typed parameters/provenance и diagnostic export. Lifecycle:
`in_progress`.

## Связанные требования

- SPEC: `specs/system.spec.md`, `specs/features/image-to-curve.spec.md`.
- IDs: FR-IMPORT-001, IM-FR-002, IM-FR-003, IM-AC-002, AC-SYS-006, AC-SYS-010.
- Stage contract: `prompts/STAGES.md`, heading `FS-011`.

## Stage identity и dependency DAG

- Stage ID: `FS-011`.
- Completed prerequisite: FS-010 implementation `d63b1b0`, full 254 tests and security-review GO.
- DAG: `FS-010 → FS-011`; no cycle/forward dependency.
- Entry gate: satisfied; typed grayscale/binary FS-010 contracts committed, OpenCV 5.0 Canny API
  and `opencv-python-headless` 5.0.0.93 Windows/Python/license metadata reviewed from official
  sources, current lockfile is clean.

## Runnable vertical slice и live product scenario

- Entry: user supplies an FS-010-valid local PNG/JPEG and selects `threshold_boundary` or `canny`.
- Path: safe preprocessing → selected edge algorithm → immutable edge raster/provenance → named
  diagnostic PNG export.
- Observable result: binary edge map with dimensions, algorithm/backend and exact parameters, or
  explicit typed failure; no contour is created or implied.

## Scope / non-goals / invariants

- Scope: deterministic binary-mask boundary, OpenCV Canny on grayscale, validated low/high/
  aperture/L2 parameters, typed result/provenance, CLI selection and preview/export evidence.
- Non-goals: contour extraction/order FS-012, skeletonization, routing or quality superiority claim.
- Both algorithms consume immutable FS-010 rasters and return same-sized binary `RasterImage`
  without mutating source.
- `threshold_boundary` and Canny are not equivalent; selected algorithm/backend is always visible.
- Missing/failing OpenCV makes only Canny unavailable; no automatic substitution with threshold
  boundary and no retry of deterministic backend failure.
- Empty edge map is a valid complete diagnostic result, not fabricated contour or failure.

## Рабочие задачи

| № | Задача | Статус |
|---|---|---|
| 1 | Confirm FS-010 evidence and review OpenCV Canny/headless/license contracts | completed |
| 2 | Add bounded headless OpenCV dependency and typed edge contracts | in_progress |
| 3 | Implement threshold-boundary and explicit Canny adapter | pending |
| 4 | Extend diagnostic CLI/export without contour claims | pending |
| 5 | Add synthetic unit/integration/component/E2E and unavailable-backend evidence | pending |
| 6 | Run full/static/frozen/overlay/security-review gates and synchronize docs | pending |

## Acceptance / PASS

- [ ] Synthetic line/rectangle fixtures give deterministic same-sized binary outputs for both
  selected modes; source rasters remain unchanged.
- [ ] Threshold-boundary connectivity and Canny low/high/aperture/L2 semantics are validated and
  recorded; invalid values/backend errors fail typed.
- [ ] Empty edge map is represented explicitly; no API/CLI/result claims contour extraction.
- [ ] Canny unavailable never falls back to threshold-boundary and the separate mode still works.
- [ ] Unit/integration/component/E2E, full/static/frozen/overlay and security review gates pass.

## Deferred

- Dominant contour conversion (`FS-012`) and all skeleton/routing behavior.

## Условие завершения

После terminal evidence FS-011 остановиться перед FS-012: пользователь авторизовал только текущие
пять этапов. Merge/push/PR выполняются только по отдельному разрешению пользователя.
