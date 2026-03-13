import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { API_URL } from '../../utils/api';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [mobile, setMobile] = useState('');
  const [pincode, setPincode] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [company, setCompany] = useState('');
  const [designation, setDesignation] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingLocation, setFetchingLocation] = useState(false);
  const router = useRouter();

  // Fetch city and state from pincode
  const fetchLocationFromPincode = async (pin: string) => {
    if (pin.length !== 6) return;
    
    setFetchingLocation(true);
    try {
      const PINCODE_API_URL = process.env.EXPO_PUBLIC_PINCODE_API_URL || 'https://api.postalpincode.in';
      const response = await fetch(`${PINCODE_API_URL}/pincode/${pin}`);
      const data = await response.json();
      
      if (data && data[0] && data[0].Status === 'Success' && data[0].PostOffice && data[0].PostOffice.length > 0) {
        const postOffice = data[0].PostOffice[0];
        setCity(postOffice.District || postOffice.Name);
        setState(postOffice.State);
      } else {
        Alert.alert('Invalid Pincode', 'Could not find location for this pincode');
        setCity('');
        setState('');
      }
    } catch (error) {
      console.error('Error fetching pincode:', error);
      Alert.alert('Error', 'Failed to fetch location from pincode');
    } finally {
      setFetchingLocation(false);
    }
  };

  const handlePincodeChange = (value: string) => {
    // Only allow numeric input
    const numericValue = value.replace(/[^0-9]/g, '');
    setPincode(numericValue);
    
    // Auto-fetch location when 6 digits entered
    if (numericValue.length === 6) {
      fetchLocationFromPincode(numericValue);
    } else {
      setCity('');
      setState('');
    }
  };

  const handleRegister = async () => {
    // Validate all required fields
    if (!name.trim()) {
      Alert.alert('Error', 'Please enter your name');
      return;
    }
    
    if (!email.trim()) {
      Alert.alert('Error', 'Please enter your email');
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      Alert.alert('Error', 'Please enter a valid email address');
      return;
    }

    if (!mobile.trim()) {
      Alert.alert('Error', 'Please enter your mobile number');
      return;
    }

    // Validate mobile number (10 digits)
    const mobileRegex = /^[0-9]{10}$/;
    if (!mobileRegex.test(mobile)) {
      Alert.alert('Error', 'Please enter a valid 10-digit mobile number');
      return;
    }

    if (!pincode.trim() || pincode.length !== 6) {
      Alert.alert('Error', 'Please enter a valid 6-digit pincode');
      return;
    }

    if (!city || !state) {
      Alert.alert('Error', 'Please enter a valid pincode to auto-fill city and state');
      return;
    }

    if (!company.trim()) {
      Alert.alert('Error', 'Please enter your company name');
      return;
    }

    if (!password) {
      Alert.alert('Error', 'Please enter a password');
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert('Error', 'Passwords do not match');
      return;
    }

    if (password.length < 6) {
      Alert.alert('Error', 'Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      // Send OTP request with all fields
      const response = await fetch(`${API_URL}/api/auth/send-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          name,
          mobile,
          pincode,
          city,
          state,
          company,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to send verification code');
      }

      // Navigate to OTP verification screen
      router.push({
        pathname: '/auth/verify-otp',
        params: {
          email,
          name,
          mobile,
          pincode,
          city,
          state,
          company: company || '',
          password,
        },
      });
    } catch (error: any) {
      Alert.alert('Registration Failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Ionicons name="person-add-outline" size={48} color="#960018" />
          </View>
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>Join our conveyor platform</Text>
        </View>

        <View style={styles.form}>
          {/* Customer Name */}
          <View style={styles.inputContainer}>
            <Ionicons name="person-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Customer Name *"
              placeholderTextColor="#94A3B8"
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
          </View>

          {/* Email */}
          <View style={styles.inputContainer}>
            <Ionicons name="mail-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Email ID *"
              placeholderTextColor="#94A3B8"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          {/* Mobile Number */}
          <View style={styles.inputContainer}>
            <Ionicons name="call-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Mobile Number *"
              placeholderTextColor="#94A3B8"
              value={mobile}
              onChangeText={(text) => setMobile(text.replace(/[^0-9]/g, ''))}
              keyboardType="phone-pad"
              maxLength={10}
            />
          </View>

          {/* Pincode */}
          <View style={styles.inputContainer}>
            <Ionicons name="location-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Pin Code *"
              placeholderTextColor="#94A3B8"
              value={pincode}
              onChangeText={handlePincodeChange}
              keyboardType="number-pad"
              maxLength={6}
            />
            {fetchingLocation && (
              <ActivityIndicator size="small" color="#960018" style={styles.inputLoader} />
            )}
          </View>

          {/* City & State (Auto-filled) */}
          {(city || state) && (
            <View style={styles.locationContainer}>
              <View style={styles.locationBox}>
                <Text style={styles.locationLabel}>City</Text>
                <Text style={styles.locationValue}>{city}</Text>
              </View>
              <View style={styles.locationBox}>
                <Text style={styles.locationLabel}>State</Text>
                <Text style={styles.locationValue}>{state}</Text>
              </View>
            </View>
          )}

          {/* Company (Required) */}
          <View style={styles.inputContainer}>
            <Ionicons name="business-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Company Name *"
              placeholderTextColor="#94A3B8"
              value={company}
              onChangeText={setCompany}
            />
          </View>

          {/* Password */}
          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Password *"
              placeholderTextColor="#94A3B8"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
            />
          </View>

          {/* Confirm Password */}
          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Confirm Password *"
              placeholderTextColor="#94A3B8"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry
              autoCapitalize="none"
            />
          </View>

          <View style={styles.infoBox}>
            <Ionicons name="shield-checkmark-outline" size={20} color="#10B981" />
            <Text style={styles.infoText}>
              We'll send a verification code to your email
            </Text>
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={loading}
            data-testid="register-btn"
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Text style={styles.buttonText}>Send Verification Code</Text>
                <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => router.back()}
          >
            <Text style={styles.linkText}>Already have an account? Sign In</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
    paddingTop: 60,
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FEF2F2',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#0F172A',
    marginTop: 8,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 15,
    color: '#64748B',
    marginTop: 8,
  },
  form: {
    width: '100%',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 10,
    marginBottom: 16,
    paddingHorizontal: 16,
    backgroundColor: '#FFFFFF',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    height: 52,
    fontSize: 16,
    color: '#0F172A',
  },
  inputLoader: {
    marginLeft: 8,
  },
  locationContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  locationBox: {
    flex: 1,
    backgroundColor: '#ECFDF5',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#A7F3D0',
  },
  locationLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#059669',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  locationValue: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0F172A',
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ECFDF5',
    borderRadius: 10,
    padding: 14,
    marginBottom: 20,
    gap: 10,
    borderWidth: 1,
    borderColor: '#A7F3D0',
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#059669',
  },
  button: {
    flexDirection: 'row',
    backgroundColor: '#960018',
    height: 52,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  buttonDisabled: {
    backgroundColor: '#94A3B8',
    shadowOpacity: 0,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  linkButton: {
    marginTop: 24,
    alignItems: 'center',
  },
  linkText: {
    color: '#960018',
    fontSize: 14,
    fontWeight: '500',
  },
});
