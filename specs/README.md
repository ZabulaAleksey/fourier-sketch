# Индекс спецификаций Fourier Sketch

| SPEC | Статус | Назначение |
|---|---|---|
| `system.spec.md` | Принята, v0.1 | Границы продукта, сквозные требования и acceptance contract |
| `features/fourier-core.spec.md` | Принята, v0.1 | Curve, DFT/FFT, spectrum, reconstruction и metrics |
| `features/basis-decomposition.spec.md` | Принята, planned FS-032 | Explicit Fourier/Haar basis selection and basis-specific reconstruction |
| `features/basis-playground.spec.md` | Принята, planned FS-033 | DCT-II/Walsh reconstruction and manual Fourier harmonic authoring |
| `features/epicycle-animation.spec.md` | Принята, v0.1 | Head-to-tail vectors, endpoint equivalence и trace |
| `features/image-to-curve.spec.md` | Принята, v0.1 | Недоверенные изображения, contours, routing и discontinuities |
| `features/desktop-export.spec.md` | Принята, v0.1 | Desktop UI, i18n boundary и exports |
| `features/android-touch.spec.md` | Принята, v0.1 | Offline Android touch input и epicycle animation |

Требования имеют устойчивые IDs. `prompts/STAGES.md` определяет порядок реализации, но не
переопределяет SPEC. Planned path или test name в traceability не является evidence реализации.
