import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import HomeScreen from './src/screens/HomeScreen';
import StopDetailScreen from './src/screens/StopDetailScreen';
import MapScreen from './src/screens/MapScreen';
import { WebSocketProvider } from './src/context/WebSocketContext';

const Stack = createStackNavigator();

const App: React.FC = () => {
  return (
    <SafeAreaProvider>
      <WebSocketProvider>
        <NavigationContainer>
          <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
          <Stack.Navigator
            initialRouteName="Home"
            screenOptions={{
              headerStyle: {
                backgroundColor: '#3b82f6',
              },
              headerTintColor: '#ffffff',
              headerTitleStyle: {
                fontWeight: 'bold',
              },
            }}
          >
            <Stack.Screen 
              name="Home" 
              component={HomeScreen}
              options={{ title: 'Bus Tracker' }}
            />
            <Stack.Screen 
              name="StopDetail" 
              component={StopDetailScreen}
              options={{ title: 'Stop Details' }}
            />
            <Stack.Screen 
              name="Map" 
              component={MapScreen}
              options={{ title: 'Live Map' }}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </WebSocketProvider>
    </SafeAreaProvider>
  );
};

export default App;