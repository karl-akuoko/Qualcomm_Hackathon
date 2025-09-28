# Android App Setup Instructions

## 🚀 Quick Start for Android Studio

### Prerequisites
- Android Studio Arctic Fox (2020.3.1) or later
- Android SDK 24+ (Android 7.0)
- Google Maps API Key
- Java 8 or later

### 1. Open Project in Android Studio

1. **Open Android Studio**
2. **Select "Open an Existing Project"**
3. **Navigate to**: `/Users/ehsan/Downloads/IdeaProjects/Qualcomm/Qualcomm_Hackathon/reroute/android`
4. **Click "OK"**

### 2. Configure Google Maps API Key

1. **Get Google Maps API Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable "Maps SDK for Android"
   - Create credentials (API Key)
   - Restrict the key to Android apps

2. **Add API Key to Android App**:
   - Open `android/app/src/main/AndroidManifest.xml`
   - Replace `YOUR_GOOGLE_MAPS_API_KEY` with your actual API key:
   ```xml
   <meta-data
       android:name="com.google.android.geo.API_KEY"
       android:value="YOUR_ACTUAL_API_KEY_HERE" />
   ```

### 3. Configure Network Access

1. **Update Base URL** (if needed):
   - Open `android/app/src/main/java/com/qualcomm/reroute/di/NetworkModule.kt`
   - Change `BASE_URL` if your server runs on different IP:
   ```kotlin
   private const val BASE_URL = "http://YOUR_SERVER_IP:8000/"
   ```

### 4. Build and Run

1. **Sync Project**:
   - Click "Sync Now" when prompted
   - Or go to `File > Sync Project with Gradle Files`

2. **Run the App**:
   - Connect Android device or start emulator
   - Click the "Run" button (green play icon)
   - Or press `Shift + F10`

## 📱 Android App Features

### ✅ **Perfect Grid Alignment**
- **45° map tilt** for roads perfectly parallel/perpendicular to screen
- **Streets run up/down**, **avenues run left/right** aligned with screen
- **All 335+ Manhattan bus stops** from GTFS data + UI data files

### ✅ **Road Disruption Controls**
- 🚧 **Road Closures** - Complete blockage (0% movement)
- 🚗💥 **Car Crashes** - Severe slowdown (30% movement)  
- 🧊 **Icy Roads** - Moderate slowdown (60% movement)
- 🚦 **Traffic Jams** - Light slowdown (70% movement)
- 🧹 **Clear All** - Remove all disruptions

### ✅ **Real-time Performance**
- **Live Metrics** - Wait times, passenger counts, efficiency
- **Baseline vs Optimized** - Compare untrained vs trained routes
- **Interactive Map** - Google Maps with bus and stop visualization
- **Disruption Impact** - See how road conditions affect performance

## 🗽 Android App Structure

```
android/
├── app/
│   ├── build.gradle                 # App dependencies
│   └── src/main/
│       ├── AndroidManifest.xml      # App permissions & config
│       ├── java/com/qualcomm/reroute/
│       │   ├── MainActivity.kt      # Main activity
│       │   ├── data/
│       │   │   ├── models/          # Data models (Bus, BusStop, etc.)
│       │   │   ├── api/             # API interface
│       │   │   └── repository/      # Data repository
│       │   ├── ui/
│       │   │   ├── screens/         # Main screen
│       │   │   ├── components/      # UI components
│       │   │   ├── viewmodel/       # ViewModels
│       │   │   └── theme/           # App theme
│       │   └── di/                  # Dependency injection
│       └── res/                      # Resources (strings, themes)
├── build.gradle                     # Project-level build config
├── settings.gradle                  # Project settings
└── gradle.properties               # Gradle properties
```

## 🔧 Troubleshooting

### Common Issues:

1. **"Google Maps API Key not found"**:
   - Check that you've added your API key to `AndroidManifest.xml`
   - Ensure the API key has "Maps SDK for Android" enabled

2. **"Network connection failed"**:
   - Make sure the Python server is running on `localhost:8000`
   - For physical device, use your computer's IP address instead of `10.0.2.2`

3. **"Build failed"**:
   - Clean and rebuild: `Build > Clean Project` then `Build > Rebuild Project`
   - Check that all dependencies are properly synced

4. **"App crashes on startup"**:
   - Check that all required permissions are granted
   - Ensure the server is running before starting the app

## 📱 Running on Physical Device

1. **Enable Developer Options** on your Android device
2. **Enable USB Debugging**
3. **Connect device via USB**
4. **Run the app** - it will install and launch on your device
5. **Update BASE_URL** in `NetworkModule.kt` to your computer's IP address

## 🎯 Next Steps

1. **Start Python Server**: Run `python start_comparison.py` in the main project
2. **Launch Android App**: Run the app in Android Studio
3. **Test Features**: Try adding road disruptions and see the impact
4. **Monitor Performance**: Watch real-time metrics and bus movement

---

**Ready to run!** The Android app provides the same functionality as the web version with a native mobile interface! 📱🚌✨
