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
  Image,
  Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';

const { height } = Dimensions.get('window');

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleLogin = async () => {
    console.log('[Login] handleLogin called');
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      console.log('[Login] Attempting login...');
      await login(email, password);
      console.log('[Login] Login successful, navigating...');
      router.replace('/(tabs)/calculator');
    } catch (error: any) {
      console.log('[Login] Login failed:', error.message);
      Alert.alert('Login Failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Header Section with Background */}
        <View style={styles.headerSection}>
          <View style={styles.logoContainer}>
            <Image 
              source={require('../../assets/images/convero-logo.png')} 
              style={styles.logo}
              resizeMode="contain"
            />
          </View>
          <Text style={styles.tagline}>INDUSTRIAL PRICING SOLUTIONS</Text>
        </View>

        {/* Form Card */}
        <View style={styles.formCard}>
          <Text style={styles.welcomeText}>Welcome Back</Text>
          <Text style={styles.subtitle}>Sign in to continue</Text>

          {/* Email Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>EMAIL</Text>
            <View style={styles.inputContainer}>
              <Ionicons name="mail-outline" size={20} color="#64748B" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Enter your email"
                placeholderTextColor="#94A3B8"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>
          </View>

          {/* Password Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>PASSWORD</Text>
            <View style={styles.inputContainer}>
              <Ionicons name="lock-closed-outline" size={20} color="#64748B" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Enter your password"
                placeholderTextColor="#94A3B8"
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                returnKeyType="go"
                onSubmitEditing={handleLogin}
              />
              <TouchableOpacity 
                onPress={() => setShowPassword(!showPassword)}
                style={styles.eyeIcon}
              >
                <Ionicons 
                  name={showPassword ? "eye-off-outline" : "eye-outline"} 
                  size={20} 
                  color="#64748B" 
                />
              </TouchableOpacity>
            </View>
          </View>

          {/* Forgot Password */}
          <TouchableOpacity
            style={styles.forgotButton}
            onPress={() => router.push('/auth/forgot-password')}
          >
            <Text style={styles.forgotText}>Forgot Password?</Text>
          </TouchableOpacity>

          {/* Sign In Button */}
          <TouchableOpacity
            style={[styles.signInButton, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.8}
          >
            <Text style={styles.buttonText}>
              {loading ? 'Signing in...' : 'Sign In'}
            </Text>
            {!loading && <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />}
          </TouchableOpacity>

          {/* Divider */}
          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* Sign Up Link */}
          <TouchableOpacity
            style={styles.signUpButton}
            onPress={() => router.push('/auth/register')}
          >
            <Text style={styles.signUpText}>
              Don't have an account? <Text style={styles.signUpTextBold}>Sign Up</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0C1220',
  },
  scrollContent: {
    flexGrow: 1,
    minHeight: height,
  },
  headerSection: {
    backgroundColor: '#0F172A',
    paddingTop: 72,
    paddingBottom: 48,
    alignItems: 'center',
  },
  logoContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 22,
    marginBottom: 18,
    shadowColor: '#C5964A',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.15,
    shadowRadius: 16,
    elevation: 8,
  },
  logo: {
    width: 180,
    height: 80,
  },
  tagline: {
    fontSize: 11,
    fontWeight: '600',
    color: '#C5964A',
    letterSpacing: 3,
  },
  formCard: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    marginTop: -24,
    paddingHorizontal: 28,
    paddingTop: 36,
    paddingBottom: 40,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -8 },
    shadowOpacity: 0.08,
    shadowRadius: 24,
    elevation: 12,
  },
  welcomeText: {
    fontSize: 28,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 4,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginBottom: 36,
    fontWeight: '400',
  },
  inputGroup: {
    marginBottom: 22,
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#C5964A',
    letterSpacing: 1,
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(241, 245, 249, 0.8)',
    borderWidth: 1,
    borderColor: 'rgba(226, 232, 240, 0.5)',
    borderRadius: 14,
    paddingHorizontal: 16,
    height: 54,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: '#0F172A',
    height: '100%',
    fontWeight: '500',
  },
  eyeIcon: {
    padding: 4,
  },
  forgotButton: {
    alignSelf: 'flex-end',
    marginBottom: 28,
  },
  forgotText: {
    fontSize: 13,
    color: '#C5964A',
    fontWeight: '600',
  },
  signInButton: {
    backgroundColor: '#960018',
    height: 56,
    borderRadius: 14,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    cursor: 'pointer',
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
  buttonDisabled: {
    backgroundColor: '#94A3B8',
    shadowOpacity: 0,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 28,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(226, 232, 240, 0.6)',
  },
  dividerText: {
    marginHorizontal: 16,
    fontSize: 13,
    color: '#94A3B8',
    fontWeight: '500',
  },
  signUpButton: {
    alignItems: 'center',
    paddingVertical: 14,
  },
  signUpText: {
    fontSize: 14,
    color: '#64748B',
  },
  signUpTextBold: {
    color: '#960018',
    fontWeight: '700',
  },
});
