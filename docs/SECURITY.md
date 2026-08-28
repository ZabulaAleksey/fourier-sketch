# Security baseline Fourier Sketch

## Поверхность и модель угроз

Приложение локальное, без backend/auth (`BDX-L0`). Основные недоверенные входы:

- bytes и metadata выбранного PNG/JPEG;
- mouse samples и числовые параметры;
- filenames/export destinations;
- optional CV/codec backend и subprocess result;
- session/project data, если persistence появится позднее.

Сетевой upload, remote URL import и telemetry отсутствуют в текущем scope. Их появление требует
отдельной SPEC/security review.

## Input validation

- encoded image: максимум 25 MiB;
- decoded image: максимум 40,000,000 pixels до полной materialization downstream arrays;
- format подтверждается decoder-ом и allowlist PNG/JPEG, не extension/MIME hint;
- corrupt, truncated, decompression-bomb и unsupported input fail closed;
- numeric input проверяет finite values, ranges и allocation estimate;
- interactive harmonics: `1..min(N, 4096)`; larger batch mode требует explicit command и budget;
- FS-004 batch reconstruction: максимум `262144` output samples и `16777216` evaluated terms;
- FS-006 timeline: maximum speed `100`, trace `10000` points, headless frames `1..9999`;
- FS-007 freehand: максимум `10000` принятых pointer points и `4096` resampled points; budget
  проверяется до дальнейшего накопления/FFT, а consecutive duplicates игнорируются;
- filenames/metadata не интерпретируются как code, format string или shell fragment.

## Resource exhaustion

Каждый heavy stage определяет time/memory/sample budget, cancellation и failure state до
terminal completion. GUI не запускает overlapping conflicting jobs. Arrays/frames не накапливаются
без bounded policy; animation export использует bounded streaming/frame plan. Infinite retry
запрещён.

## Filesystem и export

- paths обрабатываются через `pathlib` и platform dialogs;
- существующий destination не перезаписывается без explicit user confirmation;
- safe write использует temporary sibling + atomic replace только после successful encode, если
  filesystem это поддерживает;
- partial/temp artifact при failure классифицируется и сообщается; unrelated files не удаляются;
- external encoder вызывается argument list без shell interpolation;
- project never writes outside user-selected destination implicitly.

FS-006 diagnostic PNG принимает только explicit `.png` path с существующим parent. Encode идёт во
temporary sibling, затем destination резервируется через exclusive create и публикуется atomic
replace; existing destination без отдельного overwrite decision не меняется. CLI не предоставляет
overwrite flag и сообщает только basename, не полный path.

FS-007 Matplotlib adapter принимает только finite data coordinates из своих drawing axes и только
left-button stroke. Events вне axes, invalid collaborators/options и превышение capture budget
завершаются без создания timeline; raw pointer samples не выводятся в status/CLI errors.

## Dependencies and supply chain

Canonical manager/lockfile определены в `docs/DEPENDENCIES.md`. Новые CV/UI/codec dependencies
получают maintenance/license/platform review в своём stage. Install/build scripts не выполняются
из untrusted project/session input.

## Privacy and logging

Default processing local-only. Logs могут содержать operation ID, stage, dimensions, algorithm,
duration, error code и basename only when needed; они не содержат pixel data, raw curve samples,
full coefficient arrays, secrets или full path by default. Export/session persistence получает
отдельный retention contract до реализации.

## Failure and fallback invariants

- validation/integrity/resource-limit failure → fail closed;
- unavailable optional backend → explicit unavailable/degraded state после capability check;
- silent algorithm/codec fallback запрещён;
- partial output не считается complete;
- retry разрешён только для demonstrably transient idempotent operation; local deterministic
  decode/validation error не retry-ится.

Project-specific fallback chains уточняются в stage/ADR при выборе actual backends; глобальная
Fallback Policy наследуется и здесь не копируется.

## Security acceptance evidence

- unit: limits, finite/range validation, spoofed extension, path decision logic;
- integration: decoder rejects corrupt/oversized payload before unsafe processing;
- component: user sees validation/cancel/export overwrite states;
- E2E: representative invalid image and existing destination do not crash or lose data;
- dependency: frozen clean restore and lockfile review;
- logging review: no sample/image/full-path leakage in failure fixtures.

Stage `FS-010` cannot complete without live decode/limit evidence; Stage `FS-022` cannot complete
without overwrite/partial-output/codec-failure evidence.
