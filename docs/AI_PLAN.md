# План работы ИИ

## Текущая цель

Реализовать один авторизованный этап `FS-012`: детерминированно выбрать доминирующий внешний
контур из результата FS-011, преобразовать его в нормализованную закрытую `Curve`, применить
принятое arc-length resampling и провести данные через существующие Fourier/epicycle timeline и
PNG renderer. После terminal evidence остановиться до `FS-013`.

## Stage contract

- Stage ID: `FS-012`
- Lifecycle: `in_progress`.
- Режим: production; SDLC: design → implementation → testing → review.
- DAG: `FS-011 + FS-009 + FS-008 → FS-012`.
- Entry evidence: все prerequisites имеют lifecycle `completed`; локальный `main` содержит их на
  commit `8a15a9e`; baseline 299 tests, Ruff, mypy, frozen sync и overlay — PASS.
- Авторизация: команда пользователя «сливай и выполняй дальше» от 2026-08-28.

## Runnable vertical slice

Локальный synthetic/simple-shape PNG/JPEG → FS-010 safe decode/preprocessing → выбранный FS-011
edge algorithm → OpenCV external contour candidates → project-owned dominant selection →
normalized closed `Curve` → arc-length resampling → существующие FFT/epicycle timeline → actual
endpoint trace → diagnostic PNG.

Наблюдаемый результат: CLI сообщает безопасный contour/edge provenance и создаёт читаемый PNG,
построенный существующим renderer из реального timeline frame. Пустая edge map возвращает явный
успешный empty result и не создаёт Curve/timeline/output.

## Scope

- Typed raster-space contour candidates/results/errors и безопасный OpenCV adapter.
- `RETR_EXTERNAL` + `CHAIN_APPROX_NONE`; backend order не влияет на выбор.
- Dominant key: максимальная точная площадь, затем площадь bounding box, затем число точек, затем
  каноническая лексикографическая сигнатура.
- Очистка соседних дублей и повторной terminal start point.
- Каноническая closed curve: counter-clockwise domain orientation, topmost/leftmost raster start,
  без повторения первой точки в конце.
- Координаты pixel centers: центрирование и aspect-preserving scale
  `2 / max(width - 1, height - 1)` с инверсией raster Y.
- Явные бюджеты edge density, числа кандидатов и aggregate candidate points; превышение fail-closed.
- Композиция с существующими resampling, FFT, timeline и renderer без их переопределения.

## Non-goals и инварианты

- Не реализуются FS-013 product polish, skeletonization/graph, multiple components,
  `PiecewiseCurve`, forced routing или новый contour backend.
- Выбирается ровно один внешний контур; остальные кандидаты сохраняются только как bounded
  diagnostic metadata.
- Пустой/дегенеративный набор кандидатов — валидный `no contour`, а не fabricated outline.
- Backend failure, malformed output и budget overflow — типизированные ошибки без silent fallback.
- Локальный путь, pixel data и сырые backend details не попадают в пользовательское сообщение.

## Задачи

- [ ] Добавить typed contour model и OpenCV extraction boundary.
- [ ] Реализовать детерминированный project-owned selector и canonical normalization.
- [ ] Собрать application result с preprocessing/edge/contour provenance, resampled curve и
      существующим `EpicycleTimeline`.
- [ ] Добавить диагностический CLI/live PNG path и resource-based строки.
- [ ] Добавить новые unit/property/integration/component/live E2E tests, не изменяя принятые
      контракты предыдущих этапов.
- [ ] Выполнить full/static/frozen/overlay gates, visual QA, review и documentation sync.

## PASS evidence / Definition of Done

- Unit: selection, все tie-break levels, orientation/start normalization, duplicate cleanup,
  coordinate transform, empty/degenerate/malformed/budget cases.
- Property: invariance к reversal/cyclic shift и candidate-order permutation.
- Integration: реальные threshold boundary и Canny проходят до closed/resampled Curve, FFT и
  timeline; каждый trace tail равен actual chain endpoint.
- Component/live E2E: реальный subprocess и PNG renderer; empty input не создаёт ложный output.
- Full pytest, Ruff, strict mypy, `uv sync --all-groups --frozen`, overlay validator и diff check —
  PASS; независимый review — GO.
- README, architecture, decisions, security, fallbacks, testing, traceability, learning, status,
  roadmap и selected stage record синхронизированы по фактическому evidence.

## Temporary / deferred

- Допустимо: OpenCV extraction adapter при полностью project-owned deterministic selection.
- Отложено: cohesive product flow/polish (`FS-013`), skeleton (`FS-014`), multiple components
  (`FS-016`) и forced continuous routing (`FS-017`).

## Integration boundary

`FS-007`–`FS-011` и post-merge status commit fast-forward merged в локальный `main` на `8a15a9e`.
Remote `origin/main` не обновлялся; push, PR и release не выполнялись.
