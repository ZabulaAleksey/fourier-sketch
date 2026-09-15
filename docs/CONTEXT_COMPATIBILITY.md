# Context compatibility — Fourier Sketch

При bootstrap repository был GREENFIELD, и brownfield reconciliation тогда
не применялся. Ниже сохранены исходные project overlay choices; текущая
state-location migration повторно сверена как brownfield в отдельном разделе.

| Возможность | Глобально / в brief | Потребность проекта | Статус | Канонический источник |
|---|---|---|---|---|
| DEV/KARKAS workflow | global Skills, rules, validators | staged project routing | `NO_FORMAL_BRIDGE` | global Codex user layer + project `AGENTS.md`; no `.codex/dev-project.toml` |
| Git/testing/review/security/fallback | global policies | project-specific contracts only | `INHERITED` | global policy + `docs/SECURITY.md`/`TESTING.md` |
| Project agents/hooks/MCP/Skills | global mechanisms sufficient | no confirmed gap | `INHERITED` | no local copy created |
| Requirements | attached brief | clone-restorable stable contract | `PROJECT_ONLY` | `specs/*.spec.md` |
| Historical stage catalog | brief contains many prompts | preserve unique old contracts without second live state | `PROJECT_ONLY` | `docs/notes/legacy-stage-contracts.md`; current owner `docs/STAGES.md` |
| Root `ARCHITECTURE.md`, `AI_*`, `ROADMAP.md` suggested by brief | global governance requires canonical docs paths | avoid parallel roles | `CONFLICT → PROJECT_ONLY` | mapped to `docs/*.md` |
| `LEARNING.md` | brief name | canonical evidence-backed learning log | `CONFLICT → PROJECT_ONLY` | `docs/LEARNING_LOG.md` |
| `ERROR_LOG.md` | brief requests routine error log | active blockers in status; reusable failures in learning | `OBSOLETE` | no empty duplicate created |
| `DEV_LOG.md` | brief requests routine chronology | Git + status sufficient at bootstrap | `OBSOLETE` | create only if distinct trace need appears |
| Dependency stack | Python ecosystem | reproducible manager/lock | `PROJECT_ONLY` | `pyproject.toml`, `uv.lock`, `docs/DEPENDENCIES.md` |
| Product i18n | inherited global policy | initial locale/fallback/pseudo delta | `EXTEND` | SPEC, `docs/DESIGN.md`, ADR-005 |

Никакая global capability не скопирована. Machine-local prompt path, generic agents, hooks, MCP и
Codex config не добавлены.

## Brownfield state-location migration

Read-only `reconcile_project_framework.py` повторён на GitHub `main`
`04cdf13` в clean isolated clone. `prompts/STAGES.md`, AI_PLAN и AI_STATUS
классифицированы `MERGE`; `docs/STAGES.md` — `ADD`. Product code/tests,
fixtures, uv.lock, Android/Gradle files и runtime state защищены как
`FORBIDDEN_TO_OVERWRITE`. Snapshot SHA256 и rollback parent сохранены
в `docs/notes/legacy-ai-state-evidence.md`.

Old AI_PLAN выбирал completed FS-031; AI_STATUS заявлял active none и
FS-031 terminal gates, а старый detailed catalog содержал все FS-000–033
contracts без live selector. Совместимое решение: selected `FS-031`
остаётся `completed`, NEXT ждёт явного выбора нового stage, historical
contracts сохраняются в docs/notes, current owner — `docs/STAGES.md`.
Full DEV opt-in `.codex/dev-project.toml` отсутствует, поэтому
глобальный overlay validator не может утверждать formal policy
inheritance от одного пути; stage adapter проверяется отдельно.

Baseline после migration: frozen uv restore — 38 packages;
Python regression suite — 729 PASS с task-local basetemp, Ruff PASS,
strict mypy PASS для 252 source files; canonical stage adapter PASS
с `FS-031`/`completed`/checkpoint/evidence/NEXT. Исходная первая
попытка pytest была заблокирована системным Temp ACL до теста;
task-local basetemp устранил environmental failure.
