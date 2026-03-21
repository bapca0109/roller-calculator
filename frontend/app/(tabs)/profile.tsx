import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Platform,
  Modal,
  Pressable,
  Linking,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [showContactModal, setShowContactModal] = useState(false);
  const [showFaqModal, setShowFaqModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleLogout = async () => {
    try {
      // FIXED: Call logout FIRST to clear state, then navigate
      // The logout function now clears state synchronously before async operations
      // This ensures isAuthenticated becomes false immediately
      await logout();
      
      // Navigation happens AFTER state is cleared
      // The stack is replaced rather than pushed to prevent back navigation
      router.replace('/auth/login');
    } catch (error) {
      console.error('Logout error:', error);
      // Even on error, try to navigate to login
      try {
        router.replace('/auth/login');
      } catch (navError) {
        console.error('Navigation error:', navError);
      }
      Alert.alert('Error', 'Failed to logout completely. Please restart the app.');
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') {
      setDeleteError('Please type DELETE to confirm');
      return;
    }

    setIsDeleting(true);
    setDeleteError('');

    try {
      await api.delete('/account/delete');
      
      // Close modal and logout
      setShowDeleteModal(false);
      await logout();
      router.replace('/auth/login');
      
      if (Platform.OS === 'web') {
        alert('Your account has been deleted successfully.');
      } else {
        Alert.alert('Success', 'Your account has been deleted successfully.');
      }
    } catch (error: any) {
      console.error('Delete account error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to delete account. Please try again.';
      setDeleteError(errorMessage);
    } finally {
      setIsDeleting(false);
    }
  };

  const openDeleteModal = () => {
    setDeleteConfirmText('');
    setDeleteError('');
    setShowDeleteModal(true);
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

        {/* Help & Support Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Help & Support</Text>

          <View style={styles.infoCard}>
            <TouchableOpacity 
              style={styles.supportRow} 
              onPress={() => {
                console.log('FAQs clicked');
                setShowFaqModal(true);
              }}
              activeOpacity={0.7}
            >
              <View style={styles.supportLabel}>
                <Ionicons name="help-circle-outline" size={20} color="#64748B" />
                <Text style={styles.supportLabelText}>FAQs</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#94A3B8" />
            </TouchableOpacity>

            <View style={styles.divider} />

            <TouchableOpacity 
              style={styles.supportRow} 
              onPress={() => {
                console.log('Contact Us clicked');
                setShowContactModal(true);
              }}
              activeOpacity={0.7}
            >
              <View style={styles.supportLabel}>
                <Ionicons name="mail-outline" size={20} color="#64748B" />
                <Text style={styles.supportLabelText}>Contact Us</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#94A3B8" />
            </TouchableOpacity>

            <View style={styles.divider} />

            <View style={styles.supportRow}>
              <View style={styles.supportLabel}>
                <Ionicons name="information-circle-outline" size={20} color="#64748B" />
                <Text style={styles.supportLabelText}>App Version</Text>
              </View>
              <Text style={styles.versionText}>1.0.0</Text>
            </View>
          </View>
        </View>

        {/* Account Actions Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account Actions</Text>

          <View style={styles.infoCard}>
            <TouchableOpacity 
              style={styles.deleteAccountRow} 
              onPress={openDeleteModal}
              activeOpacity={0.7}
              data-testid="delete-account-btn"
            >
              <View style={styles.supportLabel}>
                <Ionicons name="trash-outline" size={20} color="#DC2626" />
                <Text style={styles.deleteAccountText}>Delete Account</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#DC2626" />
            </TouchableOpacity>
          </View>
        </View>

        {/* Contact Us Modal */}
        <Modal
          visible={showContactModal}
          transparent
          animationType="fade"
          onRequestClose={() => setShowContactModal(false)}
        >
          <Pressable 
            style={styles.modalOverlay} 
            onPress={() => setShowContactModal(false)}
          >
            <Pressable style={styles.contactModalContent} onPress={(e) => e.stopPropagation()}>
              <View style={styles.contactModalHeader}>
                <Text style={styles.contactModalTitle}>CONVERO SOLUTIONS</Text>
                <Pressable onPress={() => setShowContactModal(false)} data-testid="close-contact-modal">
                  <Ionicons name="close" size={24} color="#64748B" />
                </Pressable>
              </View>
              
              <View style={styles.contactAddressSection}>
                <Ionicons name="location-outline" size={20} color="#960018" />
                <View style={styles.contactAddressText}>
                  <Text style={styles.contactText}>Plot no. -39, Swapnil Industrial Park,</Text>
                  <Text style={styles.contactText}>Beside shiv aaradhna estate,</Text>
                  <Text style={styles.contactText}>Ahmedabad-Indore Highway,</Text>
                  <Text style={styles.contactText}>Village-Kuha, Ahmedabad,</Text>
                  <Text style={styles.contactText}>Gujarat 382433</Text>
                </View>
              </View>

              <View style={styles.contactDivider} />

              <Pressable 
                style={styles.contactInfoRow}
                onPress={() => Linking.openURL('mailto:Info@convero.in')}
              >
                <Ionicons name="mail-outline" size={20} color="#960018" />
                <Text style={styles.contactInfoText}>Info@convero.in</Text>
              </Pressable>

              <Pressable 
                style={styles.contactInfoRow}
                onPress={() => Linking.openURL('https://www.convero.in')}
              >
                <Ionicons name="globe-outline" size={20} color="#960018" />
                <Text style={styles.contactInfoText}>www.convero.in</Text>
              </Pressable>

              <Pressable 
                style={styles.contactInfoRow}
                onPress={() => Linking.openURL('tel:+919824034311')}
              >
                <Ionicons name="call-outline" size={20} color="#960018" />
                <Text style={styles.contactInfoText}>+91-9824034311</Text>
              </Pressable>
            </Pressable>
          </Pressable>
        </Modal>

        {/* FAQ Modal */}
        <Modal
          visible={showFaqModal}
          transparent
          animationType="fade"
          onRequestClose={() => setShowFaqModal(false)}
        >
          <Pressable 
            style={styles.modalOverlay} 
            onPress={() => setShowFaqModal(false)}
          >
            <Pressable style={styles.contactModalContent} onPress={(e) => e.stopPropagation()}>
              <View style={styles.contactModalHeader}>
                <Text style={styles.contactModalTitle}>Frequently Asked Questions</Text>
                <Pressable onPress={() => setShowFaqModal(false)} data-testid="close-faq-modal">
                  <Ionicons name="close" size={24} color="#64748B" />
                </Pressable>
              </View>
              
              <View style={styles.faqItem}>
                <Text style={styles.faqQuestion}>How to create a quote?</Text>
                <Text style={styles.faqAnswer}>Go to Products → Select items → Add to Cart → Submit RFQ</Text>
              </View>

              <View style={styles.faqItem}>
                <Text style={styles.faqQuestion}>How are prices calculated?</Text>
                <Text style={styles.faqAnswer}>Prices are calculated based on roller specifications including pipe diameter, shaft size, and length.</Text>
              </View>

              <View style={styles.faqItem}>
                <Text style={styles.faqQuestion}>Need more help?</Text>
                <Text style={styles.faqAnswer}>Contact us at Info@convero.in</Text>
              </View>
            </Pressable>
          </Pressable>
        </Modal>

        {/* Delete Account Modal */}
        <Modal
          visible={showDeleteModal}
          transparent
          animationType="fade"
          onRequestClose={() => setShowDeleteModal(false)}
        >
          <Pressable 
            style={styles.modalOverlay} 
            onPress={() => setShowDeleteModal(false)}
          >
            <Pressable style={styles.deleteModalContent} onPress={(e) => e.stopPropagation()}>
              <View style={styles.deleteModalHeader}>
                <Ionicons name="warning-outline" size={40} color="#DC2626" />
                <Text style={styles.deleteModalTitle}>Delete Account</Text>
              </View>
              
              <Text style={styles.deleteWarningText}>
                This action is permanent and cannot be undone. All your data including quotes and customer information will be deleted.
              </Text>

              <Text style={styles.deleteConfirmLabel}>
                Type <Text style={styles.deleteKeyword}>DELETE</Text> to confirm:
              </Text>

              <TextInput
                style={styles.deleteInput}
                value={deleteConfirmText}
                onChangeText={setDeleteConfirmText}
                placeholder="Type DELETE"
                placeholderTextColor="#94A3B8"
                autoCapitalize="characters"
                data-testid="delete-confirm-input"
              />

              {deleteError ? (
                <Text style={styles.deleteErrorText}>{deleteError}</Text>
              ) : null}

              <View style={styles.deleteButtonRow}>
                <TouchableOpacity 
                  style={styles.cancelButton}
                  onPress={() => setShowDeleteModal(false)}
                  data-testid="cancel-delete-btn"
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={[styles.confirmDeleteButton, isDeleting && styles.disabledButton]}
                  onPress={handleDeleteAccount}
                  disabled={isDeleting}
                  data-testid="confirm-delete-btn"
                >
                  {isDeleting ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.confirmDeleteButtonText}>Delete Account</Text>
                  )}
                </TouchableOpacity>
              </View>
            </Pressable>
          </Pressable>
        </Modal>

        {Platform.OS === 'web' ? (
          <button
            onClick={handleLogout}
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
            onPress={handleLogout}
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
    backgroundColor: '#F8FAFC',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 56,
    paddingBottom: 20,
    backgroundColor: '#0F172A',
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -0.3,
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
    borderWidth: 1,
    borderColor: '#F1F5F9',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  avatarContainer: {
    marginBottom: 16,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#960018',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 32,
    fontWeight: '700',
    color: '#fff',
  },
  userName: {
    fontSize: 22,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 14,
    color: '#64748B',
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
    color: '#0F172A',
    marginBottom: 12,
  },
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
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
  supportRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
  },
  supportLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  supportLabelText: {
    fontSize: 16,
    color: '#3C3C43',
  },
  versionText: {
    fontSize: 14,
    color: '#94A3B8',
    fontWeight: '500',
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
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  contactModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  contactModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  contactModalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
  },
  contactAddressSection: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  contactAddressText: {
    marginLeft: 12,
    flex: 1,
  },
  contactText: {
    fontSize: 14,
    color: '#64748B',
    lineHeight: 22,
  },
  contactDivider: {
    height: 1,
    backgroundColor: '#E2E8F0',
    marginVertical: 16,
  },
  contactInfoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    cursor: 'pointer',
  },
  contactInfoText: {
    fontSize: 14,
    color: '#0F172A',
    marginLeft: 12,
    fontWeight: '500',
  },
  faqItem: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  faqQuestion: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0F172A',
    marginBottom: 6,
  },
  faqAnswer: {
    fontSize: 14,
    color: '#64748B',
    lineHeight: 20,
  },
  // Delete Account Styles
  deleteAccountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
  },
  deleteAccountText: {
    fontSize: 16,
    color: '#DC2626',
    fontWeight: '500',
  },
  deleteModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
  },
  deleteModalHeader: {
    alignItems: 'center',
    marginBottom: 16,
  },
  deleteModalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#DC2626',
    marginTop: 12,
  },
  deleteWarningText: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 20,
  },
  deleteConfirmLabel: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
    alignSelf: 'flex-start',
  },
  deleteKeyword: {
    fontWeight: '700',
    color: '#DC2626',
  },
  deleteInput: {
    width: '100%',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    marginBottom: 12,
    textAlign: 'center',
    letterSpacing: 2,
  },
  deleteErrorText: {
    color: '#DC2626',
    fontSize: 13,
    marginBottom: 12,
    textAlign: 'center',
  },
  deleteButtonRow: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
    marginTop: 8,
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#64748B',
  },
  confirmDeleteButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    backgroundColor: '#DC2626',
    alignItems: 'center',
  },
  confirmDeleteButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  disabledButton: {
    opacity: 0.6,
  },
});
