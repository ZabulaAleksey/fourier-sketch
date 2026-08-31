package com.zabula.fouriersketch

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.pinch
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.swipe
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertTrue

class MainActivityTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    @Test fun canvasIsAccessibleAndAcceptsPrimaryTouchStroke() {
        rule.onNodeWithContentDescription("Drawing canvas").assertExists()
        rule.onNodeWithTag("epicycle-canvas").performTouchInput {
            swipe(start = center.copy(x = center.x - 80f), end = center.copy(x = center.x + 80f), durationMillis = 200)
        }
        rule.onNodeWithTag("epicycle-canvas").assertExists()
        rule.onNodeWithContentDescription("Fourier epicycle canvas. One finger pans; two fingers zoom.").assertExists()
        rule.onNodeWithTag("epicycle-canvas").performTouchInput {
            pinch(
                start0 = center.copy(x = center.x - 40f),
                end0 = center.copy(x = center.x - 80f),
                start1 = center.copy(x = center.x + 40f),
                end1 = center.copy(x = center.x + 80f),
                durationMillis = 200,
            )
        }
        val zoomLabel = rule.onNodeWithTag("zoom-value")
            .fetchSemanticsNode()
            .config[SemanticsProperties.Text]
            .single()
            .text
        val zoom = zoomLabel.substringAfter("Zoom: ").substringBefore("×").toFloat()
        assertTrue("pinch should increase zoom, actual label: $zoomLabel", zoom in 1.1f..2.1f)
        rule.mainClock.autoAdvance = false
        rule.onNodeWithText("Play").assertIsEnabled().performClick()
        rule.mainClock.advanceTimeBy(32)
        rule.onNodeWithText("Pause").performClick()
        rule.onNodeWithText("Restart").performClick()
        rule.onNodeWithText("Play").assertIsEnabled()
        rule.mainClock.autoAdvance = true
        rule.waitForIdle()
        rule.activityRule.scenario.recreate()
        rule.onNodeWithContentDescription("Fourier epicycle canvas. One finger pans; two fingers zoom.").assertExists()
    }
}
