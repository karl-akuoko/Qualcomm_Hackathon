package com.qualcomm.reroute.data.api

import com.qualcomm.reroute.data.models.DisruptionStatus
import com.qualcomm.reroute.data.models.SystemState
import retrofit2.Response
import retrofit2.http.*

interface BusDispatchApi {
    @GET("status")
    suspend fun getStatus(): Response<Map<String, Any>>
    
    @POST("add_road_closure")
    suspend fun addRoadClosure(
        @Query("avenue") avenue: Int,
        @Query("street") street: Int
    ): Response<Map<String, String>>
    
    @POST("add_car_crash")
    suspend fun addCarCrash(
        @Query("avenue") avenue: Int,
        @Query("street") street: Int
    ): Response<Map<String, String>>
    
    @POST("add_icy_roads")
    suspend fun addIcyRoads(
        @Query("avenue") avenue: Int,
        @Query("street") street: Int
    ): Response<Map<String, String>>
    
    @POST("add_traffic_jam")
    suspend fun addTrafficJam(
        @Query("avenue") avenue: Int,
        @Query("street") street: Int
    ): Response<Map<String, String>>
    
    @POST("clear_disruptions")
    suspend fun clearDisruptions(): Response<Map<String, String>>
}
