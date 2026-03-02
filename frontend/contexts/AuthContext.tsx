import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../utils/api';

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
        const parsedUser = JSON.parse(userData);
        console.log('[AuthContext] User loaded:', parsedUser.email, 'Role:', parsedUser.role);
        setUserState(parsedUser);
        setIsAuthenticated(true);
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
    }
  };

  const login = async (email: string, password: string) => {
    try {
      console.log('[AuthContext] Login attempt for:', email);
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      
      await AsyncStorage.setItem('token', access_token);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
      
      console.log('[AuthContext] Login successful, user role:', userData.role);
      setUserState(userData);
      setIsAuthenticated(true);
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
    await AsyncStorage.removeItem('token');
    await AsyncStorage.removeItem('user');
    setUserState(null);
    setIsAuthenticated(false);
    console.log('[AuthContext] Logout complete');
  };

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated, setUser, login, register, logout, refreshUser }}>
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
