package com.zabula.fouriersketch.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.json.JSONObject
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

class FourierCoreTest {
    @Test fun canonicalPythonFixtureIsPresentAndUsesTheSameContract() {
        val root = JSONObject(java.io.File("../../fixtures/android/fourier-parity-v1.json").readText())
        assertEquals("forward_1_over_n", root.getString("normalization"))
        assertEquals("signed_fft_storage", root.getString("frequency_convention"))
        val cases = root.getJSONArray("cases")
        for (caseIndex in 0 until cases.length()) {
            val item = cases.getJSONObject(caseIndex)
            val pointsJson = item.getJSONArray("points")
            val points = List(pointsJson.length()) { pointIndex ->
                val point = pointsJson.getJSONArray(pointIndex)
                Point(point.getDouble(0), point.getDouble(1))
            }
            val actualCoefficients = coefficients(points)
            val actual = actualCoefficients.associateBy { it.frequency }
            val expected = item.getJSONArray("coefficients")
            for (rowIndex in 0 until expected.length()) {
                val row = expected.getJSONArray(rowIndex)
                val coefficient = actual.getValue(row.getInt(0))
                assertEquals(row.getDouble(1), coefficient.value.re, 1e-9)
                assertEquals(row.getDouble(2), coefficient.value.im, 1e-9)
            }
            val checks = item.getJSONArray("endpoint_checks")
            for (checkIndex in 0 until checks.length()) {
                val check = checks.getJSONObject(checkIndex)
                val time = check.getDouble("time")
                var endpoint = Complex(0.0, 0.0)
                val frequencies = check.getJSONArray("frequencies")
                val expectedFrequencies = List(frequencies.length()) { frequencies.getInt(it) }
                assertEquals(
                    expectedFrequencies,
                    selectCoefficients(actualCoefficients, check.getInt("harmonic_count")).map { it.frequency },
                )
                for (frequencyIndex in 0 until frequencies.length()) {
                    val coefficient = actual.getValue(frequencies.getInt(frequencyIndex))
                    val angle = 2 * PI * coefficient.frequency * time
                    endpoint += coefficient.value * Complex(cos(angle), sin(angle))
                }
                val expectedEndpoint = check.getJSONArray("endpoint")
                assertEquals(expectedEndpoint.getDouble(0), endpoint.re, 1e-8)
                assertEquals(expectedEndpoint.getDouble(1), endpoint.im, 1e-8)
            }
        }
    }

    @Test fun signedBinsMatchCanonicalStorageOrder() {
        assertEquals(listOf(0, 1, 2, 3, 4, 5, 6, 7, -8, -7, -6, -5, -4, -3, -2, -1), signedFrequencies(16))
    }

    @Test fun circleResamplingAndDftRecoverDominantFrequency() {
        val source = List(64) { index -> Point(cos(2 * PI * index / 64), sin(2 * PI * index / 64)) }
        val selected = selectCoefficients(coefficients(resampleClosed(source)), 8)
        assertEquals(1, selected.first().frequency)
        assertTrue(selected.first().amplitude > 0.95)
    }

    @Test fun boundsAreStable() {
        assertEquals(1, boundedHarmonics(0)); assertEquals(128, boundedHarmonics(999))
        assertEquals(MIN_SPEED, boundedSpeed(-1f)); assertEquals(MAX_SPEED, boundedSpeed(999f))
    }

    @Test fun touchInputIsBoundedAndChainEndpointIsPublished() {
        val input = List(MAX_TOUCH_POINTS + 50) { Point(it.toDouble(), 0.0) }
        assertEquals(MAX_TOUCH_POINTS, sanitizeTouchPoints(input).size)
        val chain = evaluateChain(selectCoefficients(coefficients(resampleClosed(listOf(Point(1.0, 0.0), Point(0.0, 1.0)))), 3), 0.0)
        assertEquals(3, chain.size)
        assertTrue(chain.last().end.x.isFinite() && chain.last().end.y.isFinite())
    }
}
