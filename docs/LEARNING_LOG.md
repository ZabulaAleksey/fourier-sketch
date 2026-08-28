# Учебный журнал Fourier Sketch

Здесь появляются только evidence-backed повторно полезные записи с полями Problem, Symptom,
Root cause, Failed attempts, Fix, Verification, Prevention и Links. Git history и обычный progress
сюда не копируются.

## 2026-08-28 — Fast-path не должен обходить численную валидацию

### Problem

- Full retained-energy ratio математически равен `1`, но исходная energy может не помещаться в
  finite `float` даже для coefficients с finite components.

### Symptom

- Full-selection fast-path возвращал `1.0`, тогда как тот же spectrum через `spectrum_energy`
  корректно давал typed overflow error.

### Root cause

- Algebraic shortcut выполнялся до проверки численной представимости denominator.

### Failed attempts

- N/A — дефект найден независимым read-only review до commit этапа.

### Fix

- Total energy валидируется до full/zero fast-path; добавлен regression test с `1e308` coefficient.

### Verification

```text
command / check: uv run pytest -q; uv run ruff check .; uv run mypy
result: PASS
scope: FS-004 unit/property/integration и full regression
caveat: limits остаются явной частью Python float/resource contract
```

### Prevention

- Любой shortcut для degenerate case выполняется только после тех validation checks, которые
  определяют допустимость общего результата.

### Links

- `src/fourier_sketch/math/metrics.py`
- `tests/unit/math/test_metrics.py`

## 2026-08-28 — Pseudo-locale должна быть безопасна для legacy console encoding

### Problem

- Expanded locale использовала Unicode brackets, которые Windows console с `cp1251` не могла
  вывести в live CLI E2E.

### Symptom

- PNG успешно создавался, но success message завершал process через `UnicodeEncodeError`.

### Root cause

- Diagnostic marker был визуально удобен, но не входил в гарантированный charset текущего
  console boundary.

### Failed attempts

- Первый live pseudo-locale E2E создал корректный artifact, но process вернул code `1` на print.

### Fix

- Pseudo/missing markers заменены на заметные ASCII `[!! … !!]` / `[missing:key]`; literals и
  placeholders продолжают проходить expansion/format tests.

### Verification

```text
command / check: uv run pytest -m e2e; uv run pytest tests/unit/presentation/test_i18n.py
result: PASS
scope: Windows live subprocess + resource formatting
caveat: additional production locales still require their own encoding/font/layout evidence
```

### Prevention

- Первый CLI surface проверяет не только resource lookup, но и фактическую запись localized output
  через platform-default subprocess console.

### Links

- `src/fourier_sketch/presentation/i18n.py`
- `tests/e2e/test_diagnostic_cli.py`

## 2026-08-28 — Численная и presentation boundaries требуют точных edge assertions

### Problem

- Формально правильный resampling и рабочий callback path теряли исходные coordinate invariants
  на крайних численных и presentation-сценариях.

### Symptom

- Subnormal open endpoint после interpolation становился `0`, а autoscale после первого press
  менял drawing transform так, что последующие реальные motion events оказывались вне axes.

### Root cause

- Последний open sample проходил через floating-point interpolation вместо точного source
  assignment; drawing axes не имели стабильной data-coordinate system на время capture.

### Failed attempts

- Первоначальный implementation прошёл обычные examples, но targeted Hypothesis и actual callback
  tests воспроизвели обе ошибки.

### Fix

- Open endpoints назначаются точно; drawing axes получают фиксированные limits до регистрации
  событий. Добавлены property и actual Matplotlib callback regression tests.

### Verification

```text
command / check: targeted FS-007 tests; uv run pytest; uv run ruff check .; uv run mypy
result: PASS
scope: resampling, capture, application pipeline, Matplotlib component/live E2E и CLI
caveat: uniform_index остаётся baseline; arc-length method относится к FS-009
```

### Prevention

- Для coordinate pipeline проверять не только приближённое значение, но exact endpoint/topology
  contracts и actual presentation callbacks со стабильным transform.

### Links

- `src/fourier_sketch/math/resampling.py`
- `src/fourier_sketch/render/matplotlib_freehand.py`
- `tests/property/test_resampling_properties.py`
- `tests/e2e/test_freehand_surface_e2e.py`
