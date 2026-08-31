package com.zabula.fouriersketch

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import com.zabula.fouriersketch.core.Epicycle
import com.zabula.fouriersketch.core.MAX_SPEED
import com.zabula.fouriersketch.core.MAX_TOUCH_POINTS
import com.zabula.fouriersketch.core.MIN_SPEED
import com.zabula.fouriersketch.core.Point
import com.zabula.fouriersketch.core.Viewport
import kotlin.math.min

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { FourierSketchApp() }
    }
}

@Composable
fun FourierSketchApp(stateHolder: FourierViewModel = viewModel()) {
    val state by stateHolder.state
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) stateHolder.pause()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(state.playing) {
        while (stateHolder.state.value.playing) {
            withFrameNanos { frame -> stateHolder.advance(frame) }
        }
    }
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFF101014)) {
            BoxWithConstraints(modifier = Modifier.fillMaxSize().padding(12.dp)) {
                if (maxWidth > 700.dp) {
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxSize()) {
                        CanvasPanel(stateHolder, state, Modifier.weight(1f).fillMaxSize())
                        Controls(stateHolder, state, Modifier.width(280.dp))
                    }
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxSize()) {
                        CanvasPanel(stateHolder, state, Modifier.fillMaxWidth().weight(1f))
                        Controls(stateHolder, state, Modifier.fillMaxWidth())
                    }
                }
            }
        }
    }
}

@Composable
private fun Controls(holder: FourierViewModel, state: FourierUiState, modifier: Modifier) {
    val harmonicsDescription = stringResource(R.string.harmonics_description)
    val speedDescription = stringResource(R.string.speed_description)
    Column(modifier = modifier.padding(4.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(stringResource(R.string.app_name), color = Color.White, style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.draw_hint), color = Color.LightGray)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = holder::togglePlaying, enabled = state.curve != null) { Text(stringResource(if (state.playing) R.string.pause else R.string.play)) }
            Button(onClick = holder::restart, enabled = state.curve != null) { Text(stringResource(R.string.restart)) }
            Button(onClick = holder::clear) { Text(stringResource(if (state.curve == null) R.string.clear else R.string.new_curve)) }
        }
        Text(stringResource(R.string.harmonics_value, state.harmonics), color = Color.White)
        Slider(
            value = state.harmonics.toFloat(),
            onValueChange = { holder.setHarmonics(it.toInt()) },
            valueRange = 1f..128f,
            modifier = Modifier.semantics { contentDescription = harmonicsDescription },
        )
        Text(stringResource(R.string.speed_value, state.speed), color = Color.White)
        Slider(
            value = state.speed,
            onValueChange = holder::setSpeed,
            valueRange = MIN_SPEED..MAX_SPEED,
            modifier = Modifier.semantics { contentDescription = speedDescription },
        )
        Text(
            stringResource(R.string.zoom_value, state.viewport.zoom),
            color = Color.White,
            modifier = Modifier.testTag("zoom-value"),
        )
        Button(onClick = holder::resetViewport) { Text(stringResource(R.string.reset_view)) }
    }
}

@Composable
private fun CanvasPanel(holder: FourierViewModel, state: FourierUiState, modifier: Modifier) {
    var drawing by remember { mutableStateOf<List<Point>>(emptyList()) }
    val canvasDescription = stringResource(
        if (state.curve == null) R.string.drawing_canvas_description else R.string.epicycle_canvas_description,
    )
    val drawModifier = if (state.curve == null) {
        Modifier.pointerInput("draw") {
            detectDragGestures(
                onDragStart = { drawing = listOf(Point(it.x.toDouble(), it.y.toDouble())) },
                onDrag = { change, _ ->
                    if (drawing.size < MAX_TOUCH_POINTS) drawing = drawing + Point(change.position.x.toDouble(), change.position.y.toDouble())
                    change.consume()
                },
                onDragEnd = { holder.submitPixels(drawing); drawing = emptyList() },
                onDragCancel = { drawing = emptyList() },
            )
        }
    } else {
        Modifier.pointerInput("navigate") {
            detectTransformGestures { centroid, pan, zoom, _ -> holder.transformViewport(zoom, centroid.x, centroid.y, pan.x, pan.y) }
        }
    }
    Canvas(
        modifier = modifier
            .background(Color(0xFF171820))
            .testTag("epicycle-canvas")
            .semantics { contentDescription = canvasDescription }
            .then(drawModifier),
    ) {
        val scale = min(size.width, size.height) / 2f
        val viewport = state.viewport
        fun screen(point: Point): Offset = Offset(
            size.width / 2f + viewport.panX + point.x.toFloat() * scale * viewport.zoom,
            size.height / 2f + viewport.panY - point.y.toFloat() * scale * viewport.zoom,
        )
        if (state.curve == null) {
            drawPath(pixelPath(drawing), color = Color(0xFF8AB4F8), style = Stroke(3f, cap = StrokeCap.Round))
            drawing.lastOrNull()?.let { drawCircle(Color(0xFFFF5252), radius = 7f, center = Offset(it.x.toFloat(), it.y.toFloat())) }
        } else {
            val tracePath = Path()
            state.trace.forEachIndexed { index, point -> if (index == 0) tracePath.moveTo(screen(point).x, screen(point).y) else tracePath.lineTo(screen(point).x, screen(point).y) }
            drawPath(tracePath, Color(0xFFFFC107), style = Stroke(3f))
            var cursor = screen(Point(0.0, 0.0))
            state.epicycles.forEachIndexed { index, epicycle ->
                val end = screen(epicycle.end)
                val radius = epicycle.coefficient.amplitude.toFloat() * scale * viewport.zoom
                val pairColor = rainbow[index % rainbow.size]
                drawCircle(pairColor.copy(alpha = 0.55f), radius, cursor, style = Stroke(1.5f))
                drawLine(pairColor, cursor, end, 3f, StrokeCap.Round)
                cursor = end
            }
            drawCircle(Color(0xFFFF5252), 6f, cursor)
        }
    }
}

private fun pixelPath(points: List<Point>): Path = Path().apply {
    points.firstOrNull()?.let { moveTo(it.x.toFloat(), it.y.toFloat()) }
    points.drop(1).forEach { lineTo(it.x.toFloat(), it.y.toFloat()) }
}

private val rainbow = listOf(
    Color(0xFFEF5350), Color(0xFFFFA726), Color(0xFFFFEE58), Color(0xFF66BB6A),
    Color(0xFF26C6DA), Color(0xFF42A5F5), Color(0xFF7E57C2), Color(0xFFEC407A),
)
