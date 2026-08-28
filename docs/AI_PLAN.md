# План работы ИИ

## Текущая цель

`FS-013` реализован и проверен как cohesive Matplotlib image MVP от выбранного локального PNG/JPEG
до видимых intermediates, dominant contour и анимируемого endpoint trace. Не начинать `FS-014`
без отдельной пользовательской команды; текущий handoff ожидает проверку или разрешение на merge.

## Активный stage

- Stage ID: `FS-013`
- Lifecycle: `completed`.
- Branch: `feature/fs-013-image-mvp`.
- Authorization: пользователь подтвердил push `main` и разрешил продолжение 2026-08-28.
- DAG: `FS-012 → FS-013`; FS-012 завершён, проверен и находится в `origin/main@c13f74d`.

## Runnable vertical slice

- Entry: пользователь запускает один MVP entry point с локальным simple-shape PNG/JPEG.
- Path: safe decode → preprocessing controls → explicit edge mode → dominant contour → normalized
  Curve → arc-length samples → accepted FFT/timeline → immutable frame → Matplotlib multi-panel
  intermediates и actual endpoint trace.
- Observable result: source-derived grayscale/binary/edge/contour diagnostics, selected limitations,
  controls и rotating trace находятся на одной рабочей поверхности.

## Scope и invariants

- Один documented launch/action flow и reusable application/view-state boundary.
- Controls: threshold/denoise/autocontrast/invert, explicit edge algorithm/parameters,
  sample/harmonic/speed и timeline play/pause/restart.
- States: initial, processing, ready, no-contour empty, validation/runtime error и cancelled.
- Cancellation не публикует stale/partial result как complete; retry всегда явный.
- UI/renderer не вычисляет CV/Fourier logic и использует существующий
  `build_dominant_contour_timeline`/`EpicycleTimeline` path.
- Source path/payload/native detail не попадают в UI status или logs; resource limits FS-010–FS-012
  сохраняются.
- Все user-facing strings идут через `resources/en.json`; production/fallback locale — `en`,
  pseudo-locale проверяет expansion.

## Non-goals / deferred

- PySide6 shell, packaging и окончательный accessibility matrix — `FS-021`.
- Skeletonization — `FS-014`; graph/routing/multiple components — `FS-015`–`FS-017`.
- Идеальная обработка arbitrary photos, background removal и 2D FFT не входят в stage.
- Animation/data export не расширяется: FS-013 допускает только диагностический preview/Agg evidence.

## PASS evidence / DoD

- Новые unit tests для typed state/config/cancellation и transactional publication.
- Integration проходит реальные PNG/JPEG → preprocessing/edges/contour/timeline boundaries.
- Component tests вызывают actual Matplotlib controls и проверяют initial/processing/ready/empty/
  error/cancel плюс pseudo-locale/text expansion.
- Live E2E запускает documented client entry point, получает intermediates и actual endpoint trace;
  corrupt/no-contour/cancel scenarios не дают ложного completed state.
- Новые unit/integration/component/live E2E: 29 tests PASS после review hardening.
- Полный terminal regression suite: 387 tests PASS; Ruff, strict mypy, frozen sync, overlay и diff
  gates PASS.
- Визуальный multi-panel PNG проверен: четыре различимые панели, selected contour, actual endpoint
  trace и читаемые limits.
- Независимый security review: GO после hard-link no-overwrite publication, unsafe-path guard и
  Unicode line-separator escaping; cooperative native-call cancellation явно deferred до FS-023.
- Completion Documentation Synchronization Gate выполнен; stage committed и остановлен перед
  `FS-014`.

## Integration boundary

Baseline `main` и `origin/main` совпадают на `c13f74d`. FS-013 находится только в
`feature/fs-013-image-mvp`; push/merge/PR/release для этого этапа не выполнялись.
