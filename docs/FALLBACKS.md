# Fallbacks Fourier Sketch

Этот документ содержит только project-specific delta к глобальной Fallback Policy.

## 1D Fourier transform backends (FS-002)

| Поле | Контракт |
|---|---|
| Primary working path | явный вызов `fft_dft` (NumPy) |
| Correctness oracle | отдельный явный `reference_dft`, `N ≤ 2048` |
| Primary budget | `1 ≤ N ≤ 262144`, finite complex samples |
| Failure signal | `DomainValidationError` для input/budget/result; `FourierBackendError` для backend failure |
| Retry | отсутствует: local deterministic operation не retry-ится |
| Automatic fallback | запрещён |
| Degraded result | отсутствует; incomplete/non-finite spectrum не возвращается |
| Provenance | `FourierSpectrum.source_metadata["backend"]` |
| Recovery | исправить input/dependency и повторить выбранную operation явно |
| Tests | backend failure, budgets, non-finite input/result, reference/NumPy parity |

Reference implementation не заменяет недоступный NumPy backend автоматически: при большом input
это нарушило бы resource budget, а при backend defect скрыло бы фактическую причину отказа.

## Diagnostic rendering (FS-006)

| Поле | Контракт |
|---|---|
| Interactive path | Matplotlib window с `EpicycleTimeline` |
| Headless path | отдельный явный `--headless` через Agg и тот же timeline/frame |
| Failure signal | controlled CLI exit `2`; validation/I/O error без partial success |
| Retry | отсутствует для deterministic render/path failure |
| Automatic fallback | interactive → headless или headless → другой renderer запрещён |
| Partial artifact | temporary sibling удаляется; reserved empty destination удаляется при failure |
| Recovery | выбрать headless явно либо исправить destination/dependency и повторить |

Agg не является silent fallback: пользователь/automation выбирает `--headless` явно. Недоступный
Matplotlib останавливает entry point; Pillow/transitive codec не используется как альтернативный
project image/export backend.

## Local image preprocessing (FS-010)

| Поле | Контракт |
|---|---|
| Primary path | Pillow 12.3.0, explicit actual PNG/JPEG allowlist |
| Budgets | encoded `≤25 MiB`; decoded `≤40,000,000` pixels |
| Failure signal | stable `ImageInputError.code`; localized CLI exit `2` |
| Retry | отсутствует для local deterministic validation/decode failure |
| Automatic fallback | другой decoder/format, truncated recovery и first-frame fallback запрещены |
| Degraded result | отсутствует; partial transform result не публикуется |
| Provenance | actual format, byte count, source/oriented dimensions, EXIF decision, transforms |
| Recovery | исправить input/options/dependency и повторить operation явно |

Grayscale и threshold не являются fallback друг для друга: оба результата создаются одним
успешным use case и экспортируются только через explicit `--stage`. Недоступность Canny в FS-011
не изменяет FS-010 binary semantics.

## Edge detection (FS-011)

| Поле | Контракт |
|---|---|
| Project path | explicit `threshold_boundary` на FS-010 binary raster |
| Optional backend path | explicit OpenCV Canny на FS-010 grayscale raster |
| Failure signal | stable `EdgeDetectionError.code`; localized CLI exit `2` |
| Retry | отсутствует для deterministic parameter/backend failure |
| Automatic fallback | Canny ↔ threshold boundary запрещён |
| Degraded result | отсутствует; malformed backend output не публикуется |
| Provenance | algorithm, backend/version, exact parameters, source stage/dimensions |
| Recovery | исправить parameters/dependency и явно повторить выбранный algorithm |

Недоступный OpenCV делает unavailable только explicit Canny operation. `threshold_boundary`
остаётся отдельной доступной capability, но приложение не запускает её вместо Canny и не выдаёт
один результат за эквивалент другого. Empty edge map является complete diagnostic result, а не
degraded contour.

## Dominant contour (FS-012)

| Поле | Контракт |
|---|---|
| Primary path | OpenCV external extraction → project-owned dominant selection |
| Budgets | edge pixels `≤250,000`; candidates `≤25,000`; raw points `≤100,000` |
| Failure signal | stable `ContourExtractionError.code`; localized CLI exit `2` |
| Retry | отсутствует для deterministic extraction/validation/resource failure |
| Automatic fallback | другой retrieval/approximation/backend, hull, skeleton или bridge запрещены |
| Empty result | `NoContourResult`; CLI exit `0`, Curve/timeline/PNG не создаются |
| Provenance | backend, extraction modes, selection/transform/orientation/start policies и metrics |
| Recovery | изменить input/preprocessing или dependency и явно повторить operation |

`no contour` — полноценный пустой результат, а не degraded success. Backend/resource failure не
превращается в empty result, а empty result не запускает Fourier path. Остальные candidates не
соединяются и не выдаются за единую curve; multi-component policy относится к FS-016.

## Image MVP generation and cancellation (FS-013)

| Поле | Контракт |
|---|---|
| Primary path | один explicit image config → FS-010..FS-012 pipeline → existing timeline/frame |
| Failure signal | `ERROR` со stable resource key; CLI exit `2`; raw exception/path отсутствуют |
| Cancellation | current token устанавливается, snapshot становится `CANCELLED`, partial result не публикуется |
| Stale work | generation mismatch отбрасывает late ready/empty/error без изменения current snapshot |
| Automatic fallback | другой edge algorithm, decoder, contour route или sync UI path запрещены |
| Empty result | `EMPTY` с FS-012 provenance; interactive recovery или explicit headless recovery PNG |
| Retry | только новый explicit `Process`/Enter/CLI invocation с новой generation |

`Cancel` не останавливает native/Pillow/OpenCV call принудительно: проверка token происходит между
bounded pipeline steps и перед publication. Это cooperative cancellation, а не false-complete
fallback; FS-023 отвечает за measured cancellation latency и hardening representative large input.

## Skeletonization (FS-014)

| Поле | Контракт |
|---|---|
| Primary path | FS-010 binary raster → explicit scikit-image 0.26.x Lee → typed skeleton |
| Budget | decoded `≤40 MP`; foreground `≤4,000,000` pixels |
| Failure signal | stable `SkeletonizationError.code`; localized controller/CLI error, exit `2` |
| Cancellation | cooperative token до imports, до/после backend; late result не публикуется |
| Automatic fallback | Lee → Zhang/OpenCV/project-owned transform запрещён |
| Empty result | same-sized empty binary skeleton; complete success, exit `0` |
| Malformed result | wrong type/dtype/shape, foreground вне source или solid `2×2` fail closed |
| Provenance | explicit `lee`, bounded `scikit-image/<version>`, dimensions и pixel counts |
| Recovery | исправить input/dependency и явно повторить invocation; partial artifact отсутствует |

Skeleton и preview являются двумя explicit output modes, а не fallback друг для друга. Один CLI
invocation публикует ровно один artifact; существующий destination сохраняется без `--overwrite`.

## Skeleton graph (FS-015)

| Поле | Контракт |
|---|---|
| Primary path | typed Lee result → `corner-suppressed-8-v1` → compressed topology |
| Budgets | foreground `≤250,000`; node+edge records `≤500,000`; canonical JSON `≤32 MiB` |
| Failure signal | stable `SkeletonGraphError.code`; localized CLI exit `2` |
| Cancellation | cooperative checks по bounded batches; partial graph/artifact не публикуется |
| Automatic fallback | другая adjacency, generic graph backend, bridge или route запрещены |
| Empty result | explicit empty components/nodes/edges; successful JSON/overlay diagnostic |
| Malformed result | broken chain/partition/component/contact contract fail closed |
| Recovery | изменить input/preprocessing и явно повторить invocation |

Canonical serialization и loop anchor не выбирают маршрут. Disconnected components сохраняются
раздельно; отсутствие PiecewiseCurve/forced route в FS-015 является scope boundary, а не degraded
implementation.
