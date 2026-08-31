# Feature SPEC — Android Touch-to-Epicycles

Статус: Принята, v0.2; реализация FS-031 validated

## Назначение и область

Определить будущий offline Android-клиент, в котором пользователь рисует curve пальцем, а
приложение использует ту же Fourier convention и epicycle invariants, чтобы анимировать
head-to-tail vectors и фактический endpoint trace. Технология mobile adapter выбирается по
capability/performance/packaging evidence; упоминание React Native не является решением само по себе.

## Принятый mobile contract

- adapter: native Kotlin + Jetpack Compose, `minSdk 24`, `compileSdk/targetSdk 37`;
- reference profile: AVD `Medium_Phone`, Android 17 / API 37, x86_64, 1080×2400, 420 dpi;
- один primary stroke содержит не более 10 000 distinct points и после consecutive-duplicate
  cleanup arc-length resample-ится ровно в `N=128`; degenerate stroke fail-closed;
- canonical DFT: `C_k = (1/N) Σ z[n] exp(-i2πkn/N)` в FFT storage/signed-frequency order;
- selection использует amplitude-descending order с deterministic canonical tie-break,
  `K=1..128`; speed ограничена `0.01..100.00×`, trace — 10 000 endpoints;
- ViewModel сохраняет active result через configuration change. Raw pointer input не сохраняется;
  process recreation получает только bounded explicitly permitted state;
- production manifest не запрашивает network/storage permission. Store release, signing и
  redistribution остаются вне FS-031.

## Требования

### AND-FR-001 — Touch capture

Android surface принимает один primary touch stroke, различает pointer down/move/up/cancel,
ограничивает число samples и преобразует координаты экрана в portable `Point2D`/`Curve` contract.

### AND-FR-002 — Shared Fourier semantics

Resampling, coefficients, selection, vector order, endpoint и trace семантически эквивалентны
desktop/core contracts. Mobile adapter не содержит независимую недоказанную Fourier formula.

### AND-FR-003 — Animated epicycle view

После завершения stroke пользователь видит circles, head-to-tail vectors, moving endpoint и
persistent trace; доступны Play/Pause/Restart и bounded harmonic/speed controls.

### AND-FR-004 — Mobile lifecycle

Rotation, background/foreground, interruption, activity recreation и app close не публикуют
partial/stale result, не продолжают скрытую unbounded animation и восстанавливают только явно
разрешённое non-sensitive state.

### AND-FR-005 — Offline privacy

Primary touch-to-epicycle path работает без network permission, account, upload или telemetry.
Raw touch samples не пишутся в logs и не покидают device по умолчанию.

### AND-FR-006 — Accessibility and layout

Controls имеют touch targets, labels/content descriptions и keyboard/switch-access path where
platform-applicable; portrait/landscape layouts сохраняют canvas и primary controls.

## Acceptance

- AND-AC-001: debug build устанавливается на declared Android emulator/device и проходит живой
  `finger/stylus stroke → Curve → Fourier → chain → animated endpoint trace` scenario.
- AND-AC-002: shared canonical fixtures дают coefficient/endpoint parity с Python reference в
  установленных tolerances.
- AND-AC-003: cancel, background/foreground и rotation сохраняют coherent state без stale worker.
- AND-AC-004: frame-time, memory, battery-sensitive animation budget измерены на named reference
  device/profile; renderer не объявляется smooth без recorded evidence.
- AND-AC-005: release/debug manifest review подтверждает отсутствие неожиданной network/storage
  permission и uncontrolled data export.

## Планируемая трассировка

Stage `FS-031`; behaviors `BH-DRAW-001`, `BH-EPICYCLE-TRACE-001`, `BH-MOBILE-001`.
