# Feature SPEC — Image to Curve and Routing

Статус: Принята, v0.1

## Назначение и область

Преобразовать безопасно декодированное локальное изображение в diagnostic binary/edge data,
contours, skeleton graph и одну из явных curve/routing models. Fourier/epicycle consumption
использует существующий application contract.

## Требования

### IM-FR-001 — Decode and limits

PNG/JPEG принимаются только после size/pixel checks из system SPEC и фактического safe decode.
EXIF orientation обрабатывается детерминированно; metadata не исполняется и не логируется целиком.

### IM-FR-002 — Diagnostic transforms

Grayscale, optional denoise/contrast, threshold, edge detection и skeletonization являются
отдельными transforms с typed input/output и доступным intermediate preview/export.

### IM-FR-003 — Edge modes

Поддерживаются threshold boundary и Canny с валидированными параметрами и synthetic fixtures.

### IM-FR-004 — Contours

Система сначала поддерживает один dominant contour, затем все connected components. При
отсутствии contour возвращается явный empty-result state, а не fabricated curve.

### IM-FR-005 — Skeleton graph

Graph строится только из validated binary skeleton по policy `corner-suppressed-8-v1`: orthogonal
foreground pixels смежны всегда, а diagonal pixels — только когда оба общих orthogonal bridge
pixels являются background. Raw pixel degree различает isolated (`0`), endpoint (`1`),
continuation (`2`) и junction (`>=3`). Смежные junction pixels образуют один `JUNCTION_REGION`,
degree-2 chains — graph edges, а pure degree-2 loop получает deterministic `LOOP_ANCHOR` и
self-loop. Результат является immutable undirected pseudomultigraph с explicit components,
parallel/self edges и exact disjoint partition foreground между node-owned pixels и edge-owned
interior pixels. Canonical serialization детерминирована, но не задаёт traversal/routing order;
raster pixels и graph nodes не смешиваются в одном неявном type.

### IM-FR-006 — Routing policies

Режимы: `MAIN_CONTOUR`, `ALL_COMPONENTS`, `STRICT_SINGLE_CURVE`, `PIECEWISE_DISCONNECTED`.
`STRICT_SINGLE_CURVE` является только explicit opt-in и строится по тому же raw
`corner-suppressed-8-v1` adjacency, что FS-015. Для component с 0/2 odd pixel vertices
используется exact deterministic Hierholzer circuit/trail; для `>2` odd vertices — bounded
row-major spanning-tree T-join, который bottom-up дублирует parent link только для odd subtree,
после чего выполняется Hierholzer. Это deterministic linear heuristic, а не optimal Chinese
Postman claim. Disconnected components соединяются deterministic nearest-entry policy и итоговый
route всегда cyclic: межкомпонентные и closing bridges имеют explicit endpoints/type/length.
Original, duplicated и bridge steps различимы; metrics содержат их counts/lengths и
`added_length = duplicated_length + bridge_length`. Component count `≤1024`, итоговый route
`≤262144` samples, cancellation проверяется bounded batches; empty/cancelled/resource/malformed
result не публикует partial `Curve`. Piecewise mode не создаёт bridge и не меняется этой policy.

### IM-FR-007 — Discontinuous signal

Piecewise conversion создаёт один independent `Curve` на graph component только для однозначной
simple-path, pure-loop или isolated topology. Segments canonical ordered по component storage key,
сохраняют component/edge/node provenance и используют общий
`pixel-center-centered-aspect-v1` transform. Между соседними segments хранится explicit boundary
metadata; `PEN_UP_RENDERING` не рисует connector. Branched/ambiguous component возвращает typed
unsupported result без partial `PiecewiseCurve`; traversal, duplication и bridge относятся к
explicit routing policy. FS-018 sampling выбирает explicit `EQUAL` либо
`PROPORTIONAL_ARC_LENGTH` allocation, выдаёт ровно requested sample count и минимум один sample на
segment. Boundary metadata хранит sample indices, endpoints и jump length, включая periodic
last→first seam. Один discontinuous sample sequence создаёт spectrum/timeline для
`STRICT_TRAJECTORY` и `PEN_UP_RENDERING`; policy меняет только source-stroke artists, но не
coefficients, reconstruction или endpoint history. Insufficient allocation отклоняется без merge.

### IM-FR-008 — 2D FFT separation

FFT2 consumes raster intensity and returns 2D frequency data (magnitude/log magnitude/phase and
filtered reconstruction), не `FourierSpectrum` complex curve.

### IM-FR-009 — Simplification comparison

FS-027 contour diagnostic принимает opt-in finite non-negative simplification tolerance. Normalized
source contour сохраняется, упрощение выполняется до resampling, а original и simplified curves
независимо arc-length-resample-ятся к одному `N` и проходят существующий Fourier/timeline path с
одинаковым `K`, ordering и speed. Comparison явно показывает source/result point counts, tolerance,
length/deviation metrics, baseline-vs-simplified sampled error и обе reconstruction errors против
одной baseline reference. Никакой metric не объявляет универсальное improvement.

Без simplification option существующий contour path не меняется. Invalid tolerance, work budget,
cancellation или render/output failure завершаются controlled state, сохраняют existing destination
и не переключаются молча на original. Curvature-aware simplification и adaptive sampling — не FS-027.

### IM-FR-010 — Adaptive sampling comparison

FS-028 contour diagnostic принимает отдельный opt-in curvature weight и сравнивает uniform
arc-length/adaptive samples одного normalized contour при одинаковых `N`, `K`, speed и timeline
advance. Comparison показывает source curvature/density provenance, обе sampled geometries, spacing
diagnostics и обе reconstruction errors против uniform baseline reference. Он не утверждает, что
adaptive sampling лучше для произвольной curve.

Adaptive option несовместим с FS-027 simplification option в одном invocation: каждый diagnostic
остаётся отдельным измеримым slice. Без option legacy contour path не меняется. Invalid/degenerate
input или render/output failure сохраняют existing destination и не включают silent fallback.

### IM-FR-011 — Selectable bounded route optimization

FS-029 сохраняет FS-017 `baseline_tree_t_join_v1` default и добавляет explicit
`greedy_shortest_odd_pairing_v1`. Для каждого connected component с более чем двумя odd vertices
improved policy берёт lowest-key remaining odd vertex, bounded weighted shortest-path search до
остальных odd vertices, выбирает minimum `(distance, target_key)` и дублирует найденный source path;
затем existing Hierholzer/component-order/bridge/Fourier path не меняется.

Optimization expansion budget explicit `1..10,000,000`; exhaustion/cancel публикуют typed non-ready
result без partial route или silent baseline. Comparison строит baseline и improved независимо над
одним immutable graph, показывает method/budget, duplicated/bridge/added length и measured routing
time/delta. Improved route может быть valid, но не дешевле; exact/global optimum не заявляется.
`PIECEWISE_DISCONNECTED` остаётся отдельным доступным mode и не получает fabricated bridges.

## Fallback/failure

Invalid/corrupt/oversized input fail closed. Отсутствие optional CV backend не разрешает silent
algorithm switch: capability проверяется, provenance отображается, unsupported operation явно
недоступна. Cancellation не публикует partial result как complete.

## Acceptance

- IM-AC-001: oversized/corrupt/spoofed files отклоняются до unsafe allocation.
- IM-AC-002: каждый transform проверяется synthetic fixture и сохраняет diagnostic provenance.
- IM-AC-003: dominant contour pipeline заканчивается epicycle endpoint trace.
- IM-AC-004: disconnected fixture остаётся piecewise без bridge в соответствующем mode.
- IM-AC-005: forced route для Euler/non-Euler/disconnected fixtures byte-for-byte deterministic,
  покрывает каждый original raw link, остаётся cyclic/continuous, сообщает original/duplicated/
  bridge counts и lengths; Fourier trace использует именно опубликованный route без hidden seam.
- IM-AC-006: FFT2 types/API не смешаны с 1D curve Fourier.
- IM-AC-007: line/T/cross/loop/multi-component fixtures подтверждают raw degree roles, exact
  foreground partition, отсутствие implicit bridges и byte-stable canonical graph serialization.
- IM-AC-008: two-component path/loop fixture даёт deterministic `PiecewiseCurve` с exact pixel
  coverage и explicit pen-up boundary; branched fixture не создаёт partial curve или hidden route.
- IM-AC-009: unit/property/integration/component/live CLI evidence подтверждает normalized contour →
  bounded Douglas–Peucker → equal-N resampling → two actual timelines, side-by-side PNG/provenance,
  source recoverability и atomic no-overwrite failure behavior.
- IM-AC-010: unit/property/integration/component/live CLI evidence подтверждает normalized contour →
  uniform/adaptive equal-N sampling → equal-K actual timelines, deterministic density provenance,
  side-by-side PNG/metrics и unchanged legacy path.
- IM-AC-011: accepted loop/branch/disconnected corpus подтверждает original-link coverage,
  continuity, deterministic policy/provenance, explicit budget/cancel failures и measured baseline
  comparison; at least one asymmetric branch fixture имеет lower improved duplicated/added length.

## Планируемая трассировка

Stages `FS-010`–`FS-020`, `FS-027`–`FS-029`; Behaviors `BH-IMPORT-001`,
`BH-DISCONTINUITY-001`, `BH-SIMPLIFY-001`, `BH-ADAPTIVE-001`, `BH-ROUTE-OPT-001`.
