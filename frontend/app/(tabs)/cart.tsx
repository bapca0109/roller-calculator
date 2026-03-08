import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Modal,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useCart } from '../context/CartContext';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

// Packing types
const PACKING_TYPES = [
  { label: 'Standard (1%)', value: 'standard' },
  { label: 'Pallet (4%)', value: 'pallet' },
  { label: 'Wooden Box (8%)', value: 'wooden_box' },
];

export default function CartScreen() {
  const { user } = useAuth();
  const { cartItems, removeFromCart, updateCartItem, getCartTotal, getCartWeight, clearCart } = useCart();
  const isCustomer = user?.role === 'customer';

  // Submission modal state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [packingType, setPackingType] = useState('standard');
  const [freightPincode, setFreightPincode] = useState('');
  const [customerRfqNo, setCustomerRfqNo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Success state
  const [showSuccess, setShowSuccess] = useState(false);
  const [submittedNumber, setSubmittedNumber] = useState('');

  // Edit quantity state
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editQty, setEditQty] = useState('');

  const startEditQty = (itemId: string, currentQty: number) => {
    setEditingItemId(itemId);
    setEditQty(currentQty.toString());
  };

  const saveEditQty = (itemId: string) => {
    const newQty = parseInt(editQty);
    if (isNaN(newQty) || newQty < 1) {
      Alert.alert('Invalid Quantity', 'Please enter a valid quantity (minimum 1)');
      return;
    }
    if (newQty > 10000) {
      Alert.alert('Invalid Quantity', 'Maximum quantity is 10,000');
      return;
    }
    updateCartItem(itemId, { quantity: newQty });
    setEditingItemId(null);
    setEditQty('');
  };

  const cancelEditQty = () => {
    setEditingItemId(null);
    setEditQty('');
  };

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
        customer_id: null,
        delivery_location: freightPincode || null,
        packing_type: packingType,
        notes: `${isCustomer ? 'RFQ' : 'Quote'} with ${cartItems.length} items`,
        customer_rfq_no: customerRfqNo || null,
      });

      // Clear cart after successful submission
      clearCart();
      setShowSubmitModal(false);
      
      // Show success
      setSubmittedNumber(response.data.quote_number);
      setShowSuccess(true);
      
      // Reset form
      setPackingType('standard');
      setFreightPincode('');
      setCustomerRfqNo('');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{isCustomer ? 'RFQ Cart' : 'Quote Cart'}</Text>
        <Text style={styles.headerSubtitle}>
          {cartItems.length} item{cartItems.length !== 1 ? 's' : ''} in cart
        </Text>
      </View>

      {/* Cart Items */}
      {cartItems.length === 0 ? (
        <View style={styles.emptyCart}>
          <Ionicons name="cart-outline" size={80} color="#E2E8F0" />
          <Text style={styles.emptyCartTitle}>Your cart is empty</Text>
          <Text style={styles.emptyCartText}>
            Add items from the Calculator tab using Search or Configure options
          </Text>
        </View>
      ) : (
        <>
          <ScrollView style={styles.itemsList} showsVerticalScrollIndicator={false}>
            {cartItems.map((item, index) => (
              <View key={item.id} style={styles.cartItem}>
                <View style={styles.itemHeader}>
                  <View style={styles.itemCodeContainer}>
                    <Text style={styles.itemCode}>{item.product_code}</Text>
                    <View style={[
                      styles.sourceTag,
                      item.source === 'calculator' ? styles.calculatorTag : styles.searchTag
                    ]}>
                      <Text style={styles.sourceTagText}>
                        {item.source === 'calculator' ? 'CALC' : 'SEARCH'}
                      </Text>
                    </View>
                  </View>
                  <TouchableOpacity
                    onPress={() => removeFromCart(item.id)}
                    style={styles.removeBtn}
                  >
                    <Ionicons name="trash-outline" size={22} color="#EF4444" />
                  </TouchableOpacity>
                </View>

                <Text style={styles.itemName}>{item.product_name}</Text>

                <View style={styles.itemSpecs}>
                  {item.specifications.pipe_diameter && (
                    <Text style={styles.specText}>
                      Pipe: {item.specifications.pipe_diameter}mm x {item.specifications.pipe_length}mm
                    </Text>
                  )}
                  {item.specifications.bearing && (
                    <Text style={styles.specText}>
                      Bearing: {item.specifications.bearing} ({item.specifications.bearing_make?.toUpperCase()})
                    </Text>
                  )}
                </View>

                <View style={styles.itemFooter}>
                  <View style={styles.qtyWeightRow}>
                    {/* Editable Quantity */}
                    {editingItemId === item.id ? (
                      <View style={styles.editQtyContainer}>
                        <TextInput
                          style={styles.editQtyInput}
                          value={editQty}
                          onChangeText={setEditQty}
                          keyboardType="numeric"
                          autoFocus
                          selectTextOnFocus
                        />
                        <TouchableOpacity 
                          style={styles.editQtySaveBtn}
                          onPress={() => saveEditQty(item.id)}
                        >
                          <Ionicons name="checkmark" size={18} color="#fff" />
                        </TouchableOpacity>
                        <TouchableOpacity 
                          style={styles.editQtyCancelBtn}
                          onPress={cancelEditQty}
                        >
                          <Ionicons name="close" size={18} color="#666" />
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity 
                        style={styles.qtyEditableBox}
                        onPress={() => startEditQty(item.id, item.quantity)}
                      >
                        <Text style={styles.infoLabel}>Qty</Text>
                        <View style={styles.qtyValueRow}>
                          <Text style={styles.infoValue}>{item.quantity}</Text>
                          <Ionicons name="pencil" size={14} color="#960018" style={styles.editIcon} />
                        </View>
                      </TouchableOpacity>
                    )}
                    <View style={styles.infoBox}>
                      <Text style={styles.infoLabel}>Weight</Text>
                      <Text style={styles.infoValue}>{(item.weight_kg * item.quantity).toFixed(2)} kg</Text>
                    </View>
                    {!isCustomer && (
                      <View style={[styles.infoBox, styles.priceBox]}>
                        <Text style={styles.infoLabel}>Total</Text>
                        <Text style={styles.priceValue}>₹{(item.unit_price * item.quantity).toFixed(0)}</Text>
                      </View>
                    )}
                  </View>
                </View>

                {/* Show remark if present */}
                {item.remark && (
                  <View style={styles.remarkContainer}>
                    <Ionicons name="chatbubble-outline" size={14} color="#64748B" />
                    <Text style={styles.remarkText}>{item.remark}</Text>
                  </View>
                )}

                {/* Show attachments count */}
                {item.attachments && item.attachments.length > 0 && (
                  <View style={styles.attachmentsRow}>
                    <Ionicons name="attach" size={14} color="#64748B" />
                    <Text style={styles.attachmentsText}>
                      {item.attachments.length} attachment{item.attachments.length !== 1 ? 's' : ''}
                    </Text>
                  </View>
                )}
              </View>
            ))}
            <View style={{ height: 120 }} />
          </ScrollView>

          {/* Footer with Summary & Confirm Button */}
          <View style={styles.footer}>
            <View style={styles.summaryRow}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryLabel}>Items</Text>
                <Text style={styles.summaryValue}>{cartItems.length}</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryLabel}>Weight</Text>
                <Text style={styles.summaryValue}>{getCartWeight().toFixed(2)} kg</Text>
              </View>
              {!isCustomer && (
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>Total</Text>
                  <Text style={styles.totalValue}>₹{getCartTotal().toFixed(0)}</Text>
                </View>
              )}
            </View>
            <TouchableOpacity
              style={styles.confirmButton}
              onPress={() => setShowSubmitModal(true)}
            >
              <Ionicons name="checkmark-circle" size={22} color="#fff" />
              <Text style={styles.confirmButtonText}>Confirm & Submit</Text>
            </TouchableOpacity>
          </View>
        </>
      )}

      {/* Submission Modal */}
      <Modal
        visible={showSubmitModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowSubmitModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Submit {isCustomer ? 'RFQ' : 'Quote'}</Text>
              <TouchableOpacity onPress={() => setShowSubmitModal(false)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              {/* Packing Type */}
              <View style={styles.fieldSection}>
                <Text style={styles.fieldLabel}>Packing Type (Optional)</Text>
                <View style={styles.packingOptions}>
                  {PACKING_TYPES.map((type) => (
                    <TouchableOpacity
                      key={type.value}
                      style={[
                        styles.packingOption,
                        packingType === type.value && styles.packingOptionSelected,
                      ]}
                      onPress={() => setPackingType(type.value)}
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
              <View style={styles.fieldSection}>
                <Text style={styles.fieldLabel}>Delivery Pincode (Optional)</Text>
                <TextInput
                  style={styles.input}
                  value={freightPincode}
                  onChangeText={setFreightPincode}
                  placeholder="Enter 6-digit pincode for freight"
                  placeholderTextColor="#94A3B8"
                  keyboardType="numeric"
                  maxLength={6}
                />
              </View>

              {/* Customer RFQ No */}
              <View style={styles.fieldSection}>
                <Text style={styles.fieldLabel}>Your Reference No. (Optional)</Text>
                <TextInput
                  style={styles.input}
                  value={customerRfqNo}
                  onChangeText={setCustomerRfqNo}
                  placeholder="e.g., PO-12345, REQ-001"
                  placeholderTextColor="#94A3B8"
                />
                <Text style={styles.hint}>Your internal reference for tracking</Text>
              </View>
            </ScrollView>

            <View style={styles.modalFooter}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setShowSubmitModal(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.submitButton, submitting && styles.submitButtonDisabled]}
                onPress={handleSubmit}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Ionicons name="send" size={20} color="#fff" />
                    <Text style={styles.submitButtonText}>
                      Submit {isCustomer ? 'RFQ' : 'Quote'}
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Success Modal */}
      <Modal
        visible={showSuccess}
        animationType="fade"
        transparent
        onRequestClose={() => setShowSuccess(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.successContent}>
            <Ionicons name="checkmark-circle" size={72} color="#4CAF50" />
            <Text style={styles.successTitle}>
              {isCustomer ? 'RFQ Submitted!' : 'Quote Generated!'}
            </Text>
            <Text style={styles.successSubtitle}>
              Your {isCustomer ? 'Request for Quotation' : 'Quote'} has been {isCustomer ? 'sent' : 'created'} successfully.
            </Text>
            <Text style={styles.successNumber}>{submittedNumber}</Text>
            <TouchableOpacity
              style={styles.successButton}
              onPress={() => setShowSuccess(false)}
            >
              <Ionicons name="checkmark" size={24} color="#fff" />
              <Text style={styles.successButtonText}>Done</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  header: {
    backgroundColor: '#1E293B',
    paddingTop: 56,
    paddingBottom: 20,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  headerTitle: {
    fontSize: 26,
    fontWeight: '700',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginTop: 4,
  },
  emptyCart: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  emptyCartTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
    marginTop: 20,
  },
  emptyCartText: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
  itemsList: {
    flex: 1,
    padding: 16,
  },
  cartItem: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  itemCodeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  itemCode: {
    fontSize: 17,
    fontWeight: '700',
    color: '#960018',
  },
  sourceTag: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  calculatorTag: {
    backgroundColor: '#DBEAFE',
  },
  searchTag: {
    backgroundColor: '#D1FAE5',
  },
  sourceTagText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#0F172A',
  },
  removeBtn: {
    padding: 6,
  },
  itemName: {
    fontSize: 14,
    color: '#0F172A',
    marginBottom: 10,
  },
  itemSpecs: {
    marginBottom: 12,
  },
  specText: {
    fontSize: 13,
    color: '#64748B',
    marginBottom: 3,
  },
  itemFooter: {
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  qtyWeightRow: {
    flexDirection: 'row',
    gap: 12,
  },
  infoBox: {
    backgroundColor: '#F8FAFC',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  qtyEditableBox: {
    backgroundColor: '#FEF2F2',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#960018',
  },
  qtyValueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  editIcon: {
    marginLeft: 4,
  },
  editQtyContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  editQtyInput: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#960018',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    width: 70,
    textAlign: 'center',
  },
  editQtySaveBtn: {
    backgroundColor: '#4CAF50',
    padding: 8,
    borderRadius: 6,
  },
  editQtyCancelBtn: {
    backgroundColor: '#E2E8F0',
    padding: 8,
    borderRadius: 6,
  },
  priceBox: {
    flex: 1,
    backgroundColor: '#FEF2F2',
  },
  infoLabel: {
    fontSize: 11,
    color: '#64748B',
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  priceValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  remarkContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  remarkText: {
    flex: 1,
    fontSize: 12,
    color: '#64748B',
    fontStyle: 'italic',
  },
  attachmentsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  attachmentsText: {
    fontSize: 12,
    color: '#64748B',
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    paddingBottom: 24,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 14,
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#64748B',
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  confirmButton: {
    flexDirection: 'row',
    backgroundColor: '#960018',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  confirmButtonText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#fff',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
  },
  modalBody: {
    padding: 20,
  },
  fieldSection: {
    marginBottom: 24,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
    marginBottom: 10,
  },
  packingOptions: {
    gap: 10,
  },
  packingOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
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
    fontSize: 15,
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
  modalFooter: {
    flexDirection: 'row',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    padding: 16,
    borderRadius: 10,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#64748B',
  },
  submitButton: {
    flex: 2,
    flexDirection: 'row',
    padding: 16,
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
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  // Success modal
  successContent: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 32,
    alignItems: 'center',
    marginHorizontal: 24,
    marginTop: 'auto',
    marginBottom: 'auto',
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#0F172A',
    marginTop: 16,
  },
  successSubtitle: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    marginTop: 8,
  },
  successNumber: {
    fontSize: 18,
    fontWeight: '600',
    color: '#960018',
    marginTop: 8,
    marginBottom: 20,
  },
  successButton: {
    flexDirection: 'row',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: 10,
    alignItems: 'center',
    gap: 8,
  },
  successButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
