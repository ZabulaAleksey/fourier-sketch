# Feature SPEC — Epicycle Animation

Статус: Принята, v0.1

## Назначение и область

Определить математическую chain state и rendering contract, при котором фактический endpoint
последнего rotating vector является drawing point. Fourier coefficient computation принадлежит
Fourier Core; desktop shell и export детализированы отдельно.

## Требования

### EP-FR-001 — Rotating vector

Для coefficient `C_k = A_k exp(i φ_k)` vector равен
`v_k(t) = A_k exp(i(φ_k + 2πkt))` на normalized time `t`. DC stationary; знак `k` задаёт
направление вращения.

### EP-FR-002 — Head-to-tail chain

Первый vector начинается в `origin`, каждый следующий — в предыдущем `end`. State содержит
`time`, `origin`, ordered vectors, centers и endpoint. Пустой selection недопустим.

### EP-FR-003 — Endpoint equivalence

Для одинакового selected coefficient set и origin:
`chain.endpoint(t) = origin + Σv_k(t) ≈ reconstruction(t)`. Order может менять промежуточные
centers, но не endpoint в пределах tolerance.

### EP-FR-004 — Trace provenance

Animation loop добавляет `chain.endpoint` в history. Renderer не вычисляет отдельную
reconstruction point для decorative trace.

### EP-FR-005 — Renderer boundary

Для каждого vector renderer получает `start`, `end`, `amplitude/radius`, `frequency`, `phase`.
Circle center равен start; next center равен previous end. Show/hide toggles не мутируют state.

### EP-FR-006 — Controls

Diagnostic/user surface поддерживает pause, restart, speed, harmonic count и visibility circles,
vectors, endpoint, trace, original/reconstruction. Invalid control values отклоняются явно.

### EP-FR-007 — Piecewise rendering

`STRICT_PATH` показывает полную Fourier trajectory. `PEN_UP_RENDERING` разрывает stroke только по
segment metadata и не меняет coefficients/chain endpoint.

## Behavior contracts

### BH-EPICYCLE-001

Все selected vectors одновременно вращаются со своей frequency/phase/amplitude; centers образуют
непрерывную head-to-tail chain.

### BH-EPICYCLE-TRACE-001

`drawing_point(t) == chain.endpoint(t)` и `trace[n] == sampled_chain_state[n].endpoint`.

### BH-ANIMATION-001

Play/pause/restart меняют timeline предсказуемо; restart очищает или восстанавливает trace согласно
явной command semantics и не оставляет stale chain state.

## Acceptance

- EP-AC-001: DC, positive/negative k, amplitude и phase проходят analytical tests.
- EP-AC-002: `next.start == previous.end`, `endpoint == last.end`.
- EP-AC-003: endpoint/reconstruction parity проходит property tests для orderings и times.
- EP-AC-004: trace test доказывает provenance из chain state.
- EP-AC-005: renderer smoke показывает nested circles/vectors/endpoint/trace без math logic.
- EP-AC-006: live freehand E2E доказывает drawing → endpoint trace path.

## Планируемая трассировка

Stages `FS-005`–`FS-008`, `FS-018`, `FS-021`, `FS-022`.
