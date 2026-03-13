import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AppState, AppStateStatus, Platform } from 'react-native';
import api from '../utils/api';
import { 
  registerForPushNotificationsAsync, 
  savePushToken, 
  removePushToken,
  addNotificationListeners 
} from '../utils/notifications';

// Auto-logout after 7 days of inactivity (in milliseconds)
const INACTIVITY_TIMEOUT_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const LAST_ACTIVITY_KEY = 'last_activity_timestamp';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  company?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, company?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateLastActivity: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Wrapper for setUser that also updates isAuthenticated
  const setUser = useCallback((newUser: User | null) => {
    setUserState(newUser);
    setIsAuthenticated(!!newUser);
  }, []);

  // Update last activity timestamp
  const updateLastActivity = async () => {
    try {
      await AsyncStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());
    } catch (error) {
      console.error('[AuthContext] Error updating last activity:', error);
    }
  };

  // Check if session has expired due to inactivity
  const checkInactivityTimeout = async (): Promise<boolean> => {
    try {
      const lastActivity = await AsyncStorage.getItem(LAST_ACTIVITY_KEY);
      if (!lastActivity) {
        // No last activity recorded, session is valid
        return false;
      }

      const lastActivityTime = parseInt(lastActivity, 10);
      const currentTime = Date.now();
      const timeSinceLastActivity = currentTime - lastActivityTime;

      if (timeSinceLastActivity > INACTIVITY_TIMEOUT_MS) {
        console.log('[AuthContext] Session expired due to inactivity (7 days)');
        return true; // Session expired
      }

      return false; // Session still valid
    } catch (error) {
      console.error('[AuthContext] Error checking inactivity timeout:', error);
      return false;
    }
  };

  // Handle app state changes (foreground/background)
  useEffect(() => {
    const handleAppStateChange = async (nextAppState: AppStateStatus) => {
      if (nextAppState === 'active' && isAuthenticated) {
        // App came to foreground, check inactivity
        const expired = await checkInactivityTimeout();
        if (expired) {
          await logout();
        } else {
          // Update last activity when app becomes active
          await updateLastActivity();
        }
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription?.remove();
  }, [isAuthenticated]);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    console.log('[AuthContext] Starting loadUser...');
    try {
      const token = await AsyncStorage.getItem('token');
      const userData = await AsyncStorage.getItem('user');
      
      console.log('[AuthContext] Token exists:', !!token, 'UserData exists:', !!userData);
      
      if (token && userData) {
        // Check if session expired due to inactivity
        const expired = await checkInactivityTimeout();
        if (expired) {
          console.log('[AuthContext] Auto-logout: 7 days of inactivity');
          await AsyncStorage.removeItem('token');
          await AsyncStorage.removeItem('user');
          await AsyncStorage.removeItem(LAST_ACTIVITY_KEY);
          setUserState(null);
          setIsAuthenticated(false);
        } else {
          const parsedUser = JSON.parse(userData);
          console.log('[AuthContext] User loaded:', parsedUser.email, 'Role:', parsedUser.role);
          setUserState(parsedUser);
          setIsAuthenticated(true);
          // Update last activity on successful load
          await updateLastActivity();
        }
      } else {
        console.log('[AuthContext] No stored session found');
        setUserState(null);
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('[AuthContext] Error loading user:', error);
      setUserState(null);
      setIsAuthenticated(false);
    } finally {
      console.log('[AuthContext] loadUser complete, setting loading=false');
      setLoading(false);
    }
  };

  // Allow components to manually refresh user data
  const refreshUser = async () => {
    const userData = await AsyncStorage.getItem('user');
    if (userData) {
      const parsedUser = JSON.parse(userData);
      setUserState(parsedUser);
      setIsAuthenticated(true);
      await updateLastActivity();
    }
  };

  const login = async (email: string, password: string) => {
    try {
      console.log('[AuthContext] Login attempt for:', email);
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      
      await AsyncStorage.setItem('token', access_token);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
      // Set last activity on login
      await updateLastActivity();
      
      console.log('[AuthContext] Login successful, user role:', userData.role);
      setUserState(userData);
      setIsAuthenticated(true);

      // Register for push notifications for admins (only on native platforms)
      if (userData.role === 'admin' && Platform.OS !== 'web') {
        try {
          console.log('[AuthContext] Registering admin for push notifications...');
          const pushToken = await registerForPushNotificationsAsync();
          if (pushToken) {
            await savePushToken(pushToken);
            console.log('[AuthContext] Push token registered successfully');
          }
        } catch (pushError) {
          console.error('[AuthContext] Push notification registration failed:', pushError);
          // Don't throw - push notification failure shouldn't block login
        }
      }
    } catch (error: any) {
      console.error('[AuthContext] Login failed:', error.response?.data?.detail);
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  };

  const register = async (email: string, password: string, name: string, company?: string) => {
    try {
      console.log('[AuthContext] Register attempt for:', email);
      const response = await api.post('/auth/register', {
        email,
        password,
        name,
        company,
        role: 'customer'
      });
      const { access_token, user: userData } = response.data;
      
      await AsyncStorage.setItem('token', access_token);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
      // Set last activity on registration
      await updateLastActivity();
      
      console.log('[AuthContext] Registration successful, user role:', userData.role);
      setUserState(userData);
      setIsAuthenticated(true);
    } catch (error: any) {
      console.error('[AuthContext] Registration failed:', error.response?.data?.detail);
      throw new Error(error.response?.data?.detail || 'Registration failed');
    }
  };

  const logout = async () => {
    console.log('[AuthContext] Logging out...');
    
    // CRITICAL: Clear local state FIRST to immediately update UI
    // This prevents any race conditions on iOS where state updates lag
    setUserState(null);
    setIsAuthenticated(false);
    
    // Clear all local storage immediately (don't await individually to ensure atomicity)
    try {
      await Promise.all([
        AsyncStorage.removeItem('token'),
        AsyncStorage.removeItem('user'),
        AsyncStorage.removeItem(LAST_ACTIVITY_KEY),
      ]);
      console.log('[AuthContext] Local storage cleared');
    } catch (storageError) {
      console.error('[AuthContext] Error clearing storage:', storageError);
      // Continue anyway - state is already cleared
    }
    
    // Remove push token from backend AFTER clearing local storage
    // This is non-critical and should not block logout
    if (Platform.OS !== 'web') {
      // Fire and forget - don't await, don't block logout
      removePushToken().catch((error) => {
        console.warn('[AuthContext] Push token removal failed (non-critical):', error);
      });
    }
    
    console.log('[AuthContext] Logout complete');
  };

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated, setUser, login, register, logout, refreshUser, updateLastActivity }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
