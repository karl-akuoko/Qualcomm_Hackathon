package com.qualcomm.reroute.data.models

import com.google.gson.annotations.SerializedName

data class Bus(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("x")
    val longitude: Double,
    
    @SerializedName("y")
    val latitude: Double,
    
    @SerializedName("route_id")
    val routeId: String,
    
    @SerializedName("route_name")
    val routeName: String,
    
    @SerializedName("load")
    val load: Int,
    
    @SerializedName("capacity")
    val capacity: Int,
    
    @SerializedName("color")
    val color: String,
    
    @SerializedName("direction")
    val direction: String,
    
    @SerializedName("avenue")
    val avenue: Int,
    
    @SerializedName("street")
    val street: Int,
    
    @SerializedName("is_optimized")
    val isOptimized: Boolean,
    
    @SerializedName("efficiency_score")
    val efficiencyScore: Double
)
