# План работы ИИ

## Текущая цель

FS-013 и FS-014 завершены, проверены и fast-forward merged в локальный `main`. Работа остановлена
перед `FS-015`; новый product stage не активирован без отдельного разрешения пользователя.

## Следующий planned stage

- Stage ID: `FS-015`
- Lifecycle: `planned`; implementation не авторизована.
- Target branch: новая `feature/fs-015-skeleton-graph` только после явного продолжения.
- DAG: `FS-014 → FS-015`; skeleton implementation/evidence prerequisite выполнена.
- Entry evidence: binary skeleton output подтверждён; graph domain/adjacency decision ещё требуется
  спланировать и проверить до implementation.

## Integration state

- Локальный `main` содержит feature tip `eb71ec6` и post-merge status synchronization.
- `origin/main` остаётся на `c13f74d`; локальные commits ещё не опубликованы.
- Push/PR/release/deployment не выполнялись и требуют отдельного разрешения.

## Перед активацией FS-015

1. Получить явную команду продолжать разработку после merge/push handoff.
2. Прочитать только record `FS-015` в `prompts/STAGES.md`, затронутые SPEC и graph contracts.
3. Зафиксировать pixel adjacency, node/junction/loop/component semantics и bounded failure policy.
4. Создать feature branch и активировать stage selector/status до code changes.

## Handoff

Первое ещё не выполненное внешнее действие — push локального `main`, если пользователь его
разрешит. FS-015 остаётся planned и не должен начинаться автоматически.
