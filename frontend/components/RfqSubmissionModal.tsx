import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Modal,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useCart, CartItem } from '../app/context/CartContext';
import { useAuth } from '../contexts/AuthContext';
import api from '../utils/api';

// Packing types (removed "No Packing" as per user request)
const PACKING_TYPES = [
  { label: 'Standard (1%)', value: 'standard' },
  { label: 'Pallet (4%)', value: 'pallet' },
  { label: 'Wooden Box (8%)', value: 'wooden_box' },
];

interface RfqSubmissionModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: (quoteNumber: string) => void;
  customers?: any[];
}

export default function RfqSubmissionModal({
  visible,
  onClose,
  onSuccess,
  customers = [],
}: RfqSubmissionModalProps) {
  const { user } = useAuth();
  const { cartItems, getCartTotal, getCartWeight, clearCart } = useCart();
  const isCustomer = user?.role === 'customer';

  // Form state
  const [packingType, setPackingType] = useState('standard');
  const [freightPincode, setFreightPincode] = useState('');
  const [customerRfqNo, setCustomerRfqNo] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [showCustomerPicker, setShowCustomerPicker] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Reset form when modal opens
  useEffect(() => {
    if (visible) {
      setPackingType('standard');
      setFreightPincode('');
      setCustomerRfqNo('');
    }
  }, [visible]);

  const handleSubmit = async () => {
    if (cartItems.length === 0) {
      Alert.alert('Error', 'No items in cart');
      return;
    }

    setSubmitting(true);
    try {
      // Prepare products from cart items
      const products = cartItems.map((item) => ({
        product_id: item.product_code,
        product_name: item.product_name,
        quantity: item.quantity,
        unit_price: item.unit_price,
        specifications: item.specifications,
        calculated_discount: 0,
        custom_premium: 0,
        remark: item.remark || null,
        attachments: item.attachments?.map((att) => ({
          name: att.name,
          type: att.type,
          base64: att.base64 || null,
        })) || [],
      }));

      const response = await api.post('/quotes', {
        products,
        customer_id: selectedCustomer?.id || null,
        delivery_location: freightPincode || null,
        packing_type: packingType,
        notes: `${isCustomer ? 'RFQ' : 'Quote'} with ${cartItems.length} items`,
        customer_rfq_no: customerRfqNo || null,
      });

      // Clear cart after successful submission
      clearCart();
      
      // Call success callback with quote number
      onSuccess(response.data.quote_number);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.modalContainer}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>
              {isCustomer ? 'Submit RFQ' : 'Submit Quote'}
            </Text>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Ionicons name="close" size={28} color="#333" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {/* Cart Summary */}
            <View style={styles.summaryCard}>
              <Text style={styles.summaryTitle}>Order Summary</Text>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Items in Cart:</Text>
                <Text style={styles.summaryValue}>{cartItems.length}</Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Total Weight:</Text>
                <Text style={styles.summaryValue}>{getCartWeight().toFixed(2)} kg</Text>
              </View>
              {!isCustomer && (
                <View style={styles.summaryRow}>
                  <Text style={styles.summaryLabel}>Total Amount:</Text>
                  <Text style={styles.summaryValueHighlight}>Rs. {getCartTotal().toFixed(2)}</Text>
                </View>
              )}
            </View>

            {/* Packing Type Selection */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Packing Type</Text>
              <View style={styles.packingOptions}>
                {PACKING_TYPES.map((type) => (
                  <TouchableOpacity
                    key={type.value}
                    style={[
                      styles.packingOption,
                      packingType === type.value && styles.packingOptionSelected,
                    ]}
                    onPress={() => setPackingType(type.value)}
                    data-testid={`packing-${type.value}`}
                  >
                    <Ionicons
                      name={packingType === type.value ? 'radio-button-on' : 'radio-button-off'}
                      size={20}
                      color={packingType === type.value ? '#960018' : '#94A3B8'}
                    />
                    <Text
                      style={[
                        styles.packingOptionText,
                        packingType === type.value && styles.packingOptionTextSelected,
                      ]}
                    >
                      {type.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Freight Pincode */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Delivery Pincode (Optional)</Text>
              <TextInput
                style={styles.input}
                value={freightPincode}
                onChangeText={setFreightPincode}
                placeholder="Enter 6-digit pincode"
                placeholderTextColor="#94A3B8"
                keyboardType="numeric"
                maxLength={6}
                data-testid="freight-pincode-input"
              />
              <Text style={styles.hint}>Used for freight calculation</Text>
            </View>

            {/* Customer RFQ Number (for customers) */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Your Reference No. (Optional)</Text>
              <TextInput
                style={styles.input}
                value={customerRfqNo}
                onChangeText={setCustomerRfqNo}
                placeholder="e.g., PO-12345, REQ-001"
                placeholderTextColor="#94A3B8"
                data-testid="customer-rfq-input"
              />
              <Text style={styles.hint}>Your internal reference for tracking</Text>
            </View>

            {/* Customer Selection (Admin only) */}
            {!isCustomer && customers.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>Select Customer</Text>
                <TouchableOpacity
                  style={styles.customerSelector}
                  onPress={() => setShowCustomerPicker(true)}
                  data-testid="customer-selector"
                >
                  {selectedCustomer ? (
                    <View style={styles.selectedCustomerRow}>
                      <Ionicons name="person" size={20} color="#960018" />
                      <Text style={styles.selectedCustomerName}>{selectedCustomer.name}</Text>
                      <TouchableOpacity onPress={() => setSelectedCustomer(null)}>
                        <Ionicons name="close-circle" size={20} color="#94A3B8" />
                      </TouchableOpacity>
                    </View>
                  ) : (
                    <View style={styles.placeholderRow}>
                      <Ionicons name="person-add-outline" size={20} color="#94A3B8" />
                      <Text style={styles.placeholderText}>Tap to select customer</Text>
                    </View>
                  )}
                </TouchableOpacity>
              </View>
            )}
          </ScrollView>

          {/* Submit Button */}
          <View style={styles.footer}>
            <TouchableOpacity
              style={[styles.cancelButton]}
              onPress={onClose}
              disabled={submitting}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
              onPress={handleSubmit}
              disabled={submitting || cartItems.length === 0}
              data-testid="submit-rfq-btn"
            >
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="send" size={20} color="#fff" />
                  <Text style={styles.submitButtonText}>
                    {isCustomer ? 'Submit RFQ' : 'Submit Quote'}
                  </Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>

      {/* Customer Picker Modal */}
      <Modal
        visible={showCustomerPicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowCustomerPicker(false)}
      >
        <View style={styles.overlay}>
          <View style={styles.pickerModal}>
            <View style={styles.pickerHeader}>
              <Text style={styles.pickerTitle}>Select Customer</Text>
              <TouchableOpacity onPress={() => setShowCustomerPicker(false)}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.pickerList}>
              <TouchableOpacity
                style={styles.pickerOption}
                onPress={() => {
                  setSelectedCustomer(null);
                  setShowCustomerPicker(false);
                }}
              >
                <Text style={styles.pickerOptionText}>No Customer</Text>
              </TouchableOpacity>
              {customers.map((customer) => (
                <TouchableOpacity
                  key={customer.id}
                  style={[
                    styles.pickerOption,
                    selectedCustomer?.id === customer.id && styles.pickerOptionSelected,
                  ]}
                  onPress={() => {
                    setSelectedCustomer(customer);
                    setShowCustomerPicker(false);
                  }}
                >
                  <Text style={styles.pickerOptionName}>{customer.name}</Text>
                  {customer.company && (
                    <Text style={styles.pickerOptionCompany}>{customer.company}</Text>
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    justifyContent: 'flex-end',
  },
  modalContainer: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '85%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
  },
  closeBtn: {
    padding: 4,
  },
  content: {
    padding: 16,
  },
  summaryCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  summaryTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  summaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  summaryValueHighlight: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
    marginBottom: 10,
  },
  packingOptions: {
    gap: 8,
  },
  packingOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#fff',
    gap: 10,
  },
  packingOptionSelected: {
    borderColor: '#960018',
    backgroundColor: '#FEF2F2',
  },
  packingOptionText: {
    fontSize: 14,
    color: '#64748B',
  },
  packingOptionTextSelected: {
    color: '#960018',
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 10,
    padding: 14,
    fontSize: 15,
    color: '#0F172A',
    backgroundColor: '#fff',
  },
  hint: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 6,
  },
  customerSelector: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 10,
    padding: 14,
    backgroundColor: '#fff',
  },
  selectedCustomerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  selectedCustomerName: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: '#0F172A',
  },
  placeholderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  placeholderText: {
    fontSize: 15,
    color: '#94A3B8',
  },
  footer: {
    flexDirection: 'row',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#64748B',
  },
  submitButton: {
    flex: 2,
    flexDirection: 'row',
    padding: 14,
    borderRadius: 10,
    backgroundColor: '#960018',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#fff',
  },
  pickerModal: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '60%',
  },
  pickerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  pickerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
  },
  pickerList: {
    padding: 16,
  },
  pickerOption: {
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  pickerOptionSelected: {
    backgroundColor: '#FEF2F2',
  },
  pickerOptionText: {
    fontSize: 15,
    color: '#64748B',
  },
  pickerOptionName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0F172A',
  },
  pickerOptionCompany: {
    fontSize: 13,
    color: '#64748B',
    marginTop: 2,
  },
});
