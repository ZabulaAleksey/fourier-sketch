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
- FS-009 arc-length: cumulative/segment/output structures ограничены source `10000` и output
  `4096`; non-finite distance/sum/variance fail closed до публикации нового timeline;
- FS-010 image adapter: file size проверяется до read/decode, read ограничен `25 MiB + 1`, Pillow
  registry ограничен actual PNG/JPEG, decompression warnings становятся errors, dimensions
  проверяются до `load()` и после EXIF transpose; multiframe input не принимается;
- FS-011 boundary принимает только typed binary raster и explicit 4/8-connectivity; Canny принимает
  только typed grayscale raster, `0 ≤ low < high ≤ 255`, aperture `3|5|7` и boolean L2 flag;
- OpenCV output проверяется как same-sized `uint8` binary raster до публикации результата;
- FS-012 до contour extraction ограничивает edge map 250 000 foreground pixels, после backend —
  25 000 candidates и 100 000 aggregate points; превышение даёт typed `RESOURCE_LIMIT` до
  расширения raw coordinates в retained Python objects;
- contour backend output проверяется как integer `(N,1,2)`/`(N,2)`, внутри source bounds и с
  `CHAIN_APPROX_NONE` adjacency; points обязаны ссылаться на foreground source edge, а usable
  candidate — быть simple cycle без повторных pixels; malformed output не становится Curve;
- FS-014 принимает только typed binary raster, ограничивает foreground 4 000 000 pixels и
  проверяет bool dtype, same shape, output foreground subset и отсутствие solid `2×2` blocks до
  публикации skeleton;
- FS-015 принимает только typed `SkeletonizationResult`, снижает graph foreground budget до
  250 000 pixels, ограничивает node+edge records 500 000 и canonical JSON 32 MiB; adjacency matrix,
  all-pairs search, alternate graph backend и silent component bridge отсутствуют;
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

FS-010 diagnostic PNG полностью кодируется во временный sibling до публикации. Без `--overwrite`
destination создаётся одним exclusive hard-link operation и существующие данные не меняются; при
failure temp удаляется. Explicit overwrite использует atomic replace. CLI success/failure не
выводит source full path, pixels или EXIF payload.

FS-011 edge export переиспользует тот же FS-010 publication boundary. CLI success сообщает только
output basename, dimensions, selected algorithm/backend и aggregate edge count; raw pixels,
source path и backend exception detail не выводятся.

FS-013 не расширяет decoder/CV trust surface и сохраняет все FS-010–FS-012 budgets. Application
snapshot хранит config/result/frame, но не source path; presentation преобразует typed и unexpected
failures в стабильные resource keys без raw exception/native detail. Каждая operation получает
монотонную generation и отдельный cancel token: отменённый либо устаревший worker не может
опубликовать ready/empty/error поверх нового состояния. Headless output полностью кодируется во
temporary sibling, existing destination без `--overwrite` сохраняется, а отображаемый basename
экранирует control/format/surrogate/bidi code points.

Local-path guard является lexical defense-in-depth и не доказывает, что mapped drive либо
reparse/symlink target физически local. Для explicit user-selected desktop path это принятo как
residual risk FS-013; строгий no-network I/O contract, если он потребуется, должен получить
platform-aware resolution и negative evidence в FS-023.

FS-014 переиспользует тот же local-path и atomic PNG boundary. Controller не хранит source path,
late/cancelled result не публикуется, а CLI показывает только escaped basename и aggregate counts.
Preview и skeleton mode создают ровно один user-selected artifact за invocation; resource/backend
failure не оставляет partial output и не изменяет существующий destination без `--overwrite`.

FS-015 JSON и overlay используют тот же lexical local-path boundary и sibling temporary file.
No-overwrite publication выполняется atomic hard-link, overwrite — explicit `os.replace`; JSON
сериализуется только после topology validation и до publication. CLI сообщает только escaped
basename и aggregate topology counts, не source path, raster payload или raw exception.

## Dependencies and supply chain

Canonical manager/lockfile определены в `docs/DEPENDENCIES.md`. Новые CV/UI/codec dependencies
получают maintenance/license/platform review в своём stage. Install/build scripts не выполняются
из untrusted project/session input.

`opencv-python-headless` 5.0.0.93 выбран для Canny без GUI/Qt surface. Adapter загружается лениво,
не исполняет shell/subprocess и не принимает plugin name от пользователя; malformed/throwing
backend output становится typed `BACKEND_FAILURE` без partial result или fallback. Любой обычный
import-time exception становится privacy-safe `BACKEND_UNAVAILABLE`; version допускается только
как bounded ASCII identifier и сверяется с algorithm-specific provenance contract до CLI output.

`scikit-image` 0.26.0 выбран для explicit Lee thinning и загружается лениво. Adapter не принимает
backend/method name из input, допускает только bounded `0.26.x` version и валидирует native output;
unavailable/incompatible/malformed backend не переключается на Zhang/OpenCV и не раскрывает raw
exception. Frozen lock и фактический Windows wheel входят в dependency evidence FS-014.

## Privacy and logging

Default processing local-only. Logs могут содержать operation ID, stage, dimensions, algorithm,
duration, error code и basename only when needed; они не содержат pixel data, raw curve samples,
full coefficient arrays, secrets или full path by default. Export/session persistence получает
отдельный retention contract до реализации.

FS-012 success summary показывает только basename; Unicode control/format/surrogate и bidi
characters экранируются как `\\uXXXX`/`\\UXXXXXXXX`, чтобы filename не менял terminal/log display.

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
- FS-011: unavailable/malformed Canny, invalid parameters, algorithm selection, privacy и
  overwrite проходят unit/component/live E2E checks без algorithm substitution;
- FS-012: dense input, excessive candidate count, unavailable/malformed contour backend,
  degenerate/no-contour, privacy, inactive options и existing output проходят negative tests;
- FS-014: foreground budget, cancellation/stale suppression, unavailable/malformed Lee backend,
  empty result, preview/export race, corrupt input и existing output проходят unit/component/E2E;
- FS-015: reduced graph/record/JSON budgets, exact ownership validation, cancellation, corrupt/path
  privacy, atomic JSON/PNG no-overwrite и отсутствие cross-component edge;
- dependency: frozen clean restore and lockfile review;
- logging review: no sample/image/full-path leakage in failure fixtures.

Stages `FS-010`–`FS-015` have live decode/CV/graph/overwrite/privacy evidence; Stage `FS-022`
cannot complete without overwrite/partial-output/codec-failure evidence.
