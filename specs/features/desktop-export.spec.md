# Feature SPEC — Desktop UI and Export

Статус: Принята, v0.1

## Назначение и область

Определить user-facing desktop workflow, central epicycle view, i18n boundary, cancellation и
export contracts. Math/CV implementation остаётся в application/core layers.

## Требования

### UI-FR-001 — Workflow pages

UI предоставляет SOURCE, MONOCHROME, EDGES, CONTOURS, CURVE, FOURIER SPECTRUM, EPICYCLES и EXPORT.
Недоступные будущие/invalid actions имеют disabled state и объяснение.

### UI-FR-002 — Epicycles view

Центральный canvas одновременно показывает nested rotating circles, head-to-tail vectors,
moving endpoint и persistent trace; original/reconstruction overlays optional.

### UI-FR-003 — State separation

Widgets dispatch application commands и render immutable/explicit view state. Fourier/CV logic,
file parsing и export encoding не выполняются в event handlers/paint callbacks.

### UI-FR-004 — Responsiveness and cancellation

Long operations выполняются вне GUI thread, публикуют progress/error/cancel states и корректно
завершают workers при закрытии окна.

### UI-FR-005 — Localization

Все user-facing strings находятся в resources. Начальные production language/locale — `en`,
fallback — `en`; pseudo-locale проверяет expansion/missing keys. RTL locale пока не заявлена.

### UI-FR-006 — Accessibility/layout

Controls доступны с клавиатуры, labels связаны с controls, focus order устойчив; resizing и text
expansion не скрывают primary controls. Color не является единственным носителем состояния.

### EX-FR-001 — Data/image export

Поддерживаются Curve JSON/CSV, coefficients JSON/CSV, spectrum/reconstruction PNG и diagnostic
intermediates соответствующих stages. Format/version/provenance включены там, где применимо.

### EX-FR-002 — Animation export

GIF обязателен; MP4 включается только после capability/license check. Frames строятся из того же
chain state/endpoint trace, что interactive renderer.

### EX-FR-003 — Safe paths and failure

Existing destination не перезаписывается молча. Partial files маркируются/удаляются безопасно;
failure сообщает фактически созданные artifacts и не использует shell-interpolated command.

## Состояния UI

Каждая page определяет initial/empty, ready, processing, cancelled, validation error, runtime
error и completed state. Missing translation показывает fallback string и diagnostic signal, не
пустую строку или stack trace.

## Acceptance

- UI-AC-001: freehand и image MVP проходят live user-to-endpoint-trace E2E.
- UI-AC-002: component tests покрывают controls, empty/error/disabled/cancel и keyboard path.
- UI-AC-003: default/fallback/pseudo-locale tests не требуют изменения business logic.
- UI-AC-004: GUI thread остаётся responsive на representative long operation.
- EX-AC-001: exported animation endpoint history эквивалентна interactive history.
- EX-AC-002: codec unavailable даёт явный degraded/unavailable result без ложного MP4 success.
- EX-AC-003: existing file и cancellation не приводят к silent data loss.

## Планируемая трассировка

Stages `FS-006`–`FS-008`, `FS-013`, `FS-021`–`FS-026`, `FS-030`; Behaviors
`BH-DRAW-001`, `BH-ANIMATION-001`, `BH-EXPORT-001`.
