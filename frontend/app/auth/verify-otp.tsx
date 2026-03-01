import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { API_URL } from '../../utils/api';

export default function VerifyOTP() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [otp, setOtp] = useState(['', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const inputRefs = useRef<(TextInput | null)[]>([]);

  const email = params.email as string;
  const name = params.name as string;
  const company = params.company as string;
  const password = params.password as string;

  useEffect(() => {
    // Start with 60 second cooldown after initial OTP send
    setCooldown(60);
  }, []);

  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  const handleOtpChange = (value: string, index: number) => {
    if (value.length > 1) {
      value = value[value.length - 1];
    }
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-focus next input
    if (value && index < 3) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (e: any, index: number) => {
    if (e.nativeEvent.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleVerify = async () => {
    const otpCode = otp.join('');
    if (otpCode.length !== 4) {
      Alert.alert('Error', 'Please enter the complete 4-digit OTP');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/verify-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          otp: otpCode,
          name,
          company: company || null,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Verification failed');
      }

      // Store token and user info
      // Note: In a real app, you'd use AsyncStorage or a context
      Alert.alert(
        'Success',
        'Your email has been verified! You can now log in.',
        [
          {
            text: 'OK',
            onPress: () => router.replace('/auth/login'),
          },
        ]
      );
    } catch (error: any) {
      Alert.alert('Verification Failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (cooldown > 0) return;

    setResendLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/resend-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to resend OTP');
      }

      Alert.alert('OTP Sent', 'A new verification code has been sent to your email.');
      setCooldown(60);
      setOtp(['', '', '', '']);
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Ionicons name="mail-outline" size={48} color="#960018" />
          </View>
          <Text style={styles.title}>Verify Your Email</Text>
          <Text style={styles.subtitle}>
            We've sent a 4-digit code to
          </Text>
          <Text style={styles.email}>{email}</Text>
        </View>

        <View style={styles.otpContainer}>
          {otp.map((digit, index) => (
            <TextInput
              key={index}
              ref={(ref) => (inputRefs.current[index] = ref)}
              style={[
                styles.otpInput,
                digit ? styles.otpInputFilled : null,
              ]}
              value={digit}
              onChangeText={(value) => handleOtpChange(value, index)}
              onKeyPress={(e) => handleKeyPress(e, index)}
              keyboardType="number-pad"
              maxLength={1}
              selectTextOnFocus
              data-testid={`otp-input-${index}`}
            />
          ))}
        </View>

        <TouchableOpacity
          style={[styles.verifyButton, loading && styles.buttonDisabled]}
          onPress={handleVerify}
          disabled={loading}
          data-testid="verify-otp-btn"
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.verifyButtonText}>Verify & Create Account</Text>
          )}
        </TouchableOpacity>

        <View style={styles.resendContainer}>
          <Text style={styles.resendText}>Didn't receive the code?</Text>
          {cooldown > 0 ? (
            <Text style={styles.cooldownText}>
              Resend in {cooldown}s
            </Text>
          ) : (
            <TouchableOpacity
              onPress={handleResendOtp}
              disabled={resendLoading}
              data-testid="resend-otp-btn"
            >
              {resendLoading ? (
                <ActivityIndicator size="small" color="#960018" />
              ) : (
                <Text style={styles.resendLink}>Resend OTP</Text>
              )}
            </TouchableOpacity>
          )}
        </View>

        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={20} color="#64748B" />
          <Text style={styles.backButtonText}>Back to Registration</Text>
        </TouchableOpacity>

        <View style={styles.expiryNote}>
          <Ionicons name="time-outline" size={16} color="#94A3B8" />
          <Text style={styles.expiryText}>Code expires in 10 minutes</Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FEF2F2',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 8,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 15,
    color: '#64748B',
  },
  email: {
    fontSize: 16,
    fontWeight: '600',
    color: '#960018',
    marginTop: 4,
  },
  otpContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 12,
    marginBottom: 32,
  },
  otpInput: {
    width: 60,
    height: 60,
    borderWidth: 2,
    borderColor: '#E2E8F0',
    borderRadius: 12,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
    backgroundColor: '#FFFFFF',
    color: '#0F172A',
  },
  otpInputFilled: {
    borderColor: '#960018',
    backgroundColor: '#FEF2F2',
  },
  verifyButton: {
    backgroundColor: '#960018',
    height: 52,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
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
  verifyButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  resendContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 24,
    gap: 8,
  },
  resendText: {
    fontSize: 14,
    color: '#64748B',
  },
  resendLink: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
  },
  cooldownText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#94A3B8',
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
    gap: 8,
  },
  backButtonText: {
    fontSize: 14,
    color: '#64748B',
  },
  expiryNote: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
    gap: 6,
  },
  expiryText: {
    fontSize: 13,
    color: '#94A3B8',
  },
});
