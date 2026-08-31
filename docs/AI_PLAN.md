# План работы ИИ

## Текущая цель

Реализовать отдельный проверяемый FS-027 Curve Simplification slice поверх завершённых
parameterization/image MVP и hardening contracts.

## Активный stage

- Stage ID: `FS-027`
- Lifecycle: `completed`; automated gates PASS and independent review GO on the working branch,
  awaiting the already-authorized MDP publication.
- Prerequisites: FS-023, FS-009 and FS-013 are `completed` and published in `origin/main`.
- Contract: simplify curve geometry under explicit bounded/error semantics without changing the
  canonical Fourier pipeline or starting adaptive sampling FS-028.

## Integration state

- `main` содержит завершённый FS-021, включая renderer-control `0faf8fc`, последующие UI commits
  `644fd82`/`7d53100`/`66ec1ef`/`7cf355d`, touch/rainbow `cb323e2` и fixed-center canvas
  maintenance `02c026b`, завершённый FS-023 `a2d7a2c` и FS-024 `e480382`.
- `main` с FS-024 опубликован в `origin/main`. PR, release и deployment не выполнялись.
- FS-025 commit `517b7d8` интегрирован в `main` и опубликован в `origin/main`; ветка stage удалена.
- FS-026 commit `fe46cac` интегрирован в `main` и опубликован в `origin/main`; ветка stage удалена.

## План выполнения

1. [completed] Прочитать exact FS-027 contract и зафиксировать simplification/error/budget semantics.
2. [completed] Реализовать только FS-027 vertical slice без FS-028+.
3. [completed] Выполнить targeted/full/static/overlay gates, independent review и documentation sync.
4. [in_progress] Создать атомарный commit и выполнить разрешённый МДП.

## Handoff

FS-027 validated на рабочей ветке; следующий шаг — атомарный commit и разрешённый МДП. Не начинать
FS-028/FS-030/mobile/basis scope до интеграции.
