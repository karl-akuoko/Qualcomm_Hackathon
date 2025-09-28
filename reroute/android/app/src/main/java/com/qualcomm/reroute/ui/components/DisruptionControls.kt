package com.qualcomm.reroute.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun DisruptionControls(
    onRoadClosure: () -> Unit,
    onCarCrash: () -> Unit,
    onIcyRoads: () -> Unit,
    onTrafficJam: () -> Unit,
    onClearDisruptions: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = "Road Disruptions",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.height(200.dp)
            ) {
                items(disruptionButtons) { button ->
                    DisruptionButton(
                        text = button.text,
                        icon = button.icon,
                        color = button.color,
                        onClick = button.onClick
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Button(
                onClick = onClearDisruptions,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.secondary
                )
            ) {
                Text("🧹 Clear All Disruptions")
            }
        }
    }
}

@Composable
private fun DisruptionButton(
    text: String,
    icon: String,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        modifier = modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(
            containerColor = color
        )
    ) {
        Text(
            text = "$icon $text",
            style = MaterialTheme.typography.bodySmall
        )
    }
}

private data class DisruptionButtonData(
    val text: String,
    val icon: String,
    val color: Color,
    val onClick: () -> Unit
)

private val disruptionButtons = listOf(
    DisruptionButtonData(
        text = "Road Closure",
        icon = "🚧",
        color = Color(0xFFFF6B6B),
        onClick = { /* Will be set by parent */ }
    ),
    DisruptionButtonData(
        text = "Car Crash",
        icon = "🚗💥",
        color = Color(0xFFFF8C00),
        onClick = { /* Will be set by parent */ }
    ),
    DisruptionButtonData(
        text = "Icy Roads",
        icon = "🧊",
        color = Color(0xFF87CEEB),
        onClick = { /* Will be set by parent */ }
    ),
    DisruptionButtonData(
        text = "Traffic Jam",
        icon = "🚦",
        color = Color(0xFFFFA500),
        onClick = { /* Will be set by parent */ }
    )
)
