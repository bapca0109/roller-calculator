import React from 'react';
import { Stack } from 'expo-router';
import { View, ActivityIndicator, StyleSheet, Text, Image, Platform } from 'react-native';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { CartProvider } from './context/CartContext';
import { SafeAreaProvider } from 'react-native-safe-area-context';

// Global font family constant - Calibri with fallbacks
// On web, Calibri will be used if available, otherwise fallback fonts
// On native, system font will be used
export const FONT_FAMILY = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'System',
});

export const FONT_FAMILY_BOLD = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'System',
});

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
      <Stack.Screen name="auth/forgot-password" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <CartProvider>
          <RootLayoutNav />
        </CartProvider>
      </AuthProvider>
    </SafeAreaProvider>
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
