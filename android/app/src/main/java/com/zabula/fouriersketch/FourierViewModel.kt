package com.zabula.fouriersketch

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import com.zabula.fouriersketch.core.Coefficient
import com.zabula.fouriersketch.core.Point
import com.zabula.fouriersketch.core.Viewport
import com.zabula.fouriersketch.core.boundedHarmonics
import com.zabula.fouriersketch.core.boundedSpeed
import com.zabula.fouriersketch.core.coefficients
import com.zabula.fouriersketch.core.evaluateChain
import com.zabula.fouriersketch.core.pan
import com.zabula.fouriersketch.core.resampleClosed
import com.zabula.fouriersketch.core.sanitizeTouchPoints
import com.zabula.fouriersketch.core.selectCoefficients
import com.zabula.fouriersketch.core.zoomAround

data class FourierUiState(
    val curve: List<Point>? = null,
    val selected: List<Coefficient> = emptyList(),
    val epicycles: List<com.zabula.fouriersketch.core.Epicycle> = emptyList(),
    val trace: List<Point> = emptyList(),
    val harmonics: Int = 15,
    val speed: Float = 1f,
    val time: Double = 0.0,
    val playing: Boolean = false,
    val viewport: Viewport = Viewport(),
)

class FourierViewModel(private val saved: SavedStateHandle) : ViewModel() {
    private val _state = mutableStateOf(FourierUiState(
        harmonics = saved["harmonics"] ?: 15,
        speed = saved["speed"] ?: 1f,
    ))
    val state: State<FourierUiState> = _state
    private var lastFrameNanos = 0L

    fun submitPixels(pixels: List<Point>) {
        if (pixels.size < 3) return
        val boundedPixels = sanitizeTouchPoints(pixels)
        val width = boundedPixels.maxOf { it.x } - boundedPixels.minOf { it.x }
        val height = boundedPixels.maxOf { it.y } - boundedPixels.minOf { it.y }
        val radius = maxOf(width, height) / 2f
        if (radius <= 0f) return
        val centerX = boundedPixels.map { it.x }.average()
        val centerY = boundedPixels.map { it.y }.average()
        val normalized = boundedPixels.map { Point((it.x - centerX) / radius, -(it.y - centerY) / radius) }
        val curve = resampleClosed(normalized)
        val all = coefficients(curve)
        val selected = selectCoefficients(all, _state.value.harmonics)
        val epicycles = evaluateChain(selected, 0.0)
        _state.value = _state.value.copy(curve = curve, selected = selected, epicycles = epicycles, time = 0.0, trace = listOf(epicycles.last().end), playing = false, viewport = Viewport())
    }

    fun setHarmonics(value: Int) {
        val count = boundedHarmonics(value)
        saved["harmonics"] = count
        val selected = _state.value.curve?.let { selectCoefficients(coefficients(it), count) } ?: emptyList()
        val epicycles = evaluateChain(selected, _state.value.time)
        _state.value = _state.value.copy(
            harmonics = count,
            selected = selected,
            epicycles = epicycles,
            trace = epicycles.lastOrNull()?.end?.let(::listOf) ?: emptyList(),
        )
    }
    fun setSpeed(value: Float) { val speed = boundedSpeed(value); saved["speed"] = speed; _state.value = _state.value.copy(speed = speed) }
    fun togglePlaying() { _state.value = _state.value.copy(playing = !_state.value.playing); lastFrameNanos = 0L }
    fun pause() { _state.value = _state.value.copy(playing = false); lastFrameNanos = 0L }
    fun restart() {
        val epicycles = evaluateChain(_state.value.selected, 0.0)
        _state.value = _state.value.copy(
            time = 0.0,
            epicycles = epicycles,
            trace = epicycles.lastOrNull()?.end?.let(::listOf) ?: emptyList(),
            playing = false,
        )
        lastFrameNanos = 0L
    }
    fun clear() { _state.value = FourierUiState(harmonics = _state.value.harmonics, speed = _state.value.speed); lastFrameNanos = 0L }
    fun resetViewport() { _state.value = _state.value.copy(viewport = Viewport()) }
    fun transformViewport(zoom: Float, x: Float, y: Float, dx: Float, dy: Float) {
        val afterZoom = if (zoom == 1f) _state.value.viewport else zoomAround(_state.value.viewport, zoom, x, y)
        _state.value = _state.value.copy(viewport = pan(afterZoom, dx, dy))
    }
    fun advance(frameNanos: Long) {
        if (!_state.value.playing) return
        if (lastFrameNanos == 0L) { lastFrameNanos = frameNanos; return }
        val dt = ((frameNanos - lastFrameNanos).coerceAtMost(100_000_000L)) / 1_000_000_000.0
        lastFrameNanos = frameNanos
        val time = (_state.value.time + dt * _state.value.speed) % 1.0
        val chain = evaluateChain(_state.value.selected, time)
        val endpoint = chain.lastOrNull()?.end ?: Point(0.0, 0.0)
        val trace = (_state.value.trace + endpoint).takeLast(com.zabula.fouriersketch.core.MAX_TRACE_POINTS)
        _state.value = _state.value.copy(time = time, epicycles = chain, trace = trace)
    }
}
