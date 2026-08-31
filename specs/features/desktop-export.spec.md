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
Canvas сохраняет aspect ratio, предоставляет numerically bounded near-unrestricted user zoom
`0.01..100.00×` и явный reset к `1.00×`; масштаб меняет только presentation, не Fourier/timeline
state. После принятия новой freehand curve значение `1.00×` отображает её в той же относительной
системе координат, что drawing field: центр поля остаётся `O`, а доля ширины/высоты исходного поля
сохраняется в epicycle viewport без fit-to-content растягивания. Колесо мыши, slider и pinch меняют
масштаб вокруг фиксированного центра viewport: scene-coordinate под геометрическим центром canvas
остаётся неизменной, а pan пропорционально корректируется; drag левой кнопкой мыши
перемещает viewport, а reset возвращает pan к нулю. Координата Y
freehand input переводится из экранной вниз-направленной системы в Cartesian presentation contract,
чтобы ready contour не был отражён по вертикали. Wheel zoom и zoom slider всегда показывают одно
и то же view scale. Начало координат поля freehand совпадает с его visual center и с `O`, началом
head-to-tail chain, включая stationary DC vector. Vector/circle colors детерминированно следуют
rainbow palette по selection order, не меняя математическое состояние; цвет уже существующей позиции
не меняется при увеличении harmonic count, а vector и circle одной позиции используют один цвет.
На desktop-устройствах с сенсорным экраном один палец перемещает viewport, а pinch двумя пальцами
масштабирует вокруг фиксированного центра viewport в тех же границах `0.01..100.00×`. Wheel, slider и pinch
синхронизируют одно view scale; touch-навигация и reset не меняют curve, coefficients, selection,
chain geometry, endpoint, timeline, trace ledger или animation state. Android touch input остаётся
отдельным контрактом FS-031.

Visibility control `Original` disabled и unchecked, пока ready frame отсутствует. Для ready frame
его checked state строго совпадает с `frame.visibility.original`: checked показывает исходную curve,
unchecked полностью скрывает её; новая принятая curve возвращает control в checked/visible state.

### UI-FR-010 — Source/view alignment

В desktop-first layout поле freehand drawing выравнивается по вертикальному центру с epicycle canvas;
на компактном окне сохраняется безопасный минимальный размер поля без перекрытия controls.

### UI-FR-011 — Read-only harmonic inspector

После появления ready `EpicycleFrame` desktop UI предоставляет inspector текущего ordered
coefficient/vector set. Пользователь выбирает одну гармонику кликом по её vector/circle либо строкой
списка; список поддерживает обычную keyboard navigation. Stable selection identity — signed
frequency `k`, а не transient row index. Inspector показывает selection position, `k`, amplitude,
phase, angular velocity и текущий complex local contribution из той же пары
`frame.selection.coefficients[i]` / `frame.chain.vectors[i]`, которую рисует canvas.

Inspector selection является только presentation state: выбор, очистка и обновление значений не
меняют Curve, coefficients, harmonic count/order, chain geometry, endpoint, timeline state/speed,
trace ledger или animation lifecycle. При animation advance выбранный `k` сохраняется и его current
local contribution обновляется из нового immutable frame. При изменении K выбранный `k` сохраняется,
только если он остаётся в selection; новый source/timeline, stale frequency или off-harmonic canvas
click явно очищает inspector. Canvas различает click selection и drag-pan, поэтому inspection не
ломает существующую navigation.

### UI-FR-012 — Single-frequency Solo analysis

Ready inspector позволяет включить Solo для ровно одной выбранной signed frequency `k`. В FS-025
multi-select явно отложен: Solo строит отдельную analysis-проекцию из соответствующего coefficient,
а не вызывает `set_harmonic_count(1)` и не заменяет baseline Fourier selection. На canvas
`selection`, chain vectors/circles, endpoint, reconstruction и отдельный Solo trace display frame
соответствуют фактическому active set `(k,)`; persistent trace по общему UI-FR-002 не рисуется, а
видимый mode label сообщает, что активен `SOLO` и содержит `k`.

Baseline timeline остаётся source of truth и во время Solo не меняет complete spectrum, ordered
selection/K, current time, speed, visibility, play/pause state, animation lifecycle или свой trace
ledger. Animation advance проецируется в Solo при том же времени, а Solo trace содержит только
endpoint фактического `(k,)` active set. Выход из Solo раскрывает нетронутый baseline frame и тем
самым точно восстанавливает selection, geometry, endpoint, reconstruction и trace без обратной
мутации. Harmonic-count control блокируется на время Solo; новый timeline очищает Solo. Empty/stale
inspector selection отклоняется и не создаёт скрытого режима.

Solo — analysis-only view: export navigation/action недоступны до выхода из режима, поэтому
FS-022 продолжает экспортировать baseline current selection и не получает неявную новую семантику.
Solo activation/exit не ставит animation на паузу и не меняет presentation zoom/pan. Keyboard
пользователь может выбрать строку, включить и выключить Solo отдельной доступной кнопкой; color не
является единственным носителем режима.

### UI-FR-013 — Harmonic Build-Up analysis

Ready desktop view позволяет выбрать один из существующих deterministic non-explicit orderings,
target `N` в bounded interactive range и dwell `0.10..5.00 s`, затем запустить Build-Up. Start
создаёт actual `K=1` frame и запускает дискретную последовательность. Пока mode активен, existing
Play/Pause/Restart context-sensitive: они resume/pause sequence либо возвращают её к paused `K=1`;
baseline timeline time/state/trace не продвигаются и не мутируются. Один существующий QTimer считает
только dwell, не больше одного K-step за tick; smooth interpolation отложен.

Каждый display frame использует exact first-K prefix выбранного ordering и фактические chain,
reconstruction/endpoint. K transition начинает отдельный singleton endpoint trace; histories разных
K не смешиваются. Mode label показывает ordering, `K/N`, latest signed `k`, dwell, retained energy и
measured RMSE без monotonic-error claim. Inspector читает current Build-Up set и фокусирует latest k.

Solo и Build-Up взаимоисключающие. Во время Build-Up harmonic slider, Solo activation, ordering/
target/dwell editing и export navigation/action disabled. При `K=N` state становится `completed` и
timer прекращает sequence. Exit раскрывает exact latest baseline object; если baseline timeline был
running до входа, normal ticks возобновляются без catch-up. Новый timeline/source mismatch очищает
mode. Invalid budget/dwell/ordering отклоняются transactionally.

### UI-FR-003 — State separation

Widgets dispatch application commands и render immutable/explicit view state. Fourier/CV logic,
file parsing и export encoding не выполняются в event handlers/paint callbacks.

### UI-FR-004 — Responsiveness and cancellation

Long operations выполняются вне GUI thread, публикуют progress/error/cancel states и корректно
завершают workers при закрытии окна. Cancel доступен только пока есть cancellable background job;
без job control disabled и не создаёт ложный cancelled state. Cancel только запрашивает cooperative
interruption и подавляет late publication: `QThread.terminate()` запрещён. Если owned worker ещё
выполняется, закрытие окна откладывается до его normal finish.

### UI-FR-007 — Bounded renderer work

Paused/unmodified view не перерисовывается непрерывно. Static contour layers/bounds допускают
cache, desktop paint path не сканирует и не рисует persistent trace, а optimization сохраняет exact
endpoint/state parity. GPU/QML adapter вводится только после measured QPainter baseline и parity.

### UI-FR-008 — Desktop speed control

Desktop speed control использует небольшой bounded диапазон `0.01..1.00×` с шагом `0.01×`.
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
  `0.01..1.00×` с шагом `0.01×` и не передаёт timeline значение выше `1.00×`.
- EX-AC-001: exported animation endpoint history эквивалентна interactive history.
- EX-AC-002: codec unavailable даёт явный degraded/unavailable result без ложного MP4 success.
- EX-AC-003: existing file и cancellation не приводят к silent data loss.
- UI-AC-007: cancellation остаётся responsive, не вызывает forced termination и сохраняет ownership
  worker до normal finish; close завершается после bounded worker completion.
- UI-AC-008: unit/component/live desktop E2E подтверждают exact coefficient/vector mapping,
  pointer/list/keyboard selection, animation-time refresh, explicit empty/stale clearing,
  pseudo-locale expansion и отсутствие изменений Fourier/timeline/trace/animation state.
- UI-AC-009: unit/property/component/live desktop E2E подтверждают single-frequency active-set
  chain/endpoint/reconstruction/Solo-trace parity, explicit accessible mode, empty/stale rejection,
  disabled baseline mutation/export controls и точное восстановление нетронутого timeline frame.
- UI-AC-010: unit/property/integration/component/live desktop E2E подтверждают exact deterministic
  prefixes `1..N`, no-skipped-step dwell/pause/restart/completed transitions, per-K trace reset,
  measured metrics, accessible provenance, Solo/export/harmonic gating и exact baseline isolation.

## Планируемая трассировка

Stages `FS-006`–`FS-008`, `FS-013`, `FS-021`–`FS-026`, `FS-030`; Behaviors
`BH-DRAW-001`, `BH-ANIMATION-001`, `BH-EXPORT-001`, `BH-INSPECTOR-001`, `BH-SOLO-001`,
`BH-BUILDUP-001`.
