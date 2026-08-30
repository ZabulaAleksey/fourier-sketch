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

Центральный desktop canvas одновременно показывает nested rotating circles, head-to-tail vectors,
moving endpoint и уже построенный contour/reconstruction. Persistent trace остаётся application/
export evidence, но desktop canvas его не рисует: дублирующий шлейф не должен увеличивать frame work.
Canvas сохраняет fit-to-scene aspect ratio, предоставляет numerically bounded near-unrestricted user
zoom `0.01..100.00×` и явный
reset к `1.00×`; масштаб меняет только presentation, не Fourier/timeline state. Колесо мыши меняет
zoom, а drag левой кнопкой мыши перемещает viewport; reset также возвращает pan к нулю. Координата Y
freehand input переводится из экранной вниз-направленной системы в Cartesian presentation contract,
чтобы ready contour не был отражён по вертикали. Wheel zoom и zoom slider всегда показывают одно
и то же view scale. Начало координат поля freehand совпадает с его visual center и с `O`, началом
head-to-tail chain, включая stationary DC vector. Vector/circle colors детерминированно следуют
rainbow palette по selection order, не меняя математическое состояние; цвет уже существующей позиции
не меняется при увеличении harmonic count, а vector и circle одной позиции используют один цвет.
На desktop-устройствах с сенсорным экраном один палец перемещает viewport, а pinch двумя пальцами
масштабирует относительно центра pinch в тех же границах `0.01..100.00×`. Wheel, slider и pinch
синхронизируют одно view scale; touch-навигация и reset не меняют curve, coefficients, selection,
chain geometry, endpoint, timeline, trace ledger или animation state. Android touch input остаётся
отдельным контрактом FS-031.

### UI-FR-010 — Source/view alignment

В desktop-first layout поле freehand drawing выравнивается по вертикальному центру с epicycle canvas;
на компактном окне сохраняется безопасный минимальный размер поля без перекрытия controls.

### UI-FR-003 — State separation

Widgets dispatch application commands и render immutable/explicit view state. Fourier/CV logic,
file parsing и export encoding не выполняются в event handlers/paint callbacks.

### UI-FR-004 — Responsiveness and cancellation

Long operations выполняются вне GUI thread, публикуют progress/error/cancel states и корректно
завершают workers при закрытии окна. Cancel доступен только пока есть cancellable background job;
без job control disabled и не создаёт ложный cancelled state.

### UI-FR-007 — Bounded renderer work

Paused/unmodified view не перерисовывается непрерывно. Static contour layers/bounds допускают
cache, desktop paint path не сканирует и не рисует persistent trace, а optimization сохраняет exact
endpoint/state parity. GPU/QML adapter вводится только после measured QPainter baseline и parity.

### UI-FR-008 — Desktop speed control

Desktop speed control использует небольшой bounded диапазон `0.10..1.00×` с шагом `0.01×`.
Отображаемое значение и timeline speed совпадают; keyboard step не перескакивает скрытые значения.

### UI-FR-009 — Image foreground polarity

Desktop image source по умолчанию обрабатывает тёмный рисунок на светлом фоне, чтобы светлый фон не
становился dominant contour рамки изображения. Пользователь может отключить этот режим для обратной
полярности; выбор применяется как explicit preprocessing option до запуска worker.

### UI-FR-005 — Localization

Все user-facing strings находятся в resources. Начальные production language/locale — `en`,
fallback — `en`; pseudo-locale проверяет expansion/missing keys. RTL locale пока не заявлена.

### UI-FR-006 — Accessibility/layout

Controls доступны с клавиатуры, labels связаны с controls, focus order устойчив; resizing и text
expansion не скрывают primary controls. Color не является единственным носителем состояния.

### EX-FR-001 — Data/image export

Поддерживаются Curve JSON/CSV, coefficients JSON/CSV, spectrum/reconstruction PNG и diagnostic
intermediates соответствующих stages. Format/version/provenance включены там, где применимо.
FS-022 desktop export serializes the current original Curve and current ordered coefficient selection;
JSON and CSV name their schema/version and preserve point/coefficient order. PNG views consume the
same immutable frame/selection as the canvas and do not recalculate a second Fourier result.

### EX-FR-002 — Animation export

GIF обязателен; MP4 включается только после capability/license check. Frames строятся из того же
chain state/endpoint trace, что interactive renderer. Initial FS-022 GIF is bounded to `2..120`
frames with `20..1000 ms` duration per frame and records bounded endpoint-history metadata. Pillow,
already pinned for safe local images, is the selected GIF backend. No reviewed MP4 backend exists,
so MP4 is visibly unavailable and must not fall back to GIF silently.

### EX-FR-003 — Safe paths and failure

Existing destination не перезаписывается молча. Partial files маркируются/удаляются безопасно;
failure сообщает фактически созданные artifacts и не использует shell-interpolated command.
Every FS-022 artifact is encoded to a sibling temporary file and atomically published only after
successful completion; cancellation checks occur between animation frames and leave no destination.

## Состояния UI

Каждая page определяет initial/empty, ready, processing, cancelled, validation error, runtime
error и completed state. Missing translation показывает fallback string и diagnostic signal, не
пустую строку или stack trace.

## Acceptance

- UI-AC-001: freehand и image MVP проходят live user-to-endpoint-trace E2E.
- UI-AC-002: component tests покрывают controls, empty/error/disabled/cancel и keyboard path.
- UI-AC-003: default/fallback/pseudo-locale tests не требуют изменения business logic.
- UI-AC-004: GUI thread остаётся responsive на representative long operation.
- UI-AC-005: frame-time profile на named Windows environment подтверждает declared interactive
  budget для default и stress K/trace; paused view не выполняет continuous redraw.
- UI-AC-006: desktop canvas не создаёт trace artist/path, а speed slider точно покрывает
  `0.10..1.00×` с шагом `0.01×` и не передаёт timeline значение выше `1.00×`.
- EX-AC-001: exported animation endpoint history эквивалентна interactive history.
- EX-AC-002: codec unavailable даёт явный degraded/unavailable result без ложного MP4 success.
- EX-AC-003: existing file и cancellation не приводят к silent data loss.

## Планируемая трассировка

Stages `FS-006`–`FS-008`, `FS-013`, `FS-021`–`FS-026`, `FS-030`; Behaviors
`BH-DRAW-001`, `BH-ANIMATION-001`, `BH-EXPORT-001`.
