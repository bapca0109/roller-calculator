import React from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface ApprovalSuccessModalProps {
  visible: boolean;
  onClose: () => void;
  quoteNumber: string;
  onViewApproved: () => void;
}

export const ApprovalSuccessModal: React.FC<ApprovalSuccessModalProps> = ({
  visible,
  onClose,
  quoteNumber,
  onViewApproved,
}) => {
  return (
    <Modal
      visible={visible}
      animationType="fade"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.content}>
          <View style={styles.iconContainer}>
            <Ionicons name="checkmark-circle" size={64} color="#4CAF50" />
          </View>
          <Text style={styles.title}>Approved & Submitted!</Text>
          <Text style={styles.message}>
            RFQ has been converted to Quote
          </Text>
          <Text style={styles.quoteNumber} data-testid="approved-quote-number">{quoteNumber}</Text>
          <Text style={styles.subtext}>
            The customer has been notified via email.
          </Text>
          <TouchableOpacity 
            style={styles.viewButton}
            onPress={onViewApproved}
            data-testid="view-approved-quotes-btn"
          >
            <Text style={styles.viewButtonText}>View Approved Quotes</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.closeButton}
            onPress={onClose}
            data-testid="close-success-modal"
          >
            <Text style={styles.closeText}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  content: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 32,
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 10,
  },
  iconContainer: {
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1E293B',
    marginBottom: 8,
    textAlign: 'center',
  },
  message: {
    fontSize: 16,
    color: '#64748B',
    marginBottom: 8,
    textAlign: 'center',
  },
  quoteNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
    marginBottom: 16,
    textAlign: 'center',
  },
  subtext: {
    fontSize: 14,
    color: '#94A3B8',
    marginBottom: 24,
    textAlign: 'center',
  },
  viewButton: {
    backgroundColor: '#960018',
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
    marginBottom: 12,
  },
  viewButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  closeButton: {
    paddingVertical: 10,
  },
  closeText: {
    color: '#64748B',
    fontSize: 14,
    fontWeight: '500',
  },
});

export default ApprovalSuccessModal;
