# Project context — Fourier Sketch

## Устойчивые факты

- Repository: независимый product Git root `~/codex-workspace/fourier-sketch`.
- Classification: `GREENFIELD`, full staged ДЕВ overlay.
- Complexity: `COMPLEX`; mode: production-oriented staged development.
- Current SDLC at bootstrap: specification + architecture.
- Domains: scientific computing, computer vision, desktop visualization.
- Stack: Python 3.12+; actual FS-000 runtime dependencies отсутствуют.
- Backend DX: `BDX-L0` — backend/runtime service отсутствует.
- Monitoring class: `active` во время явной разработки; внешняя automation не настроена.
- First validated desktop environment: Windows; paths обязаны оставаться portable.

Исходный пользовательский brief от 2026-08-28 преобразован в repository SPEC/stages. Project не
зависит от machine-local attachment или истории чата для восстановления контекста.

## Product facts

- 1D curve signal: `z(t)=x(t)+iy(t)`.
- Canonical formulas: `docs/MATHEMATICS.md`.
- Critical visual contract: last chain endpoint is animation drawing point.
- Initial product locale/fallback: `en`; project documentation language: Russian.
- Local-first processing; network/cloud/auth не входят в approved scope.

## Tooling facts

- Dependency manager: `uv`; lockfile: `uv.lock`; environment: `.venv`.
- Tests: pytest; lint: Ruff; types: mypy.
- Project-specific agents/hooks/MCP/Skills/Codex config: none.
- Global Git/testing/security/fallback/model-routing workflows are inherited.

## Open project decisions

- exact CV backend combination выбирается when `FS-010`/`FS-011` begins;
- PySide6 introduction and packaging proof occur in `FS-021`/`FS-023`;
- MP4 encoder/backend is unresolved until `FS-022` capability/license evidence;
- additional production locales require explicit product decision.
