import React from 'react';
import { Stack } from 'expo-router';
import { View, ActivityIndicator, StyleSheet, Text, Image } from 'react-native';
import { AuthProvider, useAuth } from '../contexts/AuthContext';

// Inner layout component that uses the auth context
function RootLayoutNav() {
  const { loading } = useAuth();

  // Show splash screen until auth state is fully resolved
  if (loading) {
    return (
      <View style={styles.splashContainer}>
        <Image 
          source={require('../assets/images/logo.png')} 
          style={styles.logo}
          resizeMode="contain"
        />
        <ActivityIndicator size="large" color="#960018" style={styles.spinner} />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="auth/login" />
      <Stack.Screen name="auth/register" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <RootLayoutNav />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  splashContainer: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    width: 200,
    height: 64,
    marginBottom: 24,
  },
  spinner: {
    marginTop: 16,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#64748B',
    fontWeight: '500',
  },
});
