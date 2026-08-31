package com.zabula.fouriersketch

import com.zabula.fouriersketch.core.Viewport
import com.zabula.fouriersketch.core.pan
import com.zabula.fouriersketch.core.zoomAround
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ViewportTest {
    @Test fun pinchKeepsCentroidStationary() {
        val before = Viewport(zoom = 1.5f, panX = 12f, panY = -8f)
        val contentX = (100f - before.panX) / before.zoom
        val contentY = (80f - before.panY) / before.zoom
        val next = zoomAround(before, 2f, 100f, 80f)
        assertEquals(contentX, (100f - next.panX) / next.zoom, 0.001f)
        assertEquals(contentY, (80f - next.panY) / next.zoom, 0.001f)
        assertEquals(3f, next.zoom, 0.001f)
    }

    @Test fun zoomAndPanAreBoundedPresentationState() {
        assertTrue(zoomAround(Viewport(), 0.0001f, 0f, 0f).zoom >= 0.01f)
        assertEquals(3f, pan(Viewport(zoom = 2f), 3f, 0f).panX, 0.001f)
    }
}
