package com.qualcomm.reroute.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.qualcomm.reroute.data.models.Bus
import com.qualcomm.reroute.data.models.BusStop
import com.qualcomm.reroute.data.models.SystemState
import kotlin.math.*

@Composable
fun SimpleMapView(
    systemState: SystemState?,
    modifier: Modifier = Modifier
) {
    var offsetX by remember { mutableStateOf(0f) }
    var offsetY by remember { mutableStateOf(0f) }
    var scale by remember { mutableStateOf(1f) }
    
    // Manhattan bounds (approximate)
    val minLat = 40.7000
    val maxLat = 40.8500
    val minLon = -74.0500
    val maxLon = -73.9000
    
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF5F5F5))
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .pointerInput(Unit) {
                    detectDragGestures { _, delta ->
                        offsetX += delta.x
                        offsetY += delta.y
                    }
                }
        ) {
            // Draw Manhattan grid
            drawManhattanGrid(
                minLat, maxLat, minLon, maxLon,
                offsetX, offsetY, scale
            )
            
            // Draw bus stops
            systemState?.stops?.forEach { stop ->
                drawBusStop(
                    stop, minLat, maxLat, minLon, maxLon,
                    offsetX, offsetY, scale
                )
            }
            
            // Draw buses
            systemState?.buses?.forEach { bus ->
                drawBus(
                    bus, minLat, maxLat, minLon, maxLon,
                    offsetX, offsetY, scale
                )
            }
        }
        
        // Status overlay
        Card(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f)
            )
        ) {
            Column(
                modifier = Modifier.padding(12.dp)
            ) {
                Text(
                    text = "System Status",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                
                systemState?.let { state ->
                    Text(
                        text = "Time: ${state.simulationTime}s",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = "Buses: ${state.buses.size}",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = "Stops: ${state.stops.size}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
        
        // Zoom controls
        Column(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(16.dp)
        ) {
            Button(
                onClick = { scale = (scale * 1.2f).coerceAtMost(3f) },
                modifier = Modifier.size(48.dp)
            ) {
                Text("+")
            }
            Spacer(modifier = Modifier.height(8.dp))
            Button(
                onClick = { scale = (scale / 1.2f).coerceAtLeast(0.5f) },
                modifier = Modifier.size(48.dp)
            ) {
                Text("-")
            }
        }
    }
}

private fun DrawScope.drawManhattanGrid(
    minLat: Double, maxLat: Double, minLon: Double, maxLon: Double,
    offsetX: Float, offsetY: Float, scale: Float
) {
    val width = size.width
    val height = size.height
    
    // Draw streets (horizontal lines)
    for (street in 1..200) {
        val lat = minLat + (street / 200.0) * (maxLat - minLat)
        val y = ((maxLat - lat) / (maxLat - minLat) * height * scale + offsetY).toFloat()
        
        if (y >= 0 && y <= height) {
            drawLine(
                color = Color(0xFFE0E0E0),
                start = Offset(0f, y),
                end = Offset(width, y),
                strokeWidth = 2.dp.toPx()
            )
        }
    }
    
    // Draw avenues (vertical lines)
    for (avenue in 1..12) {
        val lon = minLon + (avenue / 12.0) * (maxLon - minLon)
        val x = ((lon - minLon) / (maxLon - minLon) * width * scale + offsetX).toFloat()
        
        if (x >= 0 && x <= width) {
            drawLine(
                color = Color(0xFFE0E0E0),
                start = Offset(x, 0f),
                end = Offset(x, height),
                strokeWidth = 2.dp.toPx()
            )
        }
    }
}

private fun DrawScope.drawBusStop(
    stop: BusStop,
    minLat: Double, maxLat: Double, minLon: Double, maxLon: Double,
    offsetX: Float, offsetY: Float, scale: Float
) {
    val width = size.width
    val height = size.height
    
    val x = ((stop.longitude - minLon) / (maxLon - minLon) * width * scale + offsetX).toFloat()
    val y = ((maxLat - stop.latitude) / (maxLat - minLat) * height * scale + offsetY).toFloat()
    
    if (x >= 0 && x <= width && y >= 0 && y <= height) {
        val color = when {
            stop.queueLength > 5 -> Color.Red
            stop.queueLength > 2 -> Color(0xFFFFA500)
            else -> Color.Green
        }
        
        drawCircle(
            color = color,
            radius = 8.dp.toPx(),
            center = Offset(x, y)
        )
        
        // Draw queue length
        if (stop.queueLength > 0) {
            drawCircle(
                color = Color.White,
                radius = 12.dp.toPx(),
                center = Offset(x, y)
            )
            drawCircle(
                color = color,
                radius = 8.dp.toPx(),
                center = Offset(x, y)
            )
        }
    }
}

private fun DrawScope.drawBus(
    bus: Bus,
    minLat: Double, maxLat: Double, minLon: Double, maxLon: Double,
    offsetX: Float, offsetY: Float, scale: Float
) {
    val width = size.width
    val height = size.height
    
    val x = ((bus.longitude - minLon) / (maxLon - minLon) * width * scale + offsetX).toFloat()
    val y = ((maxLat - bus.latitude) / (maxLat - minLat) * height * scale + offsetY).toFloat()
    
    if (x >= 0 && x <= width && y >= 0 && y <= height) {
        val color = if (bus.isOptimized) Color.Green else Color.Red
        
        drawCircle(
            color = color,
            radius = 10.dp.toPx(),
            center = Offset(x, y)
        )
        
        // Draw load indicator
        if (bus.load > 0) {
            drawCircle(
                color = Color.White,
                radius = 6.dp.toPx(),
                center = Offset(x, y)
            )
        }
    }
}
