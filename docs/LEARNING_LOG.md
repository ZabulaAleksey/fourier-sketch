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
