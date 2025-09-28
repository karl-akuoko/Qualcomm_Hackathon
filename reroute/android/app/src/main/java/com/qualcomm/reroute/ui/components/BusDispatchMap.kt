package com.qualcomm.reroute.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.*
import com.qualcomm.reroute.data.models.Bus
import com.qualcomm.reroute.data.models.BusStop
import com.qualcomm.reroute.data.models.SystemState

@Composable
fun BusDispatchMap(
    systemState: SystemState?,
    modifier: Modifier = Modifier
) {
    val manhattanCenter = LatLng(40.7831, -73.9712)
    val cameraPositionState = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(manhattanCenter, 12f)
    }
    
    Box(modifier = modifier) {
        GoogleMap(
            modifier = Modifier.fillMaxSize(),
            cameraPositionState = cameraPositionState,
            properties = MapProperties(
                isMyLocationEnabled = false,
                mapType = MapType.NORMAL
            ),
            uiSettings = MapUiSettings(
                compassEnabled = true,
                zoomControlsEnabled = true
            )
        ) {
            // Draw bus stops
            systemState?.stops?.forEach { stop ->
                Marker(
                    state = MarkerState(
                        position = LatLng(stop.latitude, stop.longitude)
                    ),
                    title = stop.name,
                    snippet = "Queue: ${stop.queueLength}",
                    icon = BitmapDescriptorFactory.defaultMarker(
                        when {
                            stop.queueLength > 5 -> BitmapDescriptorFactory.HUE_RED
                            stop.queueLength > 2 -> BitmapDescriptorFactory.HUE_ORANGE
                            else -> BitmapDescriptorFactory.HUE_GREEN
                        }
                    )
                )
            }
            
            // Draw buses
            systemState?.buses?.forEach { bus ->
                Marker(
                    state = MarkerState(
                        position = LatLng(bus.latitude, bus.longitude)
                    ),
                    title = "Bus ${bus.id}",
                    snippet = "Load: ${bus.load}/${bus.capacity}",
                    icon = BitmapDescriptorFactory.defaultMarker(
                        if (bus.isOptimized) BitmapDescriptorFactory.HUE_GREEN
                        else BitmapDescriptorFactory.HUE_RED
                    )
                )
            }
        }
        
        // Status overlay
        Card(
            modifier = Modifier
                .align(androidx.compose.ui.Alignment.TopEnd)
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
