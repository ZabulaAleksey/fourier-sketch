package com.zabula.fouriersketch.core

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin

/** Small, deterministic and Android-free Fourier kernel used by the mobile UI. */
data class Point(val x: Double, val y: Double)

data class Complex(val re: Double, val im: Double) {
    operator fun plus(other: Complex) = Complex(re + other.re, im + other.im)
    operator fun times(other: Complex) = Complex(re * other.re - im * other.im, re * other.im + im * other.re)
    operator fun times(scale: Double) = Complex(re * scale, im * scale)
    fun magnitude() = hypot(re, im)
}

data class Coefficient(val frequency: Int, val value: Complex) {
    val amplitude: Double get() = value.magnitude()
    val phase: Double get() = kotlin.math.atan2(value.im, value.re)
}

data class Epicycle(val start: Point, val end: Point, val coefficient: Coefficient)

const val MAX_TOUCH_POINTS = 10_000
const val SAMPLE_COUNT = 128
const val MAX_HARMONICS = SAMPLE_COUNT
const val MAX_TRACE_POINTS = 10_000
const val MIN_SPEED = 0.01f
const val MAX_SPEED = 100f

data class Viewport(val zoom: Float = 1f, val panX: Float = 0f, val panY: Float = 0f)

/** Presentation-only viewport transform. The pinch centroid remains stationary in content space. */
fun zoomAround(viewport: Viewport, factor: Float, centroidX: Float, centroidY: Float): Viewport {
    require(factor.isFinite() && centroidX.isFinite() && centroidY.isFinite()) { "viewport transform must be finite" }
    require(viewport.zoom.isFinite() && viewport.zoom > 0f && viewport.panX.isFinite() && viewport.panY.isFinite()) { "viewport must be finite" }
    val next = factor.coerceAtLeast(0.001f)
    val zoom = (viewport.zoom * next).coerceIn(0.01f, 100f)
    val applied = zoom / viewport.zoom
    return viewport.copy(
        zoom = zoom,
        panX = centroidX - (centroidX - viewport.panX) * applied,
        panY = centroidY - (centroidY - viewport.panY) * applied,
    )
}

fun pan(viewport: Viewport, dx: Float, dy: Float): Viewport {
    require(dx.isFinite() && dy.isFinite()) { "pan delta must be finite" }
    return viewport.copy(panX = viewport.panX + dx, panY = viewport.panY + dy)
}

fun boundedHarmonics(value: Int): Int = value.coerceIn(1, MAX_HARMONICS)
fun boundedSpeed(value: Float): Float {
    require(value.isFinite()) { "speed must be finite" }
    return value.coerceIn(MIN_SPEED, MAX_SPEED)
}

fun sanitizeTouchPoints(points: List<Point>): List<Point> {
    require(points.all { it.x.isFinite() && it.y.isFinite() }) { "touch points must be finite" }
    return points.take(MAX_TOUCH_POINTS)
}

/** Arc-length resampling of a closed polyline at N evenly spaced positions. */
fun resampleClosed(points: List<Point>, count: Int = SAMPLE_COUNT): List<Point> {
    require(count in 2..SAMPLE_COUNT) { "sample count is outside the mobile budget" }
    require(points.size <= MAX_TOUCH_POINTS) { "touch point budget exceeded" }
    require(points.all { it.x.isFinite() && it.y.isFinite() }) { "touch points must be finite" }
    require(points.size >= 2) { "at least two touch points are required" }
    val cleaned = points.fold(ArrayList<Point>(points.size)) { result, point ->
        if (result.lastOrNull() != point) result.add(point)
        result
    }
    require(cleaned.size >= 2) { "distinct touch points are required" }
    val segments = cleaned.indices.map { index ->
        val next = cleaned[(index + 1) % cleaned.size]
        hypot((next.x - cleaned[index].x).toDouble(), (next.y - cleaned[index].y).toDouble())
    }
    val total = segments.sum()
    require(total > 0.0) { "curve length must be positive" }
    val cumulative = DoubleArray(cleaned.size + 1)
    for (index in segments.indices) cumulative[index + 1] = cumulative[index] + segments[index]
    return List(count) { outputIndex ->
        val target = total * outputIndex / count
        var segment = cumulative.binarySearch(target).let { if (it >= 0) it.coerceAtMost(cleaned.size - 1) else (-it - 2).coerceIn(0, cleaned.size - 1) }
        while (segments[segment] == 0.0 && segment < segments.lastIndex) segment++
        val fraction = ((target - cumulative[segment]) / segments[segment]).coerceIn(0.0, 1.0)
        val start = cleaned[segment]
        val end = cleaned[(segment + 1) % cleaned.size]
        Point(start.x + (end.x - start.x) * fraction, start.y + (end.y - start.y) * fraction)
    }
}

/** Canonical FFT storage order: for even N, 0..N/2-1 followed by -N/2..-1. */
fun signedFrequencies(sampleCount: Int = SAMPLE_COUNT): List<Int> = List(sampleCount) { index ->
    if (index <= (sampleCount - 1) / 2) index else index - sampleCount
}

fun coefficients(samples: List<Point>): List<Coefficient> {
    require(samples.isNotEmpty() && samples.size <= SAMPLE_COUNT)
    require(samples.all { it.x.isFinite() && it.y.isFinite() }) { "samples must be finite" }
    val n = samples.size.toDouble()
    return signedFrequencies(samples.size).map { frequency ->
        var sum = Complex(0.0, 0.0)
        samples.forEachIndexed { index, point ->
            val angle = -2.0 * PI * frequency * index / n
            sum += Complex(point.x.toDouble(), point.y.toDouble()) * Complex(cos(angle), sin(angle))
        }
        Coefficient(frequency, sum * (1.0 / n))
    }
}

/** Stable amplitude ordering; ties use frequency then storage order for reproducibility. */
fun selectCoefficients(all: List<Coefficient>, harmonics: Int): List<Coefficient> =
    all.withIndex().sortedWith(compareByDescending<IndexedValue<Coefficient>> { it.value.amplitude }.thenBy { kotlin.math.abs(it.value.frequency) }.thenBy { it.value.frequency }.thenBy { it.index }).take(boundedHarmonics(harmonics)).map { it.value }

fun evaluateChain(selected: List<Coefficient>, time: Double): List<Epicycle> {
    require(time.isFinite()) { "time must be finite" }
    var cursor = Point(0.0, 0.0)
    return selected.map { coefficient ->
        val angle = 2.0 * PI * coefficient.frequency * time + coefficient.phase
        val end = Point(cursor.x + coefficient.amplitude * cos(angle), cursor.y + coefficient.amplitude * sin(angle))
        Epicycle(cursor, end, coefficient).also { cursor = end }
    }
}
