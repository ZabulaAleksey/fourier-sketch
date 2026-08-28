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
