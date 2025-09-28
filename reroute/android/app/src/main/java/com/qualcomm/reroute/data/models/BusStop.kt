package com.qualcomm.reroute.data.models

import com.google.gson.annotations.SerializedName

data class BusStop(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("name")
    val name: String,
    
    @SerializedName("x")
    val longitude: Double,
    
    @SerializedName("y")
    val latitude: Double,
    
    @SerializedName("queue_length")
    val queueLength: Int,
    
    @SerializedName("avenue")
    val avenue: Int,
    
    @SerializedName("street")
    val street: Int
)
