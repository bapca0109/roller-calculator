import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || process.env.REACT_APP_BACKEND_URL || '';

// Simple event emitter for cache refresh (works in React Native)
type RefreshListener = () => void;
const refreshListeners: RefreshListener[] = [];

export const cacheEvents = {
  on: (event: string, listener: RefreshListener) => {
    if (event === 'refresh') {
      refreshListeners.push(listener);
    }
  },
  off: (event: string, listener: RefreshListener) => {
    if (event === 'refresh') {
      const index = refreshListeners.indexOf(listener);
      if (index > -1) {
        refreshListeners.splice(index, 1);
      }
    }
  },
  emit: (event: string) => {
    if (event === 'refresh') {
      refreshListeners.forEach(listener => listener());
    }
  }
};

// Cache version key - increment this to bust all caches
const CACHE_VERSION_KEY = 'app_cache_version';
const CURRENT_CACHE_VERSION = '2'; // Increment when you want to force refresh

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  },
});

// Add cache-busting timestamp and auth token to all requests
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add cache-busting timestamp to all GET requests
    if (config.method === 'get' || !config.method) {
      config.params = {
        ...config.params,
        _t: Date.now(), // Cache buster
      };
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Check and update cache version on app start
export const checkCacheVersion = async (): Promise<boolean> => {
  try {
    const storedVersion = await AsyncStorage.getItem(CACHE_VERSION_KEY);
    if (storedVersion !== CURRENT_CACHE_VERSION) {
      console.log('[API] Cache version mismatch, clearing old cache...');
      // Clear all cached data except auth
      const token = await AsyncStorage.getItem('token');
      const user = await AsyncStorage.getItem('user');
      await AsyncStorage.clear();
      // Restore auth if it existed
      if (token) await AsyncStorage.setItem('token', token);
      if (user) await AsyncStorage.setItem('user', user);
      await AsyncStorage.setItem(CACHE_VERSION_KEY, CURRENT_CACHE_VERSION);
      return true; // Cache was cleared
    }
    return false;
  } catch (error) {
    console.error('[API] Error checking cache version:', error);
    return false;
  }
};

// Trigger global refresh - call this to force all screens to refetch data
export const triggerGlobalRefresh = () => {
  console.log('[API] Triggering global data refresh...');
  cacheEvents.emit('refresh');
};

// Force clear all data and refresh
export const forceRefreshAllData = async () => {
  console.log('[API] Force refreshing all data...');
  
  // Clear any locally cached data
  const keysToPreserve = ['token', 'user', 'last_activity_timestamp', CACHE_VERSION_KEY];
  
  try {
    const allKeys = await AsyncStorage.getAllKeys();
    const keysToRemove = allKeys.filter(key => !keysToPreserve.includes(key));
    if (keysToRemove.length > 0) {
      await AsyncStorage.multiRemove(keysToRemove);
    }
    console.log('[API] Cleared cached data, preserved auth');
  } catch (error) {
    console.error('[API] Error clearing cache:', error);
  }
  
  // Trigger all screens to refresh
  triggerGlobalRefresh();
};

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await AsyncStorage.removeItem('token');
      await AsyncStorage.removeItem('user');
    }
    return Promise.reject(error);
  }
);

export default api;
