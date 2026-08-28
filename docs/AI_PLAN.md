# План работы ИИ

## Текущая цель

Реализовать `FS-014` как самостоятельный диагностический vertical slice: безопасно подготовленный
binary raster проходит через явно выбранный thinning backend, возвращает same-sized immutable
skeleton с provenance и доступен через preview/export без graph/routing из будущих stages.

## Активный stage

- Stage ID: `FS-014`
- Lifecycle: `completed`; validated locally, not merged/pushed.
- Branch: `feature/fs-014-skeletonization`.
- Authorization: пользователь явно разрешил продолжение 2026-08-29.
- DAG: `FS-013 → FS-014`; prerequisite `FS-013` completed, validated и committed в `e918761`.
- Integration boundary: ветка построена поверх ещё не слитого `FS-013`; `main` и `origin/main`
  остаются на `c13f74d`, merge/push/PR не выполняются без отдельного разрешения.

## Reviewed algorithm/dependency

- Primary: `scikit-image 0.26.x`, explicit `skimage.morphology.skeletonize(..., method="lee")`.
- Причина explicit Lee: official API поддерживает Lee для 2D и обещает single-pixel-wide skeleton;
  default 2D Zhang не выбран из-за открытого upstream defect для некоторых dense masks в 0.26.0.
- Backend возвращает bool array, application adapter валидирует shape/dtype/subset и преобразует его
  в существующий immutable binary `RasterImage`.
- Automatic algorithm/backend fallback отсутствует; unavailable/malformed backend fail closed с
  typed privacy-safe failure и explicit provenance.

## Runnable vertical slice

- Entry: пользователь запускает documented skeleton CLI с локальным PNG/JPEG line-art input.
- Path: FS-010 safe decode/preprocessing → binary raster → explicit Lee thinning → typed result →
  atomic binary PNG export и actual source/skeleton preview.
- Observable result: same-sized one-pixel skeleton, source/skeleton pixel counts, algorithm/backend
  и output basename без full path/pixel payload; empty foreground остаётся успешным empty result.

## Scope и invariants

- Typed skeleton result/failure/provenance и lazy scikit-image adapter.
- Source dimensions и binary semantics сохраняются; source не мутируется, output foreground не
  выходит за source foreground.
- Line/T/cross/loop/noise fixtures проверяют topology-preserving properties без brittle full-image
  snapshot как единственного oracle.
- Preview/export используют существующие localization и transactional path boundaries.
- Cancellation cooperative: проверяется до/после backend call; cancelled/stale result не
  публикуется как complete, retry только explicit.
- Existing image limits сохраняются; новый backend не получает unchecked dimensions.
- Skeleton foreground дополнительно ограничен 4 000 000 pixels; malformed backend output с wrong
  dtype/shape/subset либо solid `2×2` block отклоняется до publication.

## Non-goals / deferred

- Graph nodes, endpoints/junction degree и component topology — `FS-015`.
- Multiple components, PiecewiseCurve и routing — `FS-016`–`FS-017`.
- PySide6 shell и measured hard cancellation latency — `FS-021`/`FS-023`.
- Automatic Zhang/OpenCV/project-owned fallback запрещён.

## PASS evidence / DoD

- Unit/property tests: typed contracts, source immutability, shape/subset, line/T/cross/loop/noise,
  empty/cancel/unavailable/malformed backend и no-fallback semantics.
- Integration: real PNG/JPEG → FS-010 binary → actual scikit-image Lee → typed skeleton/export.
- Component: actual Matplotlib/Agg preview и cancel/late-result suppression.
- Live E2E: documented CLI создаёт readable skeleton PNG и preview; corrupt/existing-output/backend
  failures не теряют data и не раскрывают full path.
- Full pytest, Ruff, strict mypy, frozen clean restore, dependency/overlay/diff gates PASS.
- Completion Documentation Synchronization Gate и independent reviewer выполнены до terminal claim.

Фактическое evidence: 40 targeted unit/integration/component/live E2E tests и 427 repository tests
PASS; frozen sync, Ruff, strict mypy, overlay и diff gates PASS; correctness/security re-reviews GO.

## Handoff

FS-014 завершён локально. После atomic commit остановиться перед `FS-015`: этот следующий stage
planned, но не активирован. Merge/push/PR/release не выполнять без отдельного разрешения пользователя.
