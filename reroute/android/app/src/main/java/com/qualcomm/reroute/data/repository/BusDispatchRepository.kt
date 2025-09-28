package com.qualcomm.reroute.data.repository

import com.qualcomm.reroute.data.api.BusDispatchApi
import com.qualcomm.reroute.data.models.DisruptionStatus
import com.qualcomm.reroute.data.models.SystemState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BusDispatchRepository @Inject constructor(
    private val api: BusDispatchApi
) {
    suspend fun getSystemState(): Flow<SystemState> = flow {
        // This would be implemented with WebSocket connection
        // For now, returning mock data
        emit(SystemState(
            simulationTime = 0,
            buses = emptyList(),
            stops = emptyList(),
            kpis = com.qualcomm.reroute.data.models.KPIs(
                avgWaitTime = 0.0,
                totalPassengers = 0,
                totalPassengersWaiting = 0,
                totalPassengersOnBuses = 0
            ),
            comparison = com.qualcomm.reroute.data.models.Comparison(
                baselineAvgWait = 0.0,
                optimizedAvgWait = 0.0,
                improvementPercentage = 0.0,
                baselineBuses = 0,
                optimizedBuses = 0
            )
        ))
    }
    
    suspend fun addRoadClosure(avenue: Int, street: Int): Result<String> {
        return try {
            val response = api.addRoadClosure(avenue, street)
            if (response.isSuccessful) {
                Result.success(response.body()?.get("message") ?: "Road closure added")
            } else {
                Result.failure(Exception("Failed to add road closure"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun addCarCrash(avenue: Int, street: Int): Result<String> {
        return try {
            val response = api.addCarCrash(avenue, street)
            if (response.isSuccessful) {
                Result.success(response.body()?.get("message") ?: "Car crash added")
            } else {
                Result.failure(Exception("Failed to add car crash"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun addIcyRoads(avenue: Int, street: Int): Result<String> {
        return try {
            val response = api.addIcyRoads(avenue, street)
            if (response.isSuccessful) {
                Result.success(response.body()?.get("message") ?: "Icy roads added")
            } else {
                Result.failure(Exception("Failed to add icy roads"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun addTrafficJam(avenue: Int, street: Int): Result<String> {
        return try {
            val response = api.addTrafficJam(avenue, street)
            if (response.isSuccessful) {
                Result.success(response.body()?.get("message") ?: "Traffic jam added")
            } else {
                Result.failure(Exception("Failed to add traffic jam"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun clearDisruptions(): Result<String> {
        return try {
            val response = api.clearDisruptions()
            if (response.isSuccessful) {
                Result.success(response.body()?.get("message") ?: "Disruptions cleared")
            } else {
                Result.failure(Exception("Failed to clear disruptions"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
