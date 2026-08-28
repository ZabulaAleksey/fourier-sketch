# Context compatibility — Fourier Sketch

Repository классифицирован как GREENFIELD; brownfield reconciliation не применяется. Matrix
фиксирует project overlay choices и не является live inventory global ДЕВ.

| Возможность | Глобально / в brief | Потребность проекта | Статус | Канонический источник |
|---|---|---|---|---|
| DEV/KARKAS workflow | global Skills, rules, validators | staged project routing | `INHERITED` | `~/.codex`; thin `AGENTS.md` delta |
| Git/testing/review/security/fallback | global policies | project-specific contracts only | `INHERITED` | global policy + `docs/SECURITY.md`/`TESTING.md` |
| Project agents/hooks/MCP/Skills | global mechanisms sufficient | no confirmed gap | `INHERITED` | no local copy created |
| Requirements | attached brief | clone-restorable stable contract | `PROJECT_ONLY` | `specs/*.spec.md` |
| Prompt catalog | brief contains many prompts | one detailed stage source | `PROJECT_ONLY` | `prompts/STAGES.md` |
| Root `ARCHITECTURE.md`, `AI_*`, `ROADMAP.md` suggested by brief | global governance requires canonical docs paths | avoid parallel roles | `CONFLICT → PROJECT_ONLY` | mapped to `docs/*.md` |
| `LEARNING.md` | brief name | canonical evidence-backed learning log | `CONFLICT → PROJECT_ONLY` | `docs/LEARNING_LOG.md` |
| `ERROR_LOG.md` | brief requests routine error log | active blockers in status; reusable failures in learning | `OBSOLETE` | no empty duplicate created |
| `DEV_LOG.md` | brief requests routine chronology | Git + status sufficient at bootstrap | `OBSOLETE` | create only if distinct trace need appears |
| Dependency stack | Python ecosystem | reproducible manager/lock | `PROJECT_ONLY` | `pyproject.toml`, `uv.lock`, `docs/DEPENDENCIES.md` |
| Product i18n | inherited global policy | initial locale/fallback/pseudo delta | `EXTEND` | SPEC, `docs/DESIGN.md`, ADR-005 |

Никакая global capability не скопирована. Machine-local prompt path, generic agents, hooks, MCP и
Codex config не добавлены.
