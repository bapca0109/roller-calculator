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
  ActivityIndicator,
  Modal,
  Pressable,
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
  const [gstin, setGstin] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingLocation, setFetchingLocation] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedRole, setSelectedRole] = useState<'customer' | 'admin'>('customer');
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [showAdminRequestSent, setShowAdminRequestSent] = useState(false);
  const router = useRouter();

  // Fetch city and state from pincode
  const fetchLocationFromPincode = async (pin: string) => {
    if (pin.length !== 6) return;
    
    setFetchingLocation(true);
    setErrorMessage('');
    try {
      const PINCODE_API_URL = process.env.EXPO_PUBLIC_PINCODE_API_URL || 'https://api.postalpincode.in';
      const response = await fetch(`${PINCODE_API_URL}/pincode/${pin}`);
      const data = await response.json();
      
      if (data && data[0] && data[0].Status === 'Success' && data[0].PostOffice && data[0].PostOffice.length > 0) {
        const postOffice = data[0].PostOffice[0];
        setCity(postOffice.District || postOffice.Name);
        setState(postOffice.State);
      } else {
        setErrorMessage('Invalid pincode. Could not find location for this pincode.');
        setCity('');
        setState('');
      }
    } catch (error) {
      console.error('Error fetching pincode:', error);
      setErrorMessage('Failed to fetch location from pincode. Please try again.');
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
    // Clear any previous error
    setErrorMessage('');
    
    // Validate all required fields
    if (!name.trim()) {
      setErrorMessage('Please enter your name');
      return;
    }
    
    if (!email.trim()) {
      setErrorMessage('Please enter your email');
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setErrorMessage('Please enter a valid email address');
      return;
    }

    if (!mobile.trim()) {
      setErrorMessage('Please enter your mobile number');
      return;
    }

    // Validate mobile number (10 digits)
    const mobileRegex = /^[0-9]{10}$/;
    if (!mobileRegex.test(mobile)) {
      setErrorMessage('Please enter a valid 10-digit mobile number');
      return;
    }

    if (!pincode.trim() || pincode.length !== 6) {
      setErrorMessage('Please enter a valid 6-digit pincode');
      return;
    }

    if (!city || !state) {
      setErrorMessage('Please enter a valid pincode to auto-fill city and state');
      return;
    }

    if (!company.trim()) {
      setErrorMessage('Please enter your company name');
      return;
    }

    // GSTIN is required only for customers
    if (selectedRole === 'customer') {
      if (!gstin.trim()) {
        setErrorMessage('Please enter your GSTIN number');
        return;
      }

      // Validate GSTIN format (15 characters alphanumeric)
      const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
      if (!gstinRegex.test(gstin.toUpperCase())) {
        setErrorMessage('Please enter a valid 15-character GSTIN number (e.g., 22AAAAA0000A1Z5)');
        return;
      }
    }

    if (!password) {
      setErrorMessage('Please enter a password');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      if (selectedRole === 'admin') {
        // Send admin approval request
        const response = await fetch(`${API_URL}/api/auth/request-admin`, {
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
            designation: designation.trim() || null,
            password,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to send admin request');
        }

        // Show success message for admin request
        setShowAdminRequestSent(true);
      } else {
        // Regular customer registration flow
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
            designation: designation.trim() || null,
            gst_number: gstin.toUpperCase(),
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
            designation: designation.trim() || '',
            gst_number: gstin.toUpperCase(),
            password,
          },
        });
      }
    } catch (error: any) {
      const errorMsg = error.message || 'Failed to process request';
      setErrorMessage(errorMsg);
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
          {/* Role Selection Dropdown */}
          <View style={styles.inputContainer}>
            <Ionicons name="people-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TouchableOpacity
              style={styles.dropdownButton}
              onPress={() => setShowRoleDropdown(true)}
              data-testid="role-dropdown-btn"
            >
              <Text style={[styles.dropdownText, selectedRole && styles.dropdownTextSelected]}>
                {selectedRole === 'customer' ? 'Customer' : 'Admin'}
              </Text>
              <Ionicons name="chevron-down" size={20} color="#64748B" />
            </TouchableOpacity>
          </View>

          {/* Role Info Text */}
          {selectedRole === 'admin' && (
            <View style={styles.roleInfoBox}>
              <Ionicons name="information-circle" size={16} color="#0066CC" />
              <Text style={styles.roleInfoText}>
                Admin registration requires approval from info@convero.in
              </Text>
            </View>
          )}

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

          {/* Designation (Optional) */}
          <View style={styles.inputContainer}>
            <Ionicons name="briefcase-outline" size={20} color="#64748B" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Designation (Optional)"
              placeholderTextColor="#94A3B8"
              value={designation}
              onChangeText={setDesignation}
              autoCapitalize="words"
            />
          </View>

          {/* GSTIN (Required for Customers only) */}
          {selectedRole === 'customer' && (
            <View style={styles.inputContainer}>
              <Ionicons name="document-text-outline" size={20} color="#64748B" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="GSTIN Number *"
                placeholderTextColor="#94A3B8"
                value={gstin}
                onChangeText={(text) => setGstin(text.toUpperCase())}
                autoCapitalize="characters"
                maxLength={15}
              />
            </View>
          )}

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

          {/* Error Message Display */}
          {errorMessage ? (
            <View style={styles.errorContainer}>
              <Ionicons name="alert-circle" size={20} color="#DC2626" />
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          ) : null}

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={loading}
            data-testid="register-btn"
            activeOpacity={0.7}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, pointerEvents: 'none' }}>
                <Text style={[styles.buttonText, { pointerEvents: 'none' }]}>
                  {selectedRole === 'admin' ? 'Submit Admin Request' : 'Send Verification Code'}
                </Text>
                <Ionicons name="arrow-forward" size={20} color="#FFFFFF" style={{ pointerEvents: 'none' }} />
              </View>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => router.back()}
            activeOpacity={0.7}
          >
            <View style={{ pointerEvents: 'none' }}>
              <Text style={styles.linkText}>Already have an account? Sign In</Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* Role Selection Modal */}
        <Modal
          visible={showRoleDropdown}
          transparent
          animationType="fade"
          onRequestClose={() => setShowRoleDropdown(false)}
        >
          <Pressable 
            style={styles.modalOverlay} 
            onPress={() => setShowRoleDropdown(false)}
          >
            <View style={styles.roleModalContent}>
              <Text style={styles.roleModalTitle}>Select Account Type</Text>
              
              <TouchableOpacity
                style={[
                  styles.roleOption,
                  selectedRole === 'customer' && styles.roleOptionSelected
                ]}
                onPress={() => {
                  setSelectedRole('customer');
                  setShowRoleDropdown(false);
                }}
              >
                <Ionicons 
                  name="person" 
                  size={24} 
                  color={selectedRole === 'customer' ? '#960018' : '#64748B'} 
                />
                <View style={styles.roleOptionText}>
                  <Text style={[
                    styles.roleOptionTitle,
                    selectedRole === 'customer' && styles.roleOptionTitleSelected
                  ]}>Customer</Text>
                  <Text style={styles.roleOptionDesc}>Browse products and submit RFQs</Text>
                </View>
                {selectedRole === 'customer' && (
                  <Ionicons name="checkmark-circle" size={24} color="#960018" />
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.roleOption,
                  selectedRole === 'admin' && styles.roleOptionSelected
                ]}
                onPress={() => {
                  setSelectedRole('admin');
                  setShowRoleDropdown(false);
                }}
              >
                <Ionicons 
                  name="shield-checkmark" 
                  size={24} 
                  color={selectedRole === 'admin' ? '#960018' : '#64748B'} 
                />
                <View style={styles.roleOptionText}>
                  <Text style={[
                    styles.roleOptionTitle,
                    selectedRole === 'admin' && styles.roleOptionTitleSelected
                  ]}>Admin</Text>
                  <Text style={styles.roleOptionDesc}>Manage prices, quotes & customers</Text>
                </View>
                {selectedRole === 'admin' && (
                  <Ionicons name="checkmark-circle" size={24} color="#960018" />
                )}
              </TouchableOpacity>
            </View>
          </Pressable>
        </Modal>

        {/* Admin Request Sent Modal */}
        <Modal
          visible={showAdminRequestSent}
          transparent
          animationType="fade"
          onRequestClose={() => {
            setShowAdminRequestSent(false);
            router.replace('/auth/login');
          }}
        >
          <Pressable 
            style={styles.modalOverlay} 
            onPress={() => {}}
          >
            <View style={styles.successModalContent}>
              <View style={styles.successIconContainer}>
                <Ionicons name="mail-outline" size={48} color="#960018" />
              </View>
              <Text style={styles.successTitle}>Request Sent!</Text>
              <Text style={styles.successMessage}>
                Your admin registration request has been sent to info@convero.in for approval.
              </Text>
              <Text style={styles.successSubMessage}>
                You will receive an email once your request is approved.
              </Text>
              <TouchableOpacity
                style={styles.successButton}
                onPress={() => {
                  setShowAdminRequestSent(false);
                  router.replace('/auth/login');
                }}
              >
                <Text style={styles.successButtonText}>Go to Login</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Modal>
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
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEE2E2',
    borderWidth: 1,
    borderColor: '#FECACA',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    gap: 10,
  },
  errorText: {
    flex: 1,
    color: '#DC2626',
    fontSize: 14,
    fontWeight: '500',
  },
  // Role dropdown styles
  dropdownButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingRight: 12,
  },
  dropdownText: {
    fontSize: 15,
    color: '#94A3B8',
  },
  dropdownTextSelected: {
    color: '#0F172A',
  },
  roleInfoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EFF6FF',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    gap: 8,
  },
  roleInfoText: {
    flex: 1,
    fontSize: 13,
    color: '#0066CC',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  roleModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 360,
  },
  roleModalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 20,
    textAlign: 'center',
  },
  roleOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#E2E8F0',
    marginBottom: 12,
    gap: 12,
  },
  roleOptionSelected: {
    borderColor: '#960018',
    backgroundColor: '#FEF2F2',
  },
  roleOptionText: {
    flex: 1,
  },
  roleOptionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  roleOptionTitleSelected: {
    color: '#960018',
  },
  roleOptionDesc: {
    fontSize: 13,
    color: '#64748B',
    marginTop: 2,
  },
  // Success modal styles
  successModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 32,
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
  },
  successIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FEF2F2',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  successTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 12,
  },
  successMessage: {
    fontSize: 15,
    color: '#374151',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 8,
  },
  successSubMessage: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    marginBottom: 24,
  },
  successButton: {
    backgroundColor: '#960018',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 10,
    width: '100%',
  },
  successButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
});
