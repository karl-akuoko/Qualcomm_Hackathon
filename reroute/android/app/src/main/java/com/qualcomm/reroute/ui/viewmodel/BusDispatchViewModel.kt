package com.qualcomm.reroute.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.qualcomm.reroute.data.models.Bus
import com.qualcomm.reroute.data.models.BusStop
import com.qualcomm.reroute.data.models.SystemState
import com.qualcomm.reroute.data.repository.BusDispatchRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class BusDispatchViewModel @Inject constructor(
    private val repository: BusDispatchRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(BusDispatchUiState())
    val uiState: StateFlow<BusDispatchUiState> = _uiState.asStateFlow()
    
    init {
        observeSystemState()
    }
    
    private fun observeSystemState() {
        viewModelScope.launch {
            repository.getSystemState().collect { systemState ->
                _uiState.value = _uiState.value.copy(
                    systemState = systemState,
                    isLoading = false
                )
            }
        }
    }
    
    fun addRoadClosure() {
        viewModelScope.launch {
            val avenue = (1..12).random()
            val street = (1..200).random()
            repository.addRoadClosure(avenue, street)
                .onSuccess { message ->
                    _uiState.value = _uiState.value.copy(
                        lastAction = "Road closure added at Avenue $avenue, Street $street"
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        error = error.message ?: "Failed to add road closure"
                    )
                }
        }
    }
    
    fun addCarCrash() {
        viewModelScope.launch {
            val avenue = (1..12).random()
            val street = (1..200).random()
            repository.addCarCrash(avenue, street)
                .onSuccess { message ->
                    _uiState.value = _uiState.value.copy(
                        lastAction = "Car crash added at Avenue $avenue, Street $street"
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        error = error.message ?: "Failed to add car crash"
                    )
                }
        }
    }
    
    fun addIcyRoads() {
        viewModelScope.launch {
            val avenue = (1..12).random()
            val street = (1..200).random()
            repository.addIcyRoads(avenue, street)
                .onSuccess { message ->
                    _uiState.value = _uiState.value.copy(
                        lastAction = "Icy roads added at Avenue $avenue, Street $street"
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        error = error.message ?: "Failed to add icy roads"
                    )
                }
        }
    }
    
    fun addTrafficJam() {
        viewModelScope.launch {
            val avenue = (1..12).random()
            val street = (1..200).random()
            repository.addTrafficJam(avenue, street)
                .onSuccess { message ->
                    _uiState.value = _uiState.value.copy(
                        lastAction = "Traffic jam added at Avenue $avenue, Street $street"
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        error = error.message ?: "Failed to add traffic jam"
                    )
                }
        }
    }
    
    fun clearDisruptions() {
        viewModelScope.launch {
            repository.clearDisruptions()
                .onSuccess { message ->
                    _uiState.value = _uiState.value.copy(
                        lastAction = "All disruptions cleared"
                    )
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        error = error.message ?: "Failed to clear disruptions"
                    )
                }
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

data class BusDispatchUiState(
    val systemState: SystemState? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
    val lastAction: String? = null
)
