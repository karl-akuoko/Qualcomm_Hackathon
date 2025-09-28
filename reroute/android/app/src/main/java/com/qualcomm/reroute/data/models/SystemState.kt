package com.qualcomm.reroute.data.models

import com.google.gson.annotations.SerializedName

data class SystemState(
    @SerializedName("simulation_time")
    val simulationTime: Int,
    
    @SerializedName("buses")
    val buses: List<Bus>,
    
    @SerializedName("stops")
    val stops: List<BusStop>,
    
    @SerializedName("kpis")
    val kpis: KPIs,
    
    @SerializedName("comparison")
    val comparison: Comparison
)

data class KPIs(
    @SerializedName("avg_wait_time")
    val avgWaitTime: Double,
    
    @SerializedName("total_passengers")
    val totalPassengers: Int,
    
    @SerializedName("total_passengers_waiting")
    val totalPassengersWaiting: Int,
    
    @SerializedName("total_passengers_on_buses")
    val totalPassengersOnBuses: Int
)

data class Comparison(
    @SerializedName("baseline_avg_wait")
    val baselineAvgWait: Double,
    
    @SerializedName("optimized_avg_wait")
    val optimizedAvgWait: Double,
    
    @SerializedName("improvement_percentage")
    val improvementPercentage: Double,
    
    @SerializedName("baseline_buses")
    val baselineBuses: Int,
    
    @SerializedName("optimized_buses")
    val optimizedBuses: Int
)

data class DisruptionStatus(
    @SerializedName("road_closures")
    val roadClosures: Int,
    
    @SerializedName("car_crashes")
    val carCrashes: Int,
    
    @SerializedName("icy_roads")
    val icyRoads: Int,
    
    @SerializedName("traffic_jams")
    val trafficJams: Int
)
