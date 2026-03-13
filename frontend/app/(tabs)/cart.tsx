import React, { useState, useEffect } from 'react';
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
  KeyboardAvoidingView,
  Platform,
  Pressable,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useCart } from '../context/CartContext';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { ExportButtons } from '../../components/shared/ExportButtons';

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

  // Customer selection state (for admin)
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [showCustomerPicker, setShowCustomerPicker] = useState(false);
  const [customerSearchQuery, setCustomerSearchQuery] = useState('');

  // Submission modal state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [packingType, setPackingType] = useState('standard');
  const [freightPincode, setFreightPincode] = useState('');
  const [customerRfqNo, setCustomerRfqNo] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Admin custom fields
  const [customFreightAmount, setCustomFreightAmount] = useState('');
  const [useCustomFreight, setUseCustomFreight] = useState(false);
  const [customPackingPercent, setCustomPackingPercent] = useState('');
  const [useCustomPacking, setUseCustomPacking] = useState(false);

  // Pincode validation state
  const [pincodeValid, setPincodeValid] = useState<boolean | null>(null);
  const [pincodeError, setPincodeError] = useState('');
  const [validatingPincode, setValidatingPincode] = useState(false);
  
  // Freight calculation state
  const [calculatedFreight, setCalculatedFreight] = useState(0);
  const [calculatingFreight, setCalculatingFreight] = useState(false);

  // Success state
  const [showSuccess, setShowSuccess] = useState(false);
  const [submittedNumber, setSubmittedNumber] = useState('');

  // Edit quantity state
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editQty, setEditQty] = useState('');

  // Fetch customers for admin
  useEffect(() => {
    const fetchCustomers = async () => {
      if (!isCustomer) {
        try {
          const response = await api.get('/customers');
          setCustomers(response.data.customers || []);
        } catch (error) {
          console.log('Failed to fetch customers');
        }
      }
    };
    fetchCustomers();
  }, [isCustomer]);

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

  // Pincode validation function
  const validatePincode = async (pincode: string) => {
    if (!pincode || pincode.length === 0) {
      // Empty pincode is valid (it's optional)
      setPincodeValid(null);
      setPincodeError('');
      return;
    }

    // Basic format check
    if (!/^\d{6}$/.test(pincode)) {
      setPincodeValid(false);
      setPincodeError('Please enter a valid 6-digit pincode');
      return;
    }

    // Validate with API
    setValidatingPincode(true);
    try {
      const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const data = await response.json();
      
      if (data[0]?.Status === 'Success' && data[0]?.PostOffice?.length > 0) {
        setPincodeValid(true);
        setPincodeError('');
      } else {
        setPincodeValid(false);
        setPincodeError('Invalid pincode. Please enter a valid Indian pincode.');
      }
    } catch (error) {
      // If API fails, allow the pincode (don't block submission)
      setPincodeValid(true);
      setPincodeError('');
    } finally {
      setValidatingPincode(false);
    }
  };

  // Handle pincode change with debounce
  const handlePincodeChange = (value: string) => {
    // Only allow digits
    const cleaned = value.replace(/\D/g, '');
    setFreightPincode(cleaned);
    
    // Reset validation state while typing
    if (cleaned.length < 6) {
      setPincodeValid(null);
      setPincodeError(cleaned.length > 0 ? 'Please enter a valid 6-digit pincode' : '');
      setCalculatedFreight(0);
    } else if (cleaned.length === 6) {
      // Validate when 6 digits are entered
      validatePincode(cleaned);
      // Calculate freight
      calculateFreight(cleaned);
    }
  };

  // Calculate freight based on pincode and cart items weight
  const calculateFreight = async (pincode: string) => {
    if (!pincode || pincode.length !== 6) {
      setCalculatedFreight(0);
      return;
    }

    // Calculate total weight from cart items using actual weight_kg
    let totalWeight = 0;
    
    for (const item of cartItems) {
      let weightPerUnit = item.weight_kg || 0;
      
      // If weight_kg is 0 or missing, try to get it from the API
      if (weightPerUnit === 0) {
        const specs = item.specifications || {};
        
        // Try to extract specs from product_code if not in specifications
        // Product code format: CR25 89 1000B 62C = roller_type shaft pipe_dia lengthPipe_type bearing
        let pipeD = specs.pipe_diameter;
        let pipeL = specs.pipe_length;
        let shaftD = specs.shaft_diameter;
        let pipeT = specs.pipe_type || 'B';
        
        // If specs are missing, try to parse from product_code
        if ((!pipeD || !pipeL || !shaftD) && item.product_code) {
          const parts = item.product_code.split(' ');
          if (parts.length >= 4) {
            // CR25 89 1000B 62C
            shaftD = shaftD || parseInt(parts[0].replace(/\D/g, '')) || 25;
            pipeD = pipeD || parseFloat(parts[1]) || 88.9;
            const lengthPart = parts[2] || '1000B';
            pipeL = pipeL || parseInt(lengthPart.replace(/\D/g, '')) || 1000;
            pipeT = pipeT || (lengthPart.match(/[ABC]/)?.[0]) || 'B';
          }
        }
        
        if (pipeD && pipeL && shaftD) {
          try {
            const response = await api.post('/calculate-detailed-cost', {
              roller_type: item.roller_type || 'carrying',
              pipe_diameter: pipeD,
              pipe_length: pipeL,
              pipe_type: pipeT,
              shaft_diameter: shaftD,
              bearing: specs.bearing || '6205',
              bearing_number: specs.bearing || '6205',
              bearing_make: specs.bearing_make || 'skf',
              housing: specs.housing || 'CI Machined',
              quantity: 1
            });
            
            if (response.data?.cost_breakdown?.single_roller_weight_kg) {
              weightPerUnit = response.data.cost_breakdown.single_roller_weight_kg;
              console.log(`Fetched weight for ${item.product_code}: ${weightPerUnit} kg`);
            }
          } catch (err) {
            console.log('Could not fetch weight for item:', item.product_code, err);
          }
        }
      }
      
      // Fallback to estimated weight based on roller type if still 0
      if (weightPerUnit === 0) {
        const rollerType = (item.roller_type || item.product_name || '').toLowerCase();
        if (rollerType.includes('impact')) weightPerUnit = 15;
        else if (rollerType.includes('return')) weightPerUnit = 8;
        else weightPerUnit = 12; // Carrying roller average
        console.log(`Using estimated weight for ${item.product_code}: ${weightPerUnit} kg`);
      }
      
      totalWeight += weightPerUnit * item.quantity;
    }

    console.log('Total calculated weight:', totalWeight, 'kg');

    if (totalWeight === 0) {
      setCalculatedFreight(0);
      return;
    }

    setCalculatingFreight(true);
    try {
      const response = await api.post('/calculate-freight', {
        pincode: pincode,
        total_weight_kg: totalWeight
      });
      
      if (response.data && response.data.freight_charges) {
        setCalculatedFreight(response.data.freight_charges);
      }
    } catch (error) {
      console.error('Freight calculation error:', error);
      setCalculatedFreight(0);
    } finally {
      setCalculatingFreight(false);
    }
  };

  const handleSubmit = async () => {
    if (cartItems.length === 0) {
      Alert.alert('Error', 'No items in cart');
      return;
    }

    // Admin must select a customer before submitting
    if (!isCustomer && !selectedCustomer) {
      Alert.alert('Customer Required', 'Please select a customer before submitting the RFQ.');
      return;
    }

    // Check if pincode is entered but invalid
    if (freightPincode && freightPincode.length > 0) {
      if (freightPincode.length !== 6) {
        Alert.alert('Invalid Pincode', 'Please enter a valid 6-digit pincode');
        return;
      }
      if (pincodeValid === false) {
        Alert.alert('Invalid Pincode', 'Please enter a valid Indian pincode or leave it empty');
        return;
      }
      if (validatingPincode) {
        Alert.alert('Please Wait', 'Pincode validation in progress');
        return;
      }
    }

    setSubmitting(true);
    try {
      // Prepare products from cart items
      const products = cartItems.map((item) => ({
        product_id: item.product_code,
        product_name: item.product_name,
        quantity: item.quantity,
        unit_price: item.unit_price,
        weight: item.weight_kg,  // Include weight for PDF generation
        weight_kg: item.weight_kg,  // Include weight_kg for PDF generation
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
        packing_type: useCustomPacking ? `custom_${customPackingPercent}` : packingType,
        shipping_cost: useCustomFreight ? (parseFloat(customFreightAmount) || 0) : (calculatedFreight || 0),
        freight_details: useCustomFreight ? { freight_amount: parseFloat(customFreightAmount) || 0 } : null,
        notes: `${isCustomer ? 'RFQ' : 'RFQ'} with ${cartItems.length} items`,
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
      setPincodeValid(null);
      setPincodeError('');
      setCustomFreightAmount('');
      setUseCustomFreight(false);
      setCustomPackingPercent('');
      setUseCustomPacking(false);
      setSelectedCustomer(null);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>{isCustomer ? 'RFQ Cart' : 'Quote Cart'}</Text>
          <Text style={styles.headerSubtitle}>
            {cartItems.length} item{cartItems.length !== 1 ? 's' : ''} in cart
          </Text>
        </View>
        {cartItems.length > 0 && (
          <ExportButtons
            endpoint="/api/cart/export/excel"
            filenamePrefix="Cart"
            compact={true}
          />
        )}
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
          <ScrollView 
            style={styles.itemsList} 
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ paddingBottom: 100 }}
          >
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
                      <Text style={styles.infoValue}>{((item.weight_kg || 0) * item.quantity).toFixed(2)} kg</Text>
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
                <Ionicons name="close" size={28} color="#fff" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              {/* Customer Selection - Admin Only */}
              {!isCustomer && (
                <View style={styles.fieldSection}>
                  <Text style={[styles.fieldLabel, { color: '#960018' }]}>Select Customer *</Text>
                  <TouchableOpacity
                    style={[
                      styles.input,
                      { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
                      !selectedCustomer && { borderColor: '#DC2626' }
                    ]}
                    onPress={() => setShowCustomerPicker(true)}
                  >
                    <Text style={{ color: selectedCustomer ? '#333' : '#94A3B8' }}>
                      {selectedCustomer ? `${selectedCustomer.name} (${selectedCustomer.customer_code})` : 'Select Customer (Required)'}
                    </Text>
                    <Ionicons name="chevron-down" size={20} color="#94A3B8" />
                  </TouchableOpacity>
                </View>
              )}

              {/* Packing Type */}
              <View style={styles.fieldSection}>
                <Text style={styles.fieldLabel}>Packing Type (Optional)</Text>
                <View style={styles.packingOptions}>
                  {PACKING_TYPES.map((type) => (
                    <TouchableOpacity
                      key={type.value}
                      style={[
                        styles.packingOption,
                        packingType === type.value && !useCustomPacking && styles.packingOptionSelected,
                      ]}
                      onPress={() => {
                        setPackingType(type.value);
                        setUseCustomPacking(false);
                      }}
                    >
                      <Ionicons
                        name={packingType === type.value && !useCustomPacking ? 'radio-button-on' : 'radio-button-off'}
                        size={20}
                        color={packingType === type.value && !useCustomPacking ? '#960018' : '#94A3B8'}
                      />
                      <Text
                        style={[
                          styles.packingOptionText,
                          packingType === type.value && !useCustomPacking && styles.packingOptionTextSelected,
                        ]}
                      >
                        {type.label}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                
                {/* Custom Packing % - Admin Only */}
                {!isCustomer && (
                  <View style={{ marginTop: 12 }}>
                    <TouchableOpacity
                      style={[
                        styles.packingOption,
                        useCustomPacking && styles.packingOptionSelected,
                      ]}
                      onPress={() => setUseCustomPacking(!useCustomPacking)}
                    >
                      <Ionicons
                        name={useCustomPacking ? 'radio-button-on' : 'radio-button-off'}
                        size={20}
                        color={useCustomPacking ? '#960018' : '#94A3B8'}
                      />
                      <Text style={[styles.packingOptionText, useCustomPacking && styles.packingOptionTextSelected]}>
                        Custom Packing %
                      </Text>
                    </TouchableOpacity>
                    {useCustomPacking && (
                      <TextInput
                        style={[styles.input, { marginTop: 8 }]}
                        value={customPackingPercent}
                        onChangeText={setCustomPackingPercent}
                        placeholder="Enter packing % (e.g., 2.5)"
                        placeholderTextColor="#94A3B8"
                        keyboardType="decimal-pad"
                      />
                    )}
                  </View>
                )}
              </View>

              {/* Freight Pincode */}
              <View style={styles.fieldSection}>
                <Text style={styles.fieldLabel}>Delivery Pincode (Optional)</Text>
                <View style={styles.pincodeInputContainer}>
                  <TextInput
                    style={[
                      styles.input,
                      styles.pincodeInput,
                      pincodeValid === false && styles.inputError,
                      pincodeValid === true && styles.inputSuccess,
                    ]}
                    value={freightPincode}
                    onChangeText={handlePincodeChange}
                    placeholder="Enter 6-digit pincode for freight"
                    placeholderTextColor="#94A3B8"
                    keyboardType="numeric"
                    maxLength={6}
                  />
                  {validatingPincode && (
                    <View style={styles.pincodeStatusIcon}>
                      <ActivityIndicator size="small" color="#960018" />
                    </View>
                  )}
                  {!validatingPincode && pincodeValid === true && (
                    <View style={styles.pincodeStatusIcon}>
                      <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
                    </View>
                  )}
                  {!validatingPincode && pincodeValid === false && (
                    <View style={styles.pincodeStatusIcon}>
                      <Ionicons name="close-circle" size={24} color="#DC3545" />
                    </View>
                  )}
                </View>
                {pincodeError ? (
                  <Text style={styles.errorText}>{pincodeError}</Text>
                ) : null}
                {calculatingFreight && (
                  <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 8 }}>
                    <ActivityIndicator size="small" color="#960018" />
                    <Text style={{ marginLeft: 8, color: '#666' }}>Calculating freight...</Text>
                  </View>
                )}
                {calculatedFreight > 0 && !calculatingFreight && (
                  <Text style={{ color: '#059669', fontSize: 14, marginTop: 8, fontWeight: '600' }}>
                    Estimated Freight: Rs. {calculatedFreight.toFixed(2)}
                  </Text>
                )}
                
                {/* Custom Freight Amount - Admin Only */}
                {!isCustomer && (
                  <View style={{ marginTop: 12 }}>
                    <TouchableOpacity
                      style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}
                      onPress={() => setUseCustomFreight(!useCustomFreight)}
                    >
                      <Ionicons
                        name={useCustomFreight ? 'checkbox' : 'square-outline'}
                        size={22}
                        color={useCustomFreight ? '#960018' : '#94A3B8'}
                      />
                      <Text style={{ marginLeft: 8, fontSize: 14, color: '#333' }}>
                        Use Custom Freight Amount
                      </Text>
                    </TouchableOpacity>
                    {useCustomFreight && (
                      <TextInput
                        style={styles.input}
                        value={customFreightAmount}
                        onChangeText={setCustomFreightAmount}
                        placeholder="Enter freight amount (e.g., 5000)"
                        placeholderTextColor="#94A3B8"
                        keyboardType="decimal-pad"
                      />
                    )}
                  </View>
                )}
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
                style={[
                  styles.submitButton, 
                  (submitting || validatingPincode || (freightPincode.length > 0 && pincodeValid === false)) && styles.submitButtonDisabled
                ]}
                onPress={handleSubmit}
                disabled={submitting || validatingPincode || (freightPincode.length > 0 && pincodeValid === false)}
              >
                {submitting ? (
                  <ActivityIndicator color="#fff" />
                ) : validatingPincode ? (
                  <>
                    <ActivityIndicator color="#fff" size="small" />
                    <Text style={styles.submitButtonText}>Validating...</Text>
                  </>
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

      {/* Customer Picker Modal - Admin Only */}
      <Modal
        visible={showCustomerPicker}
        transparent
        animationType="slide"
        onRequestClose={() => {
          setShowCustomerPicker(false);
          setCustomerSearchQuery('');
        }}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '70%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Customer</Text>
              <TouchableOpacity onPress={() => {
                setShowCustomerPicker(false);
                setCustomerSearchQuery('');
              }}>
                <Ionicons name="close" size={28} color="#fff" />
              </TouchableOpacity>
            </View>
            
            {/* Search Input */}
            <View style={{ paddingHorizontal: 16, paddingBottom: 12 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#F1F5F9', borderRadius: 8, paddingHorizontal: 12 }}>
                <Ionicons name="search" size={20} color="#64748B" />
                <TextInput
                  style={{ flex: 1, paddingVertical: 10, paddingHorizontal: 8, fontSize: 14, color: '#333' }}
                  placeholder="Search by name, code or company..."
                  placeholderTextColor="#94A3B8"
                  value={customerSearchQuery}
                  onChangeText={setCustomerSearchQuery}
                  autoCapitalize="none"
                />
                {customerSearchQuery.length > 0 && (
                  <TouchableOpacity onPress={() => setCustomerSearchQuery('')}>
                    <Ionicons name="close-circle" size={20} color="#94A3B8" />
                  </TouchableOpacity>
                )}
              </View>
            </View>
            
            <ScrollView 
              style={styles.modalBody}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={true}
            >
              {customers
                .filter(customer => {
                  if (!customerSearchQuery) return true;
                  const query = customerSearchQuery.toLowerCase();
                  return (
                    customer.name?.toLowerCase().includes(query) ||
                    customer.customer_code?.toLowerCase().includes(query) ||
                    customer.company?.toLowerCase().includes(query) ||
                    customer.email?.toLowerCase().includes(query)
                  );
                })
                .map((customer) => (
                <Pressable
                  key={customer.id}
                  style={({ pressed }) => [
                    styles.packingOption,
                    { 
                      paddingVertical: 14, 
                      marginBottom: 8, 
                      backgroundColor: pressed ? '#E5E7EB' : (selectedCustomer?.id === customer.id ? '#FEF2F2' : '#F8FAFC'), 
                      borderRadius: 8,
                      minHeight: 50,
                    }
                  ]}
                  onPress={() => {
                    setSelectedCustomer(customer);
                    setShowCustomerPicker(false);
                    setCustomerSearchQuery('');
                  }}
                >
                  <Ionicons
                    name={selectedCustomer?.id === customer.id ? 'radio-button-on' : 'radio-button-off'}
                    size={20}
                    color={selectedCustomer?.id === customer.id ? '#960018' : '#94A3B8'}
                  />
                  <View style={{ marginLeft: 12, flex: 1 }}>
                    <Text style={{ fontWeight: '600', color: '#333', fontSize: 15 }}>{customer.name}</Text>
                    <Text style={{ fontSize: 12, color: '#64748B' }}>{customer.customer_code} • {customer.company || 'No company'}</Text>
                  </View>
                </Pressable>
              ))}
              {customers.filter(customer => {
                if (!customerSearchQuery) return true;
                const query = customerSearchQuery.toLowerCase();
                return (
                  customer.name?.toLowerCase().includes(query) ||
                  customer.customer_code?.toLowerCase().includes(query) ||
                  customer.company?.toLowerCase().includes(query)
                );
              }).length === 0 && (
                <Text style={{ textAlign: 'center', color: '#64748B', marginTop: 20 }}>
                  {customerSearchQuery ? 'No customers match your search' : 'No customers found'}
                </Text>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  header: {
    backgroundColor: '#0F172A',
    paddingTop: 56,
    paddingBottom: 20,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: -0.3,
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
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '90%',
    minHeight: '50%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 20,
    backgroundColor: '#1a1f36',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
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
  // Pincode validation styles
  pincodeInputContainer: {
    position: 'relative',
    flexDirection: 'row',
    alignItems: 'center',
  },
  pincodeInput: {
    flex: 1,
    paddingRight: 45,
  },
  pincodeStatusIcon: {
    position: 'absolute',
    right: 12,
    top: '50%',
    transform: [{ translateY: -12 }],
  },
  inputError: {
    borderColor: '#DC3545',
    borderWidth: 2,
  },
  inputSuccess: {
    borderColor: '#4CAF50',
    borderWidth: 2,
  },
  errorText: {
    color: '#DC3545',
    fontSize: 12,
    marginTop: 4,
  },
});
