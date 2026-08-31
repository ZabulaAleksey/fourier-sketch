package com.zabula.fouriersketch

import androidx.lifecycle.SavedStateHandle
import com.zabula.fouriersketch.core.Point
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

class FourierViewModelTest {
    @Test fun drawingPublishesFixedCurveChainAndBoundedControls() {
        val holder = FourierViewModel(SavedStateHandle())
        holder.submitPixels(List(11_000) { index -> Point(cos(2 * PI * index / 11_000), sin(2 * PI * index / 11_000)) })
        assertEquals(128, holder.state.value.curve!!.size)
        assertEquals(15, holder.state.value.epicycles.size)
        assertFalse(holder.state.value.playing)
        holder.setHarmonics(999)
        holder.setSpeed(-2f)
        assertEquals(128, holder.state.value.selected.size)
        assertEquals(0.01f, holder.state.value.speed, 0.001f)
    }

    @Test fun pauseAndResetArePresentationOnly() {
        val holder = FourierViewModel(SavedStateHandle())
        holder.submitPixels(listOf(Point(-1.0, 0.0), Point(0.0, 1.0), Point(1.0, 0.0), Point(0.0, -1.0)))
        holder.restart(); holder.pause(); holder.resetViewport()
        assertFalse(holder.state.value.playing)
        assertEquals(1f, holder.state.value.viewport.zoom, 0.001f)
        assertTrue(holder.state.value.curve!!.isNotEmpty())
    }
}
