package com.qualcomm.reroute.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.qualcomm.reroute.data.models.SystemState
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Overlay

@Composable
fun OpenStreetMapView(
    systemState: SystemState?,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier) {
        AndroidView(
            factory = { context ->
                Configuration.getInstance().load(context, context.getSharedPreferences("osmdroid", 0))
                
                MapView(context).apply {
                    setTileSource(TileSourceFactory.MAPNIK)
                    setMultiTouchControls(true)
                    setBuiltInZoomControls(true)
                    controller.setZoom(12.0)
                    controller.setCenter(GeoPoint(40.7831, -73.9712)) // Manhattan center
                }
            },
            update = { mapView ->
                // Clear existing markers
                mapView.overlays.clear()
                
                // Add bus stops
                systemState?.stops?.forEach { stop ->
                    val marker = Marker(mapView)
                    marker.position = GeoPoint(stop.latitude, stop.longitude)
                    marker.title = stop.name
                    marker.snippet = "Queue: ${stop.queueLength}"
                    
                    // Color based on queue length
                    marker.icon = when {
                        stop.queueLength > 5 -> createColoredMarker(Color.Red)
                        stop.queueLength > 2 -> createColoredMarker(Color(0xFFFFA500))
                        else -> createColoredMarker(Color.Green)
                    }
                    
                    mapView.overlays.add(marker)
                }
                
                // Add buses
                systemState?.buses?.forEach { bus ->
                    val marker = Marker(mapView)
                    marker.position = GeoPoint(bus.latitude, bus.longitude)
                    marker.title = "Bus ${bus.id}"
                    marker.snippet = "Load: ${bus.load}/${bus.capacity}"
                    
                    // Color based on optimization status
                    marker.icon = if (bus.isOptimized) {
                        createColoredMarker(Color.Green)
                    } else {
                        createColoredMarker(Color.Red)
                    }
                    
                    mapView.overlays.add(marker)
                }
                
                mapView.invalidate()
            }
        )
        
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
    }
}

private fun createColoredMarker(color: Color): android.graphics.drawable.Drawable {
    // This would create a colored circle drawable
    // For now, return a default marker
    return android.graphics.drawable.ColorDrawable(color.toArgb())
}
