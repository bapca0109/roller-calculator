import React, { useState, useEffect } from 'react';
import { Platform, View, Text, StyleSheet } from 'react-native';
import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useCart } from '../context/CartContext';
import api from '../../utils/api';

export default function TabsLayout() {
  const { user, isAuthenticated } = useAuth();
  const { cartCount } = useCart();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [pendingRfqCount, setPendingRfqCount] = useState(0);
  
  // Fetch pending RFQ count for admin
  useEffect(() => {
    const fetchPendingRfqCount = async () => {
      if (user?.role === 'admin') {
        try {
          const response = await api.get('/quotes');
          const quotes = response.data;
          const pendingCount = quotes.filter(
            (q: any) => q.status?.toLowerCase() === 'pending' && q.quote_number?.startsWith('RFQ')
          ).length;
          setPendingRfqCount(pendingCount);
        } catch (error) {
          console.error('Error fetching pending RFQ count:', error);
        }
      }
    };
    
    if (isAuthenticated && user) {
      fetchPendingRfqCount();
      // Refresh every 30 seconds
      const interval = setInterval(fetchPendingRfqCount, 30000);
      return () => clearInterval(interval);
    }
  }, [user, isAuthenticated]);
  
  // If user is not authenticated, don't render tabs (prevent crash during logout)
  // Return null to prevent rendering while logout transition is happening
  // The navigation to login will be handled by the logout function
  if (!isAuthenticated || !user) {
    return null;
  }
  
  const isAdmin = user?.role === 'admin';

  // Calculate bottom padding for Android navigation bar
  // On Android, we need extra padding to avoid overlap with system navigation
  const bottomPadding = Platform.OS === 'android' ? Math.max(insets.bottom, 20) + 16 : 10;
  const tabBarHeight = Platform.OS === 'android' ? 72 + Math.max(insets.bottom, 20) : 64;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#C5964A',
        tabBarInactiveTintColor: '#94A3B8',
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#0F172A',
          borderTopWidth: 0,
          height: tabBarHeight,
          paddingBottom: bottomPadding,
          paddingTop: 8,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -4 },
          shadowOpacity: 0.15,
          shadowRadius: 12,
          elevation: 12,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '600',
          marginTop: 2,
          letterSpacing: 0.3,
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'CRM',
          href: isAdmin ? '/dashboard' : null,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-circle-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="calculator"
        options={{
          title: 'Products',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="cube-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="pulley"
        options={{
          title: 'Pulley',
          href: null,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="cog-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="cart"
        options={{
          title: 'Cart',
          tabBarIcon: ({ color, size }) => (
            <View>
              <Ionicons name="cart-outline" size={size} color={color} />
              {cartCount > 0 && (
                <View style={styles.cartBadge}>
                  <Text style={styles.cartBadgeText}>{cartCount > 99 ? '99+' : cartCount}</Text>
                </View>
              )}
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: 'Search',
          href: null, // Hidden - Search is now integrated in Calculator tab
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="search-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="quotes"
        options={{
          title: 'Sales',
          tabBarIcon: ({ color, size }) => (
            <View>
              <Ionicons name="document-text-outline" size={size} color={color} />
              {isAdmin && pendingRfqCount > 0 && (
                <View style={styles.pendingBadge}>
                  <Text style={styles.pendingBadgeText}>{pendingRfqCount > 99 ? '99+' : pendingRfqCount}</Text>
                </View>
              )}
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="customers"
        options={{
          title: 'Customers',
          href: isAdmin ? '/customers' : null,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="admin"
        options={{
          title: 'Admin',
          href: isAdmin ? '/admin' : null,
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="products"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  cartBadge: {
    position: 'absolute',
    top: -6,
    right: -10,
    backgroundColor: '#C5964A',
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  cartBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  pendingBadge: {
    position: 'absolute',
    top: -6,
    right: -10,
    backgroundColor: '#F59E0B',
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  pendingBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
});
