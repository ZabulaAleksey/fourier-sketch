# Системная спецификация Fourier Sketch

Статус: Принята как исходный контракт
Версия: 0.1

## 1. Назначение

Система позволяет пользователю получить упорядоченную плоскую кривую из мышиного ввода или
изображения, представить её комплексным сигналом, вычислить Fourier spectrum и увидеть, как
head-to-tail цепочка вращающихся vectors воспроизводит кривую следом своего последнего endpoint.

## 2. Область

- single и piecewise planar curves;
- reference DFT, NumPy FFT, IDFT, spectrum и partial reconstruction;
- epicycle math, diagnostic renderer и desktop UI;
- freehand и локальные PNG/JPEG inputs;
- preprocessing, contours, skeleton graph и routing policies;
- discontinuity analysis и отдельный 2D image FFT mode;
- экспорт данных, изображений и animation.

## 3. Вне области

- гарантированно идеальная трассировка произвольной фотографии;
- гарантированно оптимальный single-stroke route для любого графа;
- cloud/backend, совместное редактирование и сетевой upload;
- смешивание 1D complex curve Fourier с 2D image FFT;
- функции будущего stage в acceptance contract более раннего stage.

## 4. Участники и предпосылки

- `User` рисует, выбирает локальный файл, параметры и export destination.
- `System` валидирует ввод, строит выбранный pipeline и показывает диагностируемый результат.
- `Developer` использует pure mathematical contracts и reproducible project commands.

Для Fourier pipeline существует хотя бы один допустимый sample. Для image pipeline файл должен
пройти проверку размера и реальное декодирование поддерживаемого формата.

## 5. Функциональные требования

### FR-CURVE-001 — Кривая

Система должна хранить упорядоченные `Point2D` как open/closed `Curve` и несколько независимых
segments как `PiecewiseCurve`, не создавая скрытый bridge между segments.

### FR-DRAW-001 — Freehand

Система должна преобразовать mouse path в валидированную curve, resampling, Fourier spectrum,
epicycle chain и endpoint trace.

### FR-IMPORT-001 — Image input

Система должна загружать локальные PNG/JPEG, выполнять диагностируемые grayscale/denoise/
threshold/edge steps и передавать binary result в последующие contour stages.

### FR-FOURIER-001 — Единая convention

Все 1D curve modules должны использовать DFT/IDFT convention из `docs/MATHEMATICS.md`, signed
frequencies и одинаковую normalization.

### FR-HARMONICS-001 — Partial reconstruction

Система должна выбирать не менее одного coefficient по signed frequency, absolute frequency,
amplitude-descending, interleaved order или explicit set и вычислять error metrics.

### FR-EPICYCLE-001 — Vector chain

Каждый selected coefficient должен стать rotating vector; первый начинается в configured origin,
а каждый следующий — в конце предыдущего. Rendering toggles не меняют mathematical state.

### FR-EPICYCLE-TRACE-001 — Drawing point

В animation mode drawing point и новая точка persistent trace должны быть равны фактическому
endpoint последнего vector. Независимый decorative reconstruction path запрещён.

### FR-ROUTING-001 — Contour policies

Система должна различать dominant contour, all disconnected components, forced continuous route
и piecewise route. Искусственные bridges должны иметь явное происхождение и cost.

### FR-DISCONTINUITY-001 — Разрывы

Система должна поддерживать strict Fourier trajectory discontinuous signal и отдельную
`PEN_UP_RENDERING` policy, которая не изменяет coefficients.

### FR-DISCONTINUITY-ANALYSIS-001 — Измеряемый spectrum sweep

Для recorded discontinuous spectrum система должна публиковать amplitude и controlled log
amplitude, а для каждого explicit K — retained energy и reconstruction error с зафиксированным
ordering. K values уникальны, bounded и deterministic; zero amplitude не создаёт NaN/Inf. Chart и
continuous comparison являются views над immutable numeric result и не вводят theorem claims.

### FR-FFT2-001 — 2D image Fourier

Система должна реализовать FFT2 как отдельный mode с magnitude, phase, filters и reconstruction,
используя dedicated immutable raster/spectrum types. Convention: NumPy backward normalization,
axes `(row, column)`, centered `fftshift` visualization и unshifted coefficients for IFFT2.
Constant/impulse/sinusoid и real-image round trip должны иметь explicit tolerance; low/high-pass и
selected-frequency masks записывают policy/parameters и не используют 1D `FourierSpectrum` или
epicycle domain types как 2D frequency model.

### FR-DIAGNOSTICS-001 — Наблюдаемость результата

Каждый image transform, spectrum, selected coefficient set, metrics и export failure должны иметь
диагностируемое состояние без логирования пользовательского payload.

### FR-EXPORT-001 — Export

Система должна экспортировать поддерживаемые curves, coefficients, plots, images и animation.
Animation export использует тот же chain state и endpoint history, что интерактивный renderer.

### FR-I18N-001 — Пользовательские строки

Первая user-facing surface должна использовать resource keys, production locale `en`, fallback
locale `en` и pseudo-locale для проверки text expansion. Язык проектной документации не задаёт
product locale.

## 6. Нефункциональные требования

### NFR-NUM-001 — Численная корректность

Reference cases, round-trip, analytical fixtures и property tests должны проверять результат с
явными absolute/relative tolerances; NaN/Inf и degenerate input не скрываются renderer-ом.

### NFR-ARCH-001 — Границы

Domain/math не импортируют UI, OpenCV или renderer. Event handlers и paint callbacks не содержат
Fourier/CV logic.

### NFR-REPRO-001 — Воспроизводимость

Python 3.12+, `pyproject.toml` и `uv.lock` являются dependency source of truth; clean restore
должен проходить через документированную команду.

### NFR-UI-001 — Responsiveness

Длительные image/Fourier/export operations не блокируют GUI thread и поддерживают progress,
cancellation и понятный failure state.

### NFR-PORT-001 — Переносимость

Paths строятся через `pathlib`; Windows является первым проверяемым desktop environment, но
архитектура не содержит machine-specific абсолютных путей.

## 7. Требования безопасности

### SEC-INPUT-001

Локальный image input ограничен 25 MiB encoded и 40 million decoded pixels; формат определяется
безопасным decode, а не расширением. Oversized, corrupted и unsupported inputs fail closed.

### SEC-RESOURCE-001

До allocation система валидирует sample/harmonic/image dimensions; interactive harmonic count не
превышает `min(N, 4096)` без отдельного non-interactive explicit mode и evidence.

### SEC-PATH-001

Export не выполняет shell interpolation, не перезаписывает существующий файл без явного решения
пользователя и сообщает о partial output без ложного success.

### SEC-PRIVACY-001

Изображения, curves и exports остаются локальными по умолчанию; logs не содержат file content,
complex samples или full user paths без диагностической необходимости.

## 8. Основные сценарии

1. User рисует curve → resampling → DFT → selected harmonics → rotating chain → last endpoint
   формирует trace.
2. User выбирает image → validated decode → intermediate transforms → contour/route → Fourier →
   epicycle endpoint trace.
3. User меняет harmonic count/order/display toggles → math selection или rendering меняются в
   своих границах → endpoint equivalence сохраняется.
4. User экспортирует animation → экспорт использует те же chain states и endpoint history.

## 9. Ошибки и граничные случаи

- empty mouse input не создаёт curve и получает понятный no-input state;
- one-point curve допустима как DC-only signal; zero-length resampling сообщает typed error;
- duplicates могут сохраняться до cleanup, но не приводят к division by zero;
- no-contour, disconnected components, invalid image, cancellation и unavailable codec не
  маскируются автоматическим silent fallback;
- explicit jump остаётся jump в model; pen-up влияет только на stroke rendering.

## 10. Критерии приёмки системы

- AC-SYS-001: `IDFT(DFT(z)) ≈ z` на synthetic и generated finite samples.
- AC-SYS-002: circle fixture имеет ожидаемую dominant signed harmonic при зафиксированной
  orientation convention.
- AC-SYS-003: `chain.endpoint(t) ≈ reconstruction(t)` для одинакового coefficient set.
- AC-SYS-004: animation trace состоит только из фактических endpoint states.
- AC-SYS-005: ordering меняет geometry цепочки, но не математическую сумму.
- AC-SYS-006: image intermediate results доступны diagnostic/export boundary.
- AC-SYS-007: disconnected contours не получают неявный bridge.
- AC-SYS-008: FFT2 API и data model отделены от 1D epicycles.
- AC-SYS-009: export animation воспроизводит интерактивный vector-chain behavior.
- AC-SYS-010: каждый stage имеет runnable slice, PASS evidence и не зависит от future stage.
- AC-SYS-011: user-facing strings проходят default/fallback/pseudo-locale checks.
- AC-SYS-012: security/resource limits дают контролируемый отказ.

## 11. Связь с feature-SPEC и tests

| Требования | Детализация | Планируемое evidence |
|---|---|---|
| FR-CURVE/FOURIER/HARMONICS | `features/fourier-core.spec.md` | unit + property + integration |
| FR-EPICYCLE/TRACE | `features/epicycle-animation.spec.md` | property + component + E2E |
| FR-IMPORT/ROUTING/DISCONTINUITY | `features/image-to-curve.spec.md` | unit + integration + E2E |
| FR-I18N/EXPORT | `features/desktop-export.spec.md` | component + integration + E2E |

## 12. Открытые вопросы

- Поддерживаемые production locales после `en` не утверждены.
- MP4 codec/backend и packaging targets выбираются в соответствующих stages после capability
  и license review.
- Performance budgets для large-N batch mode уточняются Stage `FS-023`; interactive security
  caps выше действуют до отдельного SPEC/ADR change.

## 13. История изменений

- 2026-08-28: v0.1 — контракт извлечён из утверждённого пользовательского brief для bootstrap.
