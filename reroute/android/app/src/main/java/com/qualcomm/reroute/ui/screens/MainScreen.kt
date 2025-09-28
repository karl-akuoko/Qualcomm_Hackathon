package com.qualcomm.reroute.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.qualcomm.reroute.ui.components.SimpleMapView
import com.qualcomm.reroute.ui.components.DisruptionControls
import com.qualcomm.reroute.ui.components.PerformanceMetrics
import com.qualcomm.reroute.ui.viewmodel.BusDispatchViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: BusDispatchViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Manhattan Bus Dispatch") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Sidebar with controls
            Column(
                modifier = Modifier
                    .width(350.dp)
                    .fillMaxHeight()
                    .padding(16.dp)
            ) {
                PerformanceMetrics(
                    systemState = uiState.systemState,
                    isLoading = uiState.isLoading
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                DisruptionControls(
                    onRoadClosure = viewModel::addRoadClosure,
                    onCarCrash = viewModel::addCarCrash,
                    onIcyRoads = viewModel::addIcyRoads,
                    onTrafficJam = viewModel::addTrafficJam,
                    onClearDisruptions = viewModel::clearDisruptions
                )
                
                if (uiState.lastAction != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    ) {
                        Text(
                            text = uiState.lastAction!!,
                            modifier = Modifier.padding(8.dp),
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
                
                if (uiState.error != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        )
                    ) {
                        Text(
                            text = uiState.error!!,
                            modifier = Modifier.padding(8.dp),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                    }
                }
            }
            
            // Map
            SimpleMapView(
                systemState = uiState.systemState,
                modifier = Modifier.fillMaxSize()
            )
        }
    }
}
