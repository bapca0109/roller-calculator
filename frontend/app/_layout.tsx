import React, { useEffect } from 'react';
import { Stack } from 'expo-router';
import { View, ActivityIndicator, StyleSheet, Text, Image, Platform } from 'react-native';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { useFonts } from 'expo-font';

// Global font family constant
export const FONT_FAMILY = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'Calibri',
});

export const FONT_FAMILY_BOLD = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'CalibriBold',
});

// Set default Text font globally
const setDefaultFontFamily = () => {
  // @ts-ignore
  const oldTextRender = Text.render;
  // @ts-ignore
  Text.render = function(...args) {
    const origin = oldTextRender.call(this, ...args);
    return React.cloneElement(origin, {
      style: [{ fontFamily: FONT_FAMILY }, origin.props.style],
    });
  };
};

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
        <Text style={[styles.loadingText, { fontFamily: FONT_FAMILY }]}>Loading...</Text>
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
  // Load custom fonts
  const [fontsLoaded] = useFonts({
    'Calibri': require('../assets/fonts/Calibri-Regular.ttf'),
    'CalibriBold': require('../assets/fonts/Calibri-Bold.ttf'),
  });

  // Apply global font when fonts are loaded
  useEffect(() => {
    if (fontsLoaded) {
      setDefaultFontFamily();
    }
  }, [fontsLoaded]);

  // Show loading while fonts are loading
  if (!fontsLoaded) {
    return (
      <View style={styles.splashContainer}>
        <ActivityIndicator size="large" color="#960018" />
      </View>
    );
  }

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
