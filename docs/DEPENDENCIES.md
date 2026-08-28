# Dependency contract Fourier Sketch

## Canonical ecosystem

| Поле | Значение |
|---|---|
| Python | `>=3.12` |
| Manager | `uv` |
| Manifest | `pyproject.toml` |
| Lockfile | `uv.lock` |
| Source of truth | manifest intent + generated lockfile graph |
| Shared storage | standard machine-level uv cache |
| Project materialization | isolated `.venv/` (ignored by Git) |
| Clean restore | `uv sync --all-groups --frozen` |
| CI restore | `uv sync --all-groups --frozen` (CI not yet configured) |

Competing `requirements*.txt`, `poetry.lock`, Pipenv or conda lockfiles запрещены без отдельного
documented migration/exception.

## Stage FS-000 dependency surface

- build backend: Hatchling;
- development: pytest, Ruff, mypy;
- runtime: none.

Lockfile exact versions являются воспроизводимым evidence. Runtime NumPy, property-test Hypothesis,
Pillow/OpenCV/scikit-image, matplotlib, PySide6 и animation codec dependencies добавляются только
в первом stage реального использования с tests и license/platform review.

## Cleanup classification

- `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, build/dist/coverage —
  `REBUILDABLE`, ignored, удаляются только по explicit scoped need;
- uv shared cache — `EXPENSIVE_CACHE`, не project state и не очищается project command-ом;
- source, specs, fixtures, manifests/lockfile — `REQUIRED_RUNTIME/SOURCE`, tracked;
- user images, sessions и exports — `USER_DATA`, никогда не очищаются tooling-ом автоматически.

## Change process

1. Указать problem/capability текущего stage.
2. Проверить stdlib/existing alternative, maintenance, license, security и platform support.
3. Изменить `pyproject.toml`, затем сгенерировать `uv.lock` через `uv` (не hand-edit).
4. Выполнить frozen sync, relevant tests/lint/type/component/build.
5. Проверить diff dependency graph и документацию.

Unavailable package/network или failed graph verification останавливают change; manager не
переключается silently. Dependency-manager exception: none.
