import React from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  ScrollView,
  TextInput,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Quote, QuoteProduct, PACKING_TYPES } from './types';

interface EditQuoteModalProps {
  visible: boolean;
  quote: Quote | null;
  docLabel: string;
  onClose: () => void;
  // Products state
  editedProducts: QuoteProduct[];
  // Discount state
  useItemDiscounts: boolean;
  setUseItemDiscounts: (use: boolean) => void;
  bulkDiscountPercent: string;
  setBulkDiscountPercent: (percent: string) => void;
  editedDiscount: string;
  setEditedDiscount: (discount: string) => void;
  // Freight state
  editedFreight: string;
  setEditedFreight: (freight: string) => void;
  // Packing state
  editedPackingType: string;
  setEditedPackingType: (type: string) => void;
  customPackingPercent: string;
  setCustomPackingPercent: (percent: string) => void;
  // Commercial terms
  commercialTermsOptions: any;
  selectedPaymentTerms: string;
  setSelectedPaymentTerms: (terms: string) => void;
  selectedFreightTerms: string;
  setSelectedFreightTerms: (terms: string) => void;
  selectedColorFinish: string;
  setSelectedColorFinish: (finish: string) => void;
  selectedDeliveryTimeline: string;
  setSelectedDeliveryTimeline: (timeline: string) => void;
  // Callbacks
  onUpdateProductQuantity: (index: number, text: string) => void;
  onUpdateProductItemDiscount: (index: number, text: string) => void;
  onApplyDiscountToAllItems: () => void;
  onSaveAndMail: () => Promise<void>;
  // Calculation function
  calculateEditedTotal: () => {
    subtotal: number;
    discountAmount: number;
    afterDiscount: number;
    packingCharges: number;
    taxableAmount: number;
    total: number;
  };
  // Loading state
  savingEdit: boolean;
}

export const EditQuoteModal: React.FC<EditQuoteModalProps> = ({
  visible,
  quote,
  docLabel,
  onClose,
  editedProducts,
  useItemDiscounts,
  setUseItemDiscounts,
  bulkDiscountPercent,
  setBulkDiscountPercent,
  editedDiscount,
  setEditedDiscount,
  editedFreight,
  setEditedFreight,
  editedPackingType,
  setEditedPackingType,
  customPackingPercent,
  setCustomPackingPercent,
  commercialTermsOptions,
  selectedPaymentTerms,
  setSelectedPaymentTerms,
  selectedFreightTerms,
  setSelectedFreightTerms,
  selectedColorFinish,
  setSelectedColorFinish,
  selectedDeliveryTimeline,
  setSelectedDeliveryTimeline,
  onUpdateProductQuantity,
  onUpdateProductItemDiscount,
  onApplyDiscountToAllItems,
  onSaveAndMail,
  calculateEditedTotal,
  savingEdit,
}) => {
  if (!quote) return null;

  const totals = calculateEditedTotal();

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Edit {docLabel}</Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={28} color="#333" />
            </TouchableOpacity>
          </View>
          
          <ScrollView style={styles.modalScroll}>
            {/* Discount Mode Toggle */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Discount Mode</Text>
              <View style={styles.discountModeToggle}>
                <TouchableOpacity
                  style={[styles.modeButton, !useItemDiscounts && styles.modeButtonActive]}
                  onPress={() => setUseItemDiscounts(false)}
                >
                  <Ionicons name="calculator-outline" size={18} color={!useItemDiscounts ? '#fff' : '#666'} />
                  <Text style={[styles.modeButtonText, !useItemDiscounts && styles.modeButtonTextActive]}>
                    Total Discount
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modeButton, useItemDiscounts && styles.modeButtonActive]}
                  onPress={() => setUseItemDiscounts(true)}
                >
                  <Ionicons name="list-outline" size={18} color={useItemDiscounts ? '#fff' : '#666'} />
                  <Text style={[styles.modeButtonText, useItemDiscounts && styles.modeButtonTextActive]}>
                    Per-Item Discount
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* Bulk Apply Discount - Only visible in Per-Item mode */}
            {useItemDiscounts && (
              <View style={styles.bulkDiscountSection}>
                <Text style={styles.bulkDiscountLabel}>Apply to All Items:</Text>
                <View style={styles.bulkDiscountRow}>
                  <TextInput
                    style={styles.bulkDiscountInput}
                    value={bulkDiscountPercent}
                    onChangeText={setBulkDiscountPercent}
                    keyboardType="numeric"
                    placeholder="0"
                  />
                  <Text style={styles.bulkDiscountPercent}>%</Text>
                  <TouchableOpacity style={styles.bulkApplyButton} onPress={onApplyDiscountToAllItems}>
                    <Ionicons name="copy-outline" size={16} color="#fff" />
                    <Text style={styles.bulkApplyButtonText}>Apply to All</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* Products with editable quantity and item discount */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Products</Text>
              {editedProducts.map((product, index) => {
                const itemDiscount = product.item_discount_percent || 0;
                const valueAfterDiscount = product.unit_price * (1 - itemDiscount / 100);
                const lineTotal = product.quantity * valueAfterDiscount;

                return (
                  <View key={index} style={styles.editProductCard}>
                    <View style={styles.editProductHeader}>
                      <Text style={styles.editProductName}>{product.product_name || product.product_id}</Text>
                      <Text style={styles.editProductPrice}>Rs. {product.unit_price?.toFixed(2)}/unit</Text>
                    </View>

                    <View style={styles.editProductInputs}>
                      <View style={styles.inputGroup}>
                        <Text style={styles.inputLabel}>Qty</Text>
                        <TextInput
                          style={styles.smallInput}
                          value={product.quantity.toString()}
                          onChangeText={(text) => onUpdateProductQuantity(index, text)}
                          keyboardType="numeric"
                        />
                      </View>

                      {useItemDiscounts && (
                        <View style={styles.inputGroup}>
                          <Text style={styles.inputLabel}>Disc %</Text>
                          <TextInput
                            style={styles.smallInput}
                            value={itemDiscount.toString()}
                            onChangeText={(text) => onUpdateProductItemDiscount(index, text)}
                            keyboardType="numeric"
                            placeholder="0"
                          />
                        </View>
                      )}

                      {useItemDiscounts && (
                        <View style={styles.inputGroup}>
                          <Text style={styles.inputLabel}>After Disc</Text>
                          <Text style={styles.calculatedValue}>Rs. {valueAfterDiscount.toFixed(2)}</Text>
                        </View>
                      )}

                      <View style={styles.inputGroup}>
                        <Text style={styles.inputLabel}>Total</Text>
                        <Text style={styles.calculatedValueBold}>Rs. {lineTotal.toFixed(2)}</Text>
                      </View>
                    </View>
                  </View>
                );
              })}
            </View>

            {/* Total Discount - Only visible in Total Discount mode */}
            {!useItemDiscounts && (
              <View style={styles.detailSection}>
                <Text style={styles.sectionTitle}>Discount</Text>
                <View style={styles.freightInputRow}>
                  <Text style={styles.freightInputLabel}>Total Discount:</Text>
                  <View style={styles.freightInputWrapper}>
                    <TextInput
                      style={styles.freightInput}
                      value={editedDiscount}
                      onChangeText={setEditedDiscount}
                      keyboardType="numeric"
                      placeholder="0"
                    />
                    <Text style={styles.discountPercent}>%</Text>
                  </View>
                </View>
              </View>
            )}

            {/* Freight Input */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Freight</Text>
              <View style={styles.freightInputRow}>
                <Text style={styles.freightInputLabel}>Freight Amount:</Text>
                <View style={styles.freightInputWrapper}>
                  <Text style={styles.freightInputPrefix}>Rs.</Text>
                  <TextInput
                    style={styles.freightInput}
                    value={editedFreight}
                    onChangeText={setEditedFreight}
                    keyboardType="numeric"
                    placeholder="0"
                  />
                </View>
              </View>
              {quote.shipping_cost > 0 && parseFloat(editedFreight) !== quote.shipping_cost && (
                <Text style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                  Original freight: Rs. {quote.shipping_cost.toFixed(2)}
                </Text>
              )}
            </View>

            {/* Packing Type Selection */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Packing Type</Text>
              <View style={styles.packingOptions}>
                {PACKING_TYPES.map((option) => (
                  <TouchableOpacity
                    key={option.value}
                    style={[
                      styles.packingOption,
                      editedPackingType === option.value && styles.packingOptionActive,
                    ]}
                    onPress={() => setEditedPackingType(option.value)}
                  >
                    <Ionicons
                      name={editedPackingType === option.value ? 'radio-button-on' : 'radio-button-off'}
                      size={20}
                      color={editedPackingType === option.value ? '#960018' : '#666'}
                    />
                    <Text
                      style={[
                        styles.packingOptionText,
                        editedPackingType === option.value && styles.packingOptionTextActive,
                      ]}
                    >
                      {option.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Custom Packing Percentage Input */}
              {editedPackingType === 'custom' && (
                <View style={styles.customPackingRow}>
                  <Text style={styles.customPackingLabel}>Custom Percentage:</Text>
                  <View style={styles.freightInputWrapper}>
                    <TextInput
                      style={styles.freightInput}
                      value={customPackingPercent}
                      onChangeText={setCustomPackingPercent}
                      keyboardType="numeric"
                      placeholder="0"
                    />
                    <Text style={styles.freightInputSuffix}>%</Text>
                  </View>
                </View>
              )}

              {/* Show original packing type if different */}
              {quote.packing_type && editedPackingType !== quote.packing_type && (
                <Text style={{ color: '#666', fontSize: 12, marginTop: 8 }}>
                  Original:{' '}
                  {quote.packing_type === 'standard'
                    ? 'Standard (1%)'
                    : quote.packing_type === 'pallet'
                    ? 'Pallet (4%)'
                    : quote.packing_type === 'wooden_box'
                    ? 'Wooden Box (8%)'
                    : quote.packing_type}
                </Text>
              )}
            </View>

            {/* Commercial Terms Section */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Commercial Terms</Text>

              {commercialTermsOptions ? (
                <>
                  {/* Payment Terms Dropdown */}
                  <View style={styles.dropdownRow}>
                    <Text style={styles.dropdownLabel}>Payment Terms:</Text>
                    <View style={styles.dropdownContainer}>
                      <select
                        value={selectedPaymentTerms}
                        onChange={(e: any) => setSelectedPaymentTerms(e.target.value)}
                        style={selectStyle}
                      >
                        {commercialTermsOptions.payment_terms?.map((term: string, idx: number) => (
                          <option key={idx} value={term}>
                            {term}
                          </option>
                        ))}
                      </select>
                    </View>
                  </View>

                  {/* Freight Terms Dropdown */}
                  <View style={styles.dropdownRow}>
                    <Text style={styles.dropdownLabel}>Freight Terms:</Text>
                    <View style={styles.dropdownContainer}>
                      <select
                        value={selectedFreightTerms}
                        onChange={(e: any) => setSelectedFreightTerms(e.target.value)}
                        style={selectStyle}
                      >
                        {commercialTermsOptions.freight_terms?.map((term: string, idx: number) => (
                          <option key={idx} value={term}>
                            {term}
                          </option>
                        ))}
                      </select>
                    </View>
                  </View>

                  {/* Color/Finish Dropdown */}
                  <View style={styles.dropdownRow}>
                    <Text style={styles.dropdownLabel}>Color/Finish:</Text>
                    <View style={styles.dropdownContainer}>
                      <select
                        value={selectedColorFinish}
                        onChange={(e: any) => setSelectedColorFinish(e.target.value)}
                        style={selectStyle}
                      >
                        {commercialTermsOptions.color_finish?.map((term: string, idx: number) => (
                          <option key={idx} value={term}>
                            {term}
                          </option>
                        ))}
                      </select>
                    </View>
                  </View>

                  {/* Delivery Timeline Dropdown */}
                  <View style={styles.dropdownRow}>
                    <Text style={styles.dropdownLabel}>Delivery:</Text>
                    <View style={styles.dropdownContainer}>
                      <select
                        value={selectedDeliveryTimeline}
                        onChange={(e: any) => setSelectedDeliveryTimeline(e.target.value)}
                        style={selectStyle}
                      >
                        {commercialTermsOptions.delivery_timeline?.map((term: string, idx: number) => (
                          <option key={idx} value={term}>
                            {term}
                          </option>
                        ))}
                      </select>
                    </View>
                  </View>

                  {/* Fixed Terms */}
                  <View style={[styles.dropdownRow, { marginTop: 16 }]}>
                    <Text style={[styles.dropdownLabel, { fontWeight: '600' }]}>Warranty:</Text>
                    <Text style={styles.fixedTermText}>{commercialTermsOptions.warranty}</Text>
                  </View>
                  <View style={styles.dropdownRow}>
                    <Text style={[styles.dropdownLabel, { fontWeight: '600' }]}>Validity:</Text>
                    <Text style={styles.fixedTermText}>{commercialTermsOptions.validity}</Text>
                  </View>
                </>
              ) : (
                <Text style={{ color: '#999', fontStyle: 'italic' }}>Loading...</Text>
              )}
            </View>

            {/* Calculated Totals */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Summary</Text>

              <View style={styles.pricingRow}>
                <Text style={styles.pricingLabel}>Subtotal</Text>
                <Text style={styles.pricingValue}>
                  Rs. {(totals.subtotal - totals.discountAmount).toFixed(2)}
                </Text>
              </View>

              {totals.packingCharges > 0 && (
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>
                    Packing Charges (
                    {((totals.packingCharges / (totals.subtotal - totals.discountAmount || 1)) * 100).toFixed(1)}%)
                  </Text>
                  <Text style={styles.pricingValue}>Rs. {totals.packingCharges.toFixed(2)}</Text>
                </View>
              )}

              {(parseFloat(editedFreight) || 0) > 0 && (
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>Freight Charges</Text>
                  <Text style={styles.pricingValue}>Rs. {(parseFloat(editedFreight) || 0).toFixed(2)}</Text>
                </View>
              )}

              <View style={styles.pricingRow}>
                <Text style={styles.pricingLabel}>Taxable Amount</Text>
                <Text style={styles.pricingValue}>Rs. {totals.taxableAmount.toFixed(2)}</Text>
              </View>

              <View style={styles.pricingRow}>
                <Text style={styles.pricingLabel}>CGST @ 9%</Text>
                <Text style={styles.pricingValue}>Rs. {(totals.taxableAmount * 0.09).toFixed(2)}</Text>
              </View>

              <View style={styles.pricingRow}>
                <Text style={styles.pricingLabel}>SGST @ 9%</Text>
                <Text style={styles.pricingValue}>Rs. {(totals.taxableAmount * 0.09).toFixed(2)}</Text>
              </View>

              <View style={[styles.pricingRow, styles.totalRow]}>
                <Text style={styles.totalLabel}>GRAND TOTAL</Text>
                <Text style={styles.totalValue}>Rs. {totals.total.toFixed(2)}</Text>
              </View>
            </View>

            {/* Single Save & Mail Button */}
            <TouchableOpacity
              style={styles.saveAndMailButton}
              onPress={onSaveAndMail}
              disabled={savingEdit}
            >
              {savingEdit ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="mail" size={24} color="#fff" />
                  <Text style={styles.saveEditButtonText}>Save & Mail Revision</Text>
                </>
              )}
            </TouchableOpacity>

            {/* Show current revision if exists */}
            {quote.current_revision && (
              <Text style={styles.revisionLabel}>Current Revision: {quote.current_revision}</Text>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

// Select dropdown style for web
const selectStyle = {
  width: '100%',
  padding: 12,
  fontSize: 14,
  borderRadius: 8,
  border: '1px solid #ddd',
  backgroundColor: '#fff',
  cursor: 'pointer',
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    flex: 1,
    backgroundColor: '#fff',
    marginTop: 50,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
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
  modalScroll: {
    flex: 1,
    padding: 16,
  },
  detailSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  discountModeToggle: {
    flexDirection: 'row',
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    padding: 4,
    gap: 4,
  },
  modeButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    gap: 6,
  },
  modeButtonActive: {
    backgroundColor: '#960018',
  },
  modeButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  modeButtonTextActive: {
    color: '#fff',
  },
  bulkDiscountSection: {
    backgroundColor: '#FFF5F5',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#960018',
  },
  bulkDiscountLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#960018',
    marginBottom: 8,
  },
  bulkDiscountRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  bulkDiscountInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    width: 70,
    textAlign: 'center',
  },
  bulkDiscountPercent: {
    fontSize: 16,
    fontWeight: '600',
    color: '#960018',
  },
  bulkApplyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#960018',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
    marginLeft: 'auto',
  },
  bulkApplyButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#fff',
  },
  editProductCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  editProductHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  editProductName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  editProductPrice: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  editProductInputs: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  inputGroup: {
    flex: 1,
    minWidth: 70,
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#64748B',
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  smallInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
    textAlign: 'center',
  },
  calculatedValue: {
    fontSize: 13,
    fontWeight: '500',
    color: '#475569',
    paddingVertical: 8,
  },
  calculatedValueBold: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
    paddingVertical: 8,
  },
  freightInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 12,
  },
  freightInputLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  freightInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  freightInputPrefix: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
    marginRight: 4,
  },
  freightInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    width: 100,
    textAlign: 'center',
  },
  freightInputSuffix: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  discountPercent: {
    fontSize: 16,
    fontWeight: '600',
    color: '#960018',
    marginLeft: 4,
  },
  packingOptions: {
    gap: 8,
  },
  packingOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    gap: 10,
  },
  packingOptionActive: {
    backgroundColor: '#fff5f5',
    borderColor: '#960018',
  },
  packingOptionText: {
    fontSize: 14,
    color: '#666',
  },
  packingOptionTextActive: {
    color: '#960018',
    fontWeight: '600',
  },
  customPackingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  customPackingLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  dropdownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  dropdownLabel: {
    fontSize: 14,
    color: '#333',
    width: 120,
  },
  dropdownContainer: {
    flex: 1,
  },
  fixedTermText: {
    fontSize: 14,
    color: '#666',
    flex: 1,
  },
  pricingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  pricingLabel: {
    fontSize: 14,
    color: '#666',
  },
  pricingValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    marginTop: 8,
    paddingTop: 12,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  totalValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  saveAndMailButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 16,
    marginBottom: 20,
    gap: 8,
  },
  saveEditButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  revisionLabel: {
    textAlign: 'center',
    fontSize: 12,
    color: '#666',
    marginBottom: 20,
  },
});

export default EditQuoteModal;
