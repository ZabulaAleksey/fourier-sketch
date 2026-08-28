# Журнал архитектурных решений

## 2026-08-28 — ADR-001: Полный staged overlay без ранней product implementation

**Контекст:** Пользовательский brief описывает большой pipeline и прямо запрещает реализовывать
все функции одновременно.

**Решение:** Создать GREENFIELD repository как полный ДЕВ / КАРКАС overlay. Stage `FS-000`
содержит package/tooling/docs/smoke scaffold; первый product stage — `FS-001` и требует отдельного
запуска. `prompts/STAGES.md` — единственный detailed stage source.

**Рассмотренные альтернативы:** Сразу реализовать MVP; создать только README; копировать каждый
prompt отдельным файлом.

**Последствия:** Контекст больше минимального скрипта, но требования, DAG и completion evidence
разделены. Empty product directories и speculative code не создаются.

**Миграция / откат:** Удаление overlay не требуется; отдельный stage может быть пересмотрен через
SPEC/ADR до начала реализации.

## 2026-08-28 — ADR-002: Единая complex DFT convention

**Контекст:** Несогласованные signs/normalization ломают reconstruction и epicycle equivalence.

**Решение:** Использовать forward factor `1/N` и negative exponential, inverse positive
exponential без дополнительного factor; even-N Nyquist label — `-N/2`. Полный контракт хранится в
`docs/MATHEMATICS.md`.

**Рассмотренные альтернативы:** NumPy raw index convention без signed domain labels; symmetric
normalization; positive exponent forward transform.

**Последствия:** Все adapters сериализуют signed frequency явно. Любое изменение — breaking
mathematical contract с migration тестов/exports.

**Миграция / откат:** До product data нет миграции. После появления exports потребуется versioned
format и explicit converter.

## 2026-08-28 — ADR-003: Trace только из фактического chain endpoint

**Контекст:** Независимое вычисление decorative reconstruction может визуально расходиться с
показанной vector chain.

**Решение:** Math layer создаёт `EpicycleChainState`; interactive и exported trace append только
`state.endpoint`. Renderer не вычисляет coefficients/reconstruction.

**Рассмотренные альтернативы:** Отдельный fast reconstruction path в renderer; заранее
вычисленная polyline поверх декоративных circles.

**Последствия:** `BH-EPICYCLE-TRACE-001` становится property/integration/E2E contract. Performance
оптимизация обязана сохранять тот же state provenance.

**Миграция / откат:** Alternative renderer допустим только как adapter к тому же chain state.

## 2026-08-28 — ADR-004: `uv` и just-in-time dependencies

**Контекст:** Проект выбирает Python 3.12+ и требует воспроизводимого окружения, но поздние CV/UI
libraries не нужны bootstrap.

**Решение:** `uv` + `pyproject.toml` + `uv.lock` — единственный dependency contract. На FS-000
добавляются только build/test/lint/type tools. NumPy, Hypothesis, matplotlib, Pillow/OpenCV и
PySide6 добавляются в stage фактического использования после capability/license review.

**Рассмотренные альтернативы:** pip/requirements; добавить весь предполагаемый stack сразу;
Poetry.

**Последствия:** Lockfile изменяется по stages, dependency surface остаётся минимальной.

**Миграция / откат:** При несовместимости сохраняется текущий lockfile; silent switch manager
запрещён.

## 2026-08-28 — ADR-005: Initial product locale `en`

**Контекст:** Project context ведётся на русском, но user-facing desktop surface должна иметь
явный language/locale contract до первой строки UI.

**Решение:** Начальная production locale и fallback — `en`; strings живут в resources,
pseudo-locale проверяет expansion/missing keys. Дополнительные production locales не обещаны.

**Рассмотренные альтернативы:** Hardcoded English; использовать язык project docs как locale;
сразу поддержать `ru`/`uk` без утверждённых переводов.

**Последствия:** Stage `FS-006` включает минимальную рабочую locale boundary; Stage `FS-021`
расширяет её, но не создаёт впервые.

**Миграция / откат:** Новая locale добавляется ресурсами и tests без изменения math/application.
