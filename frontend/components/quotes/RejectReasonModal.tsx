import React from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Quote } from './types';

interface RejectReasonModalProps {
  visible: boolean;
  onClose: () => void;
  quote: Quote | null;
  selectedReason: string | null;
  setSelectedReason: (reason: string | null) => void;
  onConfirmReject: () => Promise<void>;
  isRejecting: boolean;
}

const REJECT_REASONS = [
  { id: 'low_quantity', label: 'Rejected due to low quantity' },
  { id: 'low_amount', label: 'Rejected due to low amount' },
  { id: 'not_in_range', label: 'Rejected due to product is not within the manufacturing range' },
];

export const RejectReasonModal: React.FC<RejectReasonModalProps> = ({
  visible,
  onClose,
  quote,
  selectedReason,
  setSelectedReason,
  onConfirmReject,
  isRejecting,
}) => {
  return (
    <Modal
      visible={visible}
      animationType="fade"
      transparent={false}
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Reject RFQ</Text>
          <TouchableOpacity onPress={onClose} data-testid="close-reject-modal">
            <Ionicons name="close" size={28} color="#333" />
          </TouchableOpacity>
        </View>
        <ScrollView style={styles.scroll}>
          {quote && (
            <>
              <Text style={styles.subtitle}>
                Select a reason for rejecting {quote.quote_number}
              </Text>
              
              <View style={styles.reasonOptions}>
                {REJECT_REASONS.map((reason) => (
                  <TouchableOpacity
                    key={reason.id}
                    style={[
                      styles.reasonOption,
                      selectedReason === reason.id && styles.reasonOptionActive
                    ]}
                    onPress={() => setSelectedReason(reason.id)}
                    data-testid={`reject-reason-${reason.id}`}
                  >
                    <Ionicons 
                      name={selectedReason === reason.id ? 'radio-button-on' : 'radio-button-off'} 
                      size={24} 
                      color={selectedReason === reason.id ? '#960018' : '#666'} 
                    />
                    <Text style={[
                      styles.reasonText,
                      selectedReason === reason.id && styles.reasonTextActive
                    ]}>{reason.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              
              <TouchableOpacity 
                style={[
                  styles.confirmButton,
                  !selectedReason && styles.confirmButtonDisabled
                ]}
                onPress={onConfirmReject}
                disabled={!selectedReason || isRejecting}
                data-testid="confirm-reject-btn"
              >
                {isRejecting ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Ionicons name="close-circle" size={24} color="#fff" />
                    <Text style={styles.confirmButtonText}>Confirm Rejection</Text>
                  </>
                )}
              </TouchableOpacity>
            </>
          )}
        </ScrollView>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  scroll: {
    flex: 1,
    padding: 20,
  },
  subtitle: {
    fontSize: 16,
    color: '#64748B',
    marginBottom: 24,
  },
  reasonOptions: {
    marginBottom: 24,
  },
  reasonOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginBottom: 12,
    gap: 12,
  },
  reasonOptionActive: {
    borderColor: '#960018',
    backgroundColor: '#FFF5F5',
  },
  reasonText: {
    fontSize: 15,
    color: '#475569',
    flex: 1,
  },
  reasonTextActive: {
    color: '#960018',
    fontWeight: '500',
  },
  confirmButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#C41E3A',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  confirmButtonDisabled: {
    backgroundColor: '#94A3B8',
  },
  confirmButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default RejectReasonModal;
