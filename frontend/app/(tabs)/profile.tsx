import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      // Use the logout function from AuthContext
      await logout();
      // Navigate to login using expo-router (works on all platforms)
      // Use setTimeout to ensure state updates complete before navigation
      setTimeout(() => {
        router.replace('/auth/login');
      }, 100);
    } catch (error) {
      console.error('Logout error:', error);
      Alert.alert('Error', 'Failed to logout. Please try again.');
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'admin':
        return 'Administrator';
      case 'sales':
        return 'Sales Team';
      case 'customer':
        return 'Customer';
      default:
        return role;
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return '#C41E3A';
      case 'sales':
        return '#FF9500';
      case 'customer':
        return '#007AFF';
      default:
        return '#8E8E93';
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Profile</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.profileCard}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {user?.name?.charAt(0).toUpperCase()}
              </Text>
            </View>
          </View>

          <Text style={styles.userName}>{user?.name}</Text>
          <Text style={styles.userEmail}>{user?.email}</Text>

          <View
            style={[
              styles.roleBadge,
              { backgroundColor: `${getRoleBadgeColor(user?.role || '')}20` },
            ]}
          >
            <Text
              style={[
                styles.roleBadgeText,
                { color: getRoleBadgeColor(user?.role || '') },
              ]}
            >
              {getRoleLabel(user?.role || '')}
            </Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account Information</Text>

          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <View style={styles.infoLabel}>
                <Ionicons name="mail-outline" size={20} color="#8E8E93" />
                <Text style={styles.infoLabelText}>Email</Text>
              </View>
              <Text style={styles.infoValue}>{user?.email}</Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.infoRow}>
              <View style={styles.infoLabel}>
                <Ionicons name="person-outline" size={20} color="#8E8E93" />
                <Text style={styles.infoLabelText}>Name</Text>
              </View>
              <Text style={styles.infoValue}>{user?.name}</Text>
            </View>

            {user?.company && (
              <>
                <View style={styles.divider} />
                <View style={styles.infoRow}>
                  <View style={styles.infoLabel}>
                    <Ionicons name="business-outline" size={20} color="#8E8E93" />
                    <Text style={styles.infoLabelText}>Company</Text>
                  </View>
                  <Text style={styles.infoValue}>{user.company}</Text>
                </View>
              </>
            )}

            <View style={styles.divider} />

            <View style={styles.infoRow}>
              <View style={styles.infoLabel}>
                <Ionicons name="shield-checkmark-outline" size={20} color="#8E8E93" />
                <Text style={styles.infoLabelText}>Role</Text>
              </View>
              <Text style={styles.infoValue}>{getRoleLabel(user?.role || '')}</Text>
            </View>
          </View>
        </View>

        {Platform.OS === 'web' ? (
          <button
            onClick={() => {
              localStorage.clear();
              sessionStorage.clear();
              window.location.href = '/auth/login';
            }}
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: '#C41E3A',
              borderRadius: 12,
              padding: 16,
              gap: 8,
              marginTop: 20,
              marginBottom: 30,
              border: 'none',
              cursor: 'pointer',
              width: '100%',
            }}
          >
            <Ionicons name="log-out-outline" size={20} color="#fff" />
            <span style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>Logout</span>
          </button>
        ) : (
          <TouchableOpacity 
            style={styles.logoutButton} 
            onPress={() => {
              AsyncStorage.removeItem('token');
              AsyncStorage.removeItem('user');
              router.replace('/auth/login');
            }}
          >
            <Ionicons name="log-out-outline" size={20} color="#fff" />
            <Text style={styles.logoutButtonText}>Logout</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 34,
    fontWeight: 'bold',
    color: '#000',
  },
  content: {
    padding: 16,
  },
  profileCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  avatarContainer: {
    marginBottom: 16,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#000',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 14,
    color: '#8E8E93',
    marginBottom: 16,
  },
  roleBadge: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 16,
  },
  roleBadgeText: {
    fontSize: 14,
    fontWeight: '600',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginBottom: 12,
  },
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  infoLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  infoLabelText: {
    fontSize: 16,
    color: '#3C3C43',
  },
  infoValue: {
    fontSize: 16,
    color: '#8E8E93',
    maxWidth: '50%',
    textAlign: 'right',
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E5EA',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#C41E3A',
    borderRadius: 12,
    padding: 16,
    gap: 8,
    marginTop: 20,
    marginBottom: 30,
    cursor: 'pointer',
  },
  logoutButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
