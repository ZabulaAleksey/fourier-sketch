# План работы ИИ

## Текущая цель

Этап `FS-012` завершён и подтверждён. Активной implementation-задачи нет; repository остановлен
перед `FS-013` согласно handoff текущего stage.

## Последний завершённый stage

- Stage ID: `FS-012`
- Lifecycle: `completed`.
- DAG: `FS-011 + FS-009 + FS-008 → FS-012`; prerequisites и entry evidence подтверждены.
- Implementation commits: `418192a`, hardening `a1c211c`.
- Runnable slice: local PNG/JPEG → safe preprocessing → selected edges → bounded OpenCV external
  candidates → project-owned dominant selection → canonical closed `Curve` → arc-length samples →
  existing FFT/timeline → actual endpoint trace → diagnostic PNG.

## Реализованный контракт

- Extraction: `RETR_EXTERNAL` + `CHAIN_APPROX_NONE`, source-foreground binding, simple unique
  adjacent cycle, exact shoelace area и fail-closed native-output validation.
- Dominant key: area2 → bounding-box area → point count → canonical signature; backend order не
  является семантикой.
- Transform: counter-clockwise domain orientation, topmost/leftmost raster start, centered
  aspect-preserving pixel-center coordinates с одним scale.
- Budgets: 250 000 edge pixels, 25 000 candidates, 100 000 aggregate raw points; resampling 3..4096.
- Empty semantics: blank/degenerate/open fragments возвращают `NoContourResult`; Curve, timeline и
  output не создаются.
- Failure semantics: invalid options/backend/resource limit типизированы, без alternate algorithm,
  fabricated contour, raw native detail или небезопасного filename display.

## Terminal evidence

- New targeted unit/property/integration/component/live E2E: 59 PASS.
- Full regression: 358 PASS; принятые pre-FS-012 tests не изменялись.
- `uv sync --all-groups --frozen`, Ruff, strict mypy, overlay validator и diff check: PASS.
- Visual QA: normalized ellipse, K=12, actual accumulated endpoint trace и renderer layers: PASS.
- Independent correctness re-review: GO; предыдущие P1/P2 закрыты, новых P0/P1/P2 нет.
- Independent security re-review: GO; resource/terminal-safety P2 закрыты, новых P0/P1/P2 нет.
- Completion Documentation Synchronization Gate: выполнен; stale FS-012 planned/blocked claims
  устранены, stable SPEC/math contracts проверены без изменений.

## Acceptance / DoD

- [x] Deterministic dominant selection и все tie-break levels.
- [x] Orientation/start/coordinate normalization инвариантны к cyclic shift/reversal.
- [x] Реальные threshold-boundary и Canny проходят до closed/resampled Curve и timeline.
- [x] Каждый emitted trace tail равен actual chain endpoint.
- [x] Empty/open/backtracking/off-source inputs не создают скрытую closed route.
- [x] Resource, malformed backend, privacy, overwrite и localization boundaries проверены.
- [x] Unit/property/integration/component/live E2E, full/static/security/overlay gates прошли.

## Следующий кандидат — не запущен

- Next candidate: `FS-013`.
- Lifecycle: `planned`; технический prerequisite `FS-012` завершён.
- Intended slice: cohesive user-selected image → diagnostics/controls → dominant contour → rotating
  endpoint trace product MVP.
- До явной авторизации не создаются FS-013 code/tests и не меняется его lifecycle.

## Integration boundary

Локальный `main` остаётся на `8a15a9e`; FS-012 находится только в
`feature/fs-012-dominant-contour`. Remote `origin/main` не обновлялся; push, merge, PR и release для
FS-012 не выполнялись.
