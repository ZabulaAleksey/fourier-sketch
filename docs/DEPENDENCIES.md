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

## Текущая dependency surface (FS-012)

- build backend: Hatchling;
- runtime: NumPy `>=2.5.2` для explicit FFT adapter; Matplotlib `>=3.10.6` для diagnostic
  interactive/Agg adapters; Pillow `>=12.3.0` для allowlisted PNG/JPEG decode и bounded image
  transforms; `opencv-python-headless>=5.0.0.93,<6` только для explicit Canny adapter;
- development: pytest, Ruff, mypy, Hypothesis `>=6.165.10` для property contracts.

Lockfile exact versions являются воспроизводимым evidence. FS-002 review подтвердил Python 3.12,
Windows wheels и open-source license metadata: NumPy — BSD-compatible SPDX expression, Hypothesis —
MPL-2.0. FS-006 frozen lock установил Matplotlib `3.11.1`; package metadata подтверждает
Matplotlib license agreement (PSF-compatible), Python 3.12 и Windows wheel. Его direct/transitive
graph: contourpy, cycler, fonttools, kiwisolver, packaging, Pillow, pyparsing, python-dateutil и
six; локальная metadata review не обнаружила copyleft requirement для project code.

NumPy, Pillow и OpenCV objects не выходят через public application API; Hypothesis остаётся dev-only.
FS-010 повысил уже присутствовавший transitive Pillow до direct dependency и зафиксировал
12.3.0 в lockfile. Official package metadata подтверждает Python `>=3.10`, Windows wheels и
MIT-CMU license; project использует Python `>=3.12`. Official security guide подтверждает
content-based format detection и decompression-bomb warning/error semantics, поэтому adapter
дополнительно передаёт `formats=("PNG", "JPEG")`, превращает warning в error и применяет более
строгий project pixel limit до `load()`.

Review sources: [PyPI Pillow](https://pypi.org/project/pillow/),
[security guide](https://pillow.readthedocs.io/en/stable/handbook/security.html),
[format handbook](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html),
[ImageOps API](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html),
[MIT-CMU license](https://github.com/python-pillow/Pillow/blob/main/LICENSE).

FS-011 добавил direct `opencv-python-headless` и зафиксировал 5.0.0.93. Headless distribution
выбрана потому, что проект использует только local Canny и не нуждается в OpenCV GUI/Qt surface.
Official Canny contract требует 8-bit single-channel input и задаёт low/high, Sobel aperture и
L2-gradient flag; adapter валидирует эти параметры и same-sized binary output. PyPI metadata
подтверждает CPython ABI3 Windows wheels и Apache-2.0 package metadata; OpenCV core имеет
Apache-2.0, Python wrapper — MIT. Перед redistribution installer всё равно должен включить
third-party notices из фактического wheel/lock graph.

FS-012 не добавляет dependency: тот же headless OpenCV используется только для `findContours` с
`RETR_EXTERNAL` и `CHAIN_APPROX_NONE`; selection/normalization остаются project-owned Python code.
Official shape contract подтверждает, что `RETR_EXTERNAL` извлекает только крайние внешние contours,
а `CHAIN_APPROX_NONE` сохраняет все соседние contour points.

Review sources: [OpenCV 5.0 Canny documentation](https://docs.opencv.org/5.0/py_tutorials/py_imgproc/py_canny/py_canny.html),
[OpenCV structural analysis API](https://docs.opencv.org/5.0/main_modules/imgproc_shape.html),
[PyPI opencv-python-headless](https://pypi.org/project/opencv-python-headless/),
[OpenCV Apache-2.0 license](https://github.com/opencv/opencv/blob/4.x/LICENSE),
[opencv-python MIT license](https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt).

Direct scikit-image, PySide6 и animation codec dependencies добавляются только в первом stage
реального использования с tests и license/platform review.

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
