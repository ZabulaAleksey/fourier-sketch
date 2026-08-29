# План работы ИИ

## Текущая цель

Реализовать FS-017 как explicit forced continuous routing policy с измеримыми duplication/bridge
costs, не изменяя честную FS-016 PiecewiseCurve semantics и не переходя к FS-018 Fourier.

## Активный stage

- Stage ID: `FS-017`
- Lifecycle: `completed`; terminal evidence собрано 2026-08-29.
- Branch: `feature/fs-017-forced-routing`, создана от validated FS-016 tip `721694d`.
- DAG: `FS-016 → FS-017`; explicit disconnected segment representation completed.
- Contract: forced route opt-in only; shared raw adjacency, exact Euler where valid, linear
  spanning-tree T-join otherwise, cyclic explicit bridges, original/duplicated/bridge provenance
  and costs observable; no silent mutation of PiecewiseCurve.

## Integration state

- FS-015..FS-017 form an unmerged branch chain above `main`/`origin/main@aba291d`.
- Merge/push/PR/release/deployment не выполнялись.

## План выполнения

1. Вынести shared raw adjacency helper с FS-015 parity regression.
2. Реализовать Hierholzer + spanning-tree T-join и cyclic component bridges как explicit route.
3. Добавить diagnostic overlay/CLI и live branched multi-component E2E.
4. Закрыть review/full/static/overlay gates и синхронизировать documentation evidence.

## Handoff

Создать atomic FS-017 commit и перейти к отдельной активации FS-018 без merge/push.
