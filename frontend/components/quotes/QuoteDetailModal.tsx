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

interface QuoteDetailModalProps {
  visible: boolean;
  quote: Quote | null;
  isAdmin: boolean;
  isCustomer: boolean;
  docLabel: string;
  onClose: () => void;
  // Editable state (for admin editing pending RFQs)
  editableProducts: QuoteProduct[];
  useItemDiscount: boolean;
  setUseItemDiscount: (use: boolean) => void;
  totalDiscountPercent: string;
  setTotalDiscountPercent: (percent: string) => void;
  itemDiscounts: { [key: number]: string };
  setItemDiscounts: (discounts: { [key: number]: string }) => void;
  editPackingType: string;
  setEditPackingType: (type: string) => void;
  customPackingPercent: string;
  setCustomPackingPercent: (percent: string) => void;
  editDeliveryPincode: string;
  customFreightAmount: string;
  setCustomFreightAmount: (amount: string) => void;
  pincodeValid: boolean;
  pincodeError: string;
  freightLoading: boolean;
  // Commercial Terms (for admin approving RFQs)
  commercialTermsOptions: any;
  selectedPaymentTerms: string;
  setSelectedPaymentTerms: (terms: string) => void;
  selectedFreightTerms: string;
  setSelectedFreightTerms: (terms: string) => void;
  selectedColorFinish: string;
  setSelectedColorFinish: (finish: string) => void;
  selectedDeliveryTimeline: string;
  setSelectedDeliveryTimeline: (timeline: string) => void;
  // Actions
  onPincodeChange: (pincode: string) => void;
  onUpdateProductQuantity: (index: number, qty: number) => void;
  onDeleteProduct: (index: number) => void;
  onApprove: (quote: Quote) => void;
  onReject: (quote: Quote) => void;
  onEdit: (quote: Quote) => void;
  onViewHistory: (quoteId: string) => void;
  onExportPdf: () => void;
  onDownloadAttachment: (quoteId: string, productIdx: number, attachmentIdx: number, filename: string) => void;
  onDownloadAllAsZip: (quoteId: string, quoteNumber: string) => void;
  // Loading states
  approvingId: string | null;
  generatingPdf: boolean;
  loadingHistory: boolean;
  // Helper functions
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => string;
  formatDate: (date: string) => string;
  calculateTotalDiscount: () => number;
  calculateApprovalTotal: () => {
    subtotal: number;
    discountAmount: number;
    afterDiscount: number;
    packingCharges: number;
    freightAmount: number;
    taxableAmount: number;
    total: number;
  };
}

export const QuoteDetailModal: React.FC<QuoteDetailModalProps> = ({
  visible,
  quote,
  isAdmin,
  isCustomer,
  docLabel,
  onClose,
  editableProducts,
  useItemDiscount,
  setUseItemDiscount,
  totalDiscountPercent,
  setTotalDiscountPercent,
  itemDiscounts,
  setItemDiscounts,
  editPackingType,
  setEditPackingType,
  customPackingPercent,
  setCustomPackingPercent,
  editDeliveryPincode,
  customFreightAmount,
  setCustomFreightAmount,
  pincodeValid,
  pincodeError,
  freightLoading,
  commercialTermsOptions,
  selectedPaymentTerms,
  setSelectedPaymentTerms,
  selectedFreightTerms,
  setSelectedFreightTerms,
  selectedColorFinish,
  setSelectedColorFinish,
  selectedDeliveryTimeline,
  setSelectedDeliveryTimeline,
  onPincodeChange,
  onUpdateProductQuantity,
  onDeleteProduct,
  onApprove,
  onReject,
  onEdit,
  onViewHistory,
  onExportPdf,
  onDownloadAttachment,
  onDownloadAllAsZip,
  approvingId,
  generatingPdf,
  loadingHistory,
  getStatusColor,
  getStatusIcon,
  formatDate,
  calculateTotalDiscount,
  calculateApprovalTotal,
}) => {
  if (!quote) return null;

  const isRfq = quote.quote_number?.startsWith('RFQ');
  const isPending = quote.status?.toLowerCase() === 'pending';
  const isApproved = quote.status?.toLowerCase() === 'approved';
  const isRejected = quote.status?.toLowerCase() === 'rejected';
  const canEdit = isAdmin && isRfq && !isApproved && !isRejected;

  // Debug logging
  console.log('QuoteDetailModal Debug:', {
    canEdit,
    isAdmin,
    isRfq,
    isPending,
    isApproved,
    isRejected,
    hasCommercialTermsOptions: !!commercialTermsOptions,
    commercialTermsOptionsKeys: commercialTermsOptions ? Object.keys(commercialTermsOptions) : []
  });

  const renderProductPrice = (product: QuoteProduct, index: number) => {
    const originalPrice = product.unit_price * product.quantity;
    const discountPct = canEdit
      ? useItemDiscount
        ? parseFloat(itemDiscounts[index] || '0') || 0
        : parseFloat(totalDiscountPercent) || 0
      : product.item_discount_percent || 0;
    const discountedPrice = originalPrice * (1 - discountPct / 100);

    if (discountPct > 0) {
      return (
        <View style={{ alignItems: 'flex-end' }}>
          <Text style={[styles.productPrice, { textDecorationLine: 'line-through', color: '#999', fontSize: 12 }]}>
            Rs. {originalPrice.toFixed(2)}
          </Text>
          <Text style={styles.productPrice}>Rs. {discountedPrice.toFixed(2)}</Text>
          <Text style={{ fontSize: 10, color: '#059669' }}>({discountPct}% off)</Text>
        </View>
      );
    }
    return <Text style={styles.productPrice}>Rs. {originalPrice.toFixed(2)}</Text>;
  };

  const renderEditableProduct = (product: QuoteProduct, index: number) => (
    <View key={index} style={styles.editableProductCard}>
      <View style={styles.editableProductHeader}>
        <Text style={styles.productName}>{product.product_name || product.product_id}</Text>
        <TouchableOpacity
          style={styles.deleteProductButton}
          onPress={() => onDeleteProduct(index)}
        >
          <Ionicons name="trash-outline" size={20} color="#DC3545" />
        </TouchableOpacity>
      </View>
      <View style={styles.editableProductRow}>
        <View style={styles.qtyEditContainer}>
          <Text style={styles.qtyLabel}>Qty:</Text>
          <TouchableOpacity
            style={styles.qtyButton}
            onPress={() => onUpdateProductQuantity(index, product.quantity - 1)}
          >
            <Ionicons name="remove" size={18} color="#333" />
          </TouchableOpacity>
          <TextInput
            style={styles.qtyInput}
            value={product.quantity.toString()}
            onChangeText={(text) => onUpdateProductQuantity(index, parseInt(text) || 1)}
            keyboardType="numeric"
          />
          <TouchableOpacity
            style={styles.qtyButton}
            onPress={() => onUpdateProductQuantity(index, product.quantity + 1)}
          >
            <Ionicons name="add" size={18} color="#333" />
          </TouchableOpacity>
        </View>
        {renderProductPrice(product, index)}
      </View>
      {product.specifications && (
        <View style={styles.specsContainer}>
          {product.specifications.pipe_diameter && (
            <Text style={styles.specText}>Pipe: {product.specifications.pipe_diameter}mm</Text>
          )}
          {product.specifications.shaft_diameter && (
            <Text style={styles.specText}>Shaft: {product.specifications.shaft_diameter}mm</Text>
          )}
          {product.specifications.bearing && (
            <Text style={styles.specText}>Bearing: {product.specifications.bearing}</Text>
          )}
        </View>
      )}
      {product.remark && (
        <View style={styles.remarkContainer}>
          <Ionicons name="chatbubble-outline" size={14} color="#64748B" />
          <Text style={styles.remarkText}>{product.remark}</Text>
        </View>
      )}
    </View>
  );

  const renderReadOnlyProduct = (product: QuoteProduct, index: number) => (
    <View key={index} style={styles.productCard}>
      <Text style={styles.productName}>{product.product_name || product.product_id}</Text>
      <View style={styles.productDetails}>
        <Text style={styles.productQty}>Qty: {product.quantity}</Text>
        {(!isCustomer || isApproved) && renderProductPrice(product, index)}
      </View>
      {product.specifications && (
        <View style={styles.specsContainer}>
          {product.specifications.pipe_diameter && (
            <Text style={styles.specText}>Pipe: {product.specifications.pipe_diameter}mm</Text>
          )}
          {product.specifications.shaft_diameter && (
            <Text style={styles.specText}>Shaft: {product.specifications.shaft_diameter}mm</Text>
          )}
          {product.specifications.bearing && (
            <Text style={styles.specText}>Bearing: {product.specifications.bearing}</Text>
          )}
        </View>
      )}
      {product.remark && (
        <View style={styles.remarkContainer}>
          <Ionicons name="chatbubble-outline" size={14} color="#64748B" />
          <Text style={styles.remarkText}>{product.remark}</Text>
        </View>
      )}
    </View>
  );

  const getPackingLabel = (packingType: string | undefined) => {
    if (packingType === 'standard') return 'Standard 1';
    if (packingType === 'pallet') return 'Pallet 4';
    if (packingType === 'wooden_box') return 'Wooden Box 8';
    if (packingType?.startsWith('custom_')) return `Custom ${packingType.split('_')[1]}`;
    return 'Standard 1';
  };

  const totals = calculateApprovalTotal();

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
            <View>
              <Text style={styles.modalTitle}>
                {quote.quote_number || `${docLabel} #${quote.id.slice(-6).toUpperCase()}`}
              </Text>
              {quote.original_rfq_number && (
                <Text style={styles.rfqReference}>Ref: {quote.original_rfq_number}</Text>
              )}
            </View>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={28} color="#fff" />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalScroll}>
            {/* Status */}
            <View style={styles.detailSection}>
              <View style={[styles.statusBadgeLarge, { backgroundColor: `${getStatusColor(quote.status)}20` }]}>
                <Ionicons name={getStatusIcon(quote.status) as any} size={20} color={getStatusColor(quote.status)} />
                <Text style={[styles.statusTextLarge, { color: getStatusColor(quote.status) }]}>
                  {quote.status?.toUpperCase()}
                </Text>
              </View>
            </View>

            {/* Products */}
            <View style={styles.detailSection}>
              <Text style={styles.sectionTitle}>Products</Text>
              {canEdit
                ? editableProducts.map(renderEditableProduct)
                : quote.products.map(renderReadOnlyProduct)}
            </View>

            {/* Pricing Summary - Hide for customers viewing pending/non-approved quotes AND for admin viewing pending RFQs */}
            {!canEdit && !(isCustomer && !isApproved) && (
              <View style={styles.detailSection}>
                <Text style={styles.sectionTitle}>Pricing Summary</Text>
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>Subtotal</Text>
                  <Text style={styles.pricingValue}>
                    Rs. {((quote.subtotal || 0) - (quote.total_discount || 0)).toFixed(2)}
                  </Text>
                </View>
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>Packing ({getPackingLabel(quote.packing_type)}%)</Text>
                  <Text style={styles.pricingValue}>Rs. {(quote.packing_charges || 0).toFixed(2)}</Text>
                </View>
                {(quote.shipping_cost || 0) > 0 && (
                  <View style={styles.pricingRow}>
                    <Text style={styles.pricingLabel}>Freight Charges</Text>
                    <Text style={styles.pricingValue}>Rs. {(quote.shipping_cost || 0).toFixed(2)}</Text>
                  </View>
                )}
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>Taxable Amount</Text>
                  <Text style={styles.pricingValue}>
                    Rs. {((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0) + (quote.shipping_cost || 0)).toFixed(2)}
                  </Text>
                </View>
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>CGST @ 9%</Text>
                  <Text style={styles.pricingValue}>
                    Rs. {(((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0) + (quote.shipping_cost || 0)) * 0.09).toFixed(2)}
                  </Text>
                </View>
                <View style={styles.pricingRow}>
                  <Text style={styles.pricingLabel}>SGST @ 9%</Text>
                  <Text style={styles.pricingValue}>
                    Rs. {(((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0) + (quote.shipping_cost || 0)) * 0.09).toFixed(2)}
                  </Text>
                </View>
                <View style={[styles.pricingRow, styles.totalRow]}>
                  <Text style={styles.totalLabel}>GRAND TOTAL</Text>
                  <Text style={styles.totalValue}>
                    Rs. {(((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0) + (quote.shipping_cost || 0)) * 1.18).toFixed(2)}
                  </Text>
                </View>
              </View>
            )}

            {/* Show message for customers on non-approved quotes */}
            {isCustomer && !isApproved && (
              <View style={styles.detailSection}>
                <View style={styles.pendingPriceMessage}>
                  <Ionicons name="time-outline" size={24} color="#F59E0B" />
                  <Text style={styles.pendingPriceText}>
                    {isPending
                      ? 'Pricing will be available once your RFQ is approved by admin'
                      : isRejected
                      ? 'This quote was rejected. Please contact us for more information.'
                      : 'Pricing details are being processed'}
                  </Text>
                </View>
              </View>
            )}

            {/* Delivery */}
            {quote.delivery_location && (
              <View style={styles.detailSection}>
                <Text style={styles.sectionTitle}>Delivery</Text>
                <Text style={styles.deliveryText}>Pincode: {quote.delivery_location}</Text>
              </View>
            )}

            {/* Discount Section - Editable for Admin on Pending RFQs */}
            {canEdit && (
              <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
                <Text style={styles.sectionTitle}>Discount</Text>
                <View style={styles.discountModeToggle}>
                  <TouchableOpacity
                    style={[styles.modeButton, !useItemDiscount && styles.modeButtonActive]}
                    onPress={() => setUseItemDiscount(false)}
                  >
                    <Ionicons name="calculator-outline" size={18} color={!useItemDiscount ? '#fff' : '#666'} />
                    <Text style={[styles.modeButtonText, !useItemDiscount && styles.modeButtonTextActive]}>
                      Total Discount
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.modeButton, useItemDiscount && styles.modeButtonActive]}
                    onPress={() => setUseItemDiscount(true)}
                  >
                    <Ionicons name="list-outline" size={18} color={useItemDiscount ? '#fff' : '#666'} />
                    <Text style={[styles.modeButtonText, useItemDiscount && styles.modeButtonTextActive]}>
                      Item-wise
                    </Text>
                  </TouchableOpacity>
                </View>

                {!useItemDiscount ? (
                  <View style={styles.freightInputRow}>
                    <Text style={styles.freightInputLabel}>Discount on Total:</Text>
                    <View style={styles.freightInputWrapper}>
                      <TextInput
                        style={styles.freightInput}
                        value={totalDiscountPercent}
                        onChangeText={setTotalDiscountPercent}
                        keyboardType="numeric"
                        placeholder="0"
                      />
                      <Text style={styles.freightInputSuffix}>%</Text>
                    </View>
                  </View>
                ) : (
                  <View style={styles.itemDiscountContainer}>
                    {editableProducts.map((product, index) => (
                      <View key={index} style={styles.itemDiscountRow}>
                        <Text style={styles.itemDiscountName} numberOfLines={1}>
                          {product.product_name || product.product_id}
                        </Text>
                        <View style={styles.freightInputWrapper}>
                          <TextInput
                            style={[styles.freightInput, { width: 60 }]}
                            value={itemDiscounts[index] || '0'}
                            onChangeText={(text) => {
                              setItemDiscounts({ ...itemDiscounts, [index]: text });
                            }}
                            keyboardType="numeric"
                            placeholder="0"
                          />
                          <Text style={styles.freightInputSuffix}>%</Text>
                        </View>
                      </View>
                    ))}
                  </View>
                )}

                <View style={styles.calculatedFreightRow}>
                  <Text style={styles.calculatedFreightLabel}>Total Discount Amount:</Text>
                  <Text style={[styles.calculatedFreightValue, { color: '#4CAF50' }]}>
                    - Rs. {calculateTotalDiscount().toFixed(2)}
                  </Text>
                </View>
              </View>
            )}

            {/* Packing & Freight Details - Editable for Admin on Pending RFQs */}
            {canEdit && (
              <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
                <Text style={styles.sectionTitle}>Packing & Freight (Editable)</Text>

                <Text style={styles.fieldLabel}>Packing Type</Text>
                <View style={styles.packingOptions}>
                  {PACKING_TYPES.map((option) => (
                    <TouchableOpacity
                      key={option.value}
                      style={[
                        styles.packingOption,
                        editPackingType === option.value && styles.packingOptionActive,
                      ]}
                      onPress={() => setEditPackingType(option.value)}
                    >
                      <Ionicons
                        name={editPackingType === option.value ? 'radio-button-on' : 'radio-button-off'}
                        size={20}
                        color={editPackingType === option.value ? '#960018' : '#666'}
                      />
                      <Text
                        style={[
                          styles.packingOptionText,
                          editPackingType === option.value && styles.packingOptionTextActive,
                        ]}
                      >
                        {option.label}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {editPackingType === 'custom' && (
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

                <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Delivery Pincode</Text>
                <TextInput
                  style={[styles.editableInput, !pincodeValid && styles.inputError]}
                  value={editDeliveryPincode}
                  onChangeText={onPincodeChange}
                  keyboardType="numeric"
                  placeholder="Enter delivery pincode"
                  maxLength={6}
                />
                {pincodeError && <Text style={styles.errorText}>{pincodeError}</Text>}

                <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Custom Freight Amount (Rs.)</Text>
                <TextInput
                  style={styles.editableInput}
                  value={customFreightAmount}
                  onChangeText={setCustomFreightAmount}
                  keyboardType="numeric"
                  placeholder="Enter custom freight amount"
                />
                {freightLoading && (
                  <View style={styles.freightLoadingRow}>
                    <ActivityIndicator size="small" color="#960018" />
                    <Text style={styles.freightLoadingText}>Calculating freight...</Text>
                  </View>
                )}

                {/* Commercial Terms Selection - For pending RFQs */}
                <View style={{ backgroundColor: '#E0F7FA', marginTop: 20, padding: 16, borderRadius: 12, borderWidth: 2, borderColor: '#00BCD4' }}>
                  <Text style={{ fontSize: 18, fontWeight: '700', color: '#006064', marginBottom: 12 }}>Commercial Terms</Text>
                  
                  {commercialTermsOptions ? (
                    <>
                      {/* Payment Terms */}
                      <View style={styles.termRow}>
                        <Text style={styles.termLabel}>Payment Terms:</Text>
                        <View style={styles.termPickerContainer}>
                          {commercialTermsOptions.payment_terms?.map((term: string, idx: number) => (
                            <TouchableOpacity
                              key={idx}
                              style={[
                                styles.termOption,
                                selectedPaymentTerms === term && styles.termOptionSelected
                              ]}
                              onPress={() => setSelectedPaymentTerms(term)}
                            >
                              <Ionicons
                                name={selectedPaymentTerms === term ? 'radio-button-on' : 'radio-button-off'}
                                size={18}
                                color={selectedPaymentTerms === term ? '#960018' : '#666'}
                              />
                              <Text style={[
                                styles.termOptionText,
                                selectedPaymentTerms === term && styles.termOptionTextSelected
                              ]}>{term}</Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>

                      {/* Freight Terms */}
                      <View style={styles.termRow}>
                        <Text style={styles.termLabel}>Freight Terms:</Text>
                        <View style={styles.termPickerContainer}>
                          {commercialTermsOptions.freight_terms?.map((term: string, idx: number) => (
                            <TouchableOpacity
                              key={idx}
                              style={[
                                styles.termOption,
                                selectedFreightTerms === term && styles.termOptionSelected
                              ]}
                              onPress={() => setSelectedFreightTerms(term)}
                            >
                              <Ionicons
                                name={selectedFreightTerms === term ? 'radio-button-on' : 'radio-button-off'}
                                size={18}
                                color={selectedFreightTerms === term ? '#960018' : '#666'}
                              />
                              <Text style={[
                                styles.termOptionText,
                                selectedFreightTerms === term && styles.termOptionTextSelected
                              ]}>{term}</Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>

                      {/* Color/Finish */}
                      <View style={styles.termRow}>
                        <Text style={styles.termLabel}>Color/Finish:</Text>
                        <View style={styles.termPickerContainer}>
                          {commercialTermsOptions.color_finish?.map((term: string, idx: number) => (
                            <TouchableOpacity
                              key={idx}
                              style={[
                                styles.termOption,
                                selectedColorFinish === term && styles.termOptionSelected
                              ]}
                              onPress={() => setSelectedColorFinish(term)}
                            >
                              <Ionicons
                                name={selectedColorFinish === term ? 'radio-button-on' : 'radio-button-off'}
                                size={18}
                                color={selectedColorFinish === term ? '#960018' : '#666'}
                              />
                              <Text style={[
                                styles.termOptionText,
                                selectedColorFinish === term && styles.termOptionTextSelected
                              ]}>{term}</Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>

                      {/* Delivery Timeline */}
                      <View style={styles.termRow}>
                        <Text style={styles.termLabel}>Delivery:</Text>
                        <View style={styles.termPickerContainer}>
                          {commercialTermsOptions.delivery_timeline?.map((term: string, idx: number) => (
                            <TouchableOpacity
                              key={idx}
                              style={[
                                styles.termOption,
                                selectedDeliveryTimeline === term && styles.termOptionSelected
                              ]}
                              onPress={() => setSelectedDeliveryTimeline(term)}
                            >
                              <Ionicons
                                name={selectedDeliveryTimeline === term ? 'radio-button-on' : 'radio-button-off'}
                                size={18}
                                color={selectedDeliveryTimeline === term ? '#960018' : '#666'}
                              />
                              <Text style={[
                                styles.termOptionText,
                                selectedDeliveryTimeline === term && styles.termOptionTextSelected
                              ]}>{term}</Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      </View>

                      {/* Fixed Terms */}
                      <View style={[styles.termRow, { marginTop: 16, backgroundColor: '#F8FAFC', borderRadius: 8, padding: 12 }]}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                          <Text style={{ fontWeight: '600', color: '#333' }}>Warranty:</Text>
                          <Text style={{ color: '#666' }}>{commercialTermsOptions.warranty}</Text>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                          <Text style={{ fontWeight: '600', color: '#333' }}>Validity:</Text>
                          <Text style={{ color: '#666' }}>{commercialTermsOptions.validity}</Text>
                        </View>
                      </View>
                    </>
                  ) : (
                    <Text style={{ color: '#666', fontStyle: 'italic' }}>Loading commercial terms...</Text>
                  )}
                </View>

                {/* Live Calculation Preview */}
                <View style={[styles.detailSection, { marginTop: 20, backgroundColor: '#F8FAFC', padding: 12, borderRadius: 12 }]}>
                  <Text style={[styles.sectionTitle, { marginBottom: 8 }]}>Live Calculation Preview</Text>
                  <View style={styles.pricingRow}>
                    <Text style={styles.pricingLabel}>Subtotal (after discount)</Text>
                    <Text style={styles.pricingValue}>Rs. {totals.afterDiscount.toFixed(2)}</Text>
                  </View>
                  <View style={styles.pricingRow}>
                    <Text style={styles.pricingLabel}>Packing Charges</Text>
                    <Text style={styles.pricingValue}>Rs. {totals.packingCharges.toFixed(2)}</Text>
                  </View>
                  <View style={styles.pricingRow}>
                    <Text style={styles.pricingLabel}>Freight Charges</Text>
                    <Text style={styles.pricingValue}>Rs. {totals.freightAmount.toFixed(2)}</Text>
                  </View>
                  <View style={styles.pricingRow}>
                    <Text style={styles.pricingLabel}>Taxable Amount</Text>
                    <Text style={styles.pricingValue}>Rs. {totals.taxableAmount.toFixed(2)}</Text>
                  </View>
                  <View style={[styles.pricingRow, styles.totalRow]}>
                    <Text style={styles.totalLabel}>GRAND TOTAL (incl. GST)</Text>
                    <Text style={styles.totalValue}>Rs. {totals.total.toFixed(2)}</Text>
                  </View>
                </View>
              </View>
            )}

            {/* Commercial Terms - For approved quotes */}
            {isApproved && quote.commercial_terms && (
              <View style={styles.detailSection}>
                <Text style={styles.sectionTitle}>Commercial Terms</Text>
                {quote.commercial_terms.payment_terms && (
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Payment Terms</Text>
                    <Text style={styles.infoValue}>{quote.commercial_terms.payment_terms}</Text>
                  </View>
                )}
                {quote.commercial_terms.freight_terms && (
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Freight Terms</Text>
                    <Text style={styles.infoValue}>{quote.commercial_terms.freight_terms}</Text>
                  </View>
                )}
                {quote.commercial_terms.color_finish && (
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Color/Finish</Text>
                    <Text style={styles.infoValue}>{quote.commercial_terms.color_finish}</Text>
                  </View>
                )}
                {quote.commercial_terms.delivery_timeline && (
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Delivery Timeline</Text>
                    <Text style={styles.infoValue}>{quote.commercial_terms.delivery_timeline}</Text>
                  </View>
                )}
              </View>
            )}

            {/* Customer Reference */}
            {quote.customer_rfq_no && (
              <View style={styles.detailSection}>
                <Text style={styles.sectionTitle}>Customer Reference</Text>
                <Text style={styles.deliveryText}>{quote.customer_rfq_no}</Text>
              </View>
            )}

            {/* Notes */}
            {quote.notes && (
              <View style={styles.detailSection}>
                <Text style={styles.sectionTitle}>Notes</Text>
                <Text style={styles.notesText}>{quote.notes}</Text>
              </View>
            )}

            {/* Date */}
            <View style={styles.detailSection}>
              <Text style={styles.dateText}>
                {isApproved && (quote.approved_at_ist || quote.approved_at)
                  ? `Approved: ${quote.approved_at_ist || formatDate(quote.approved_at || '')}`
                  : `Created: ${quote.created_at_ist || formatDate(quote.created_at)}`}
              </Text>
            </View>

            {/* Action Buttons Row */}
            <View style={styles.detailActionsRow}>
              {canEdit && (
                <>
                  <TouchableOpacity
                    style={styles.approveConfirmButton}
                    onPress={() => onApprove(quote)}
                    disabled={approvingId === quote.id}
                  >
                    {approvingId === quote.id ? (
                      <ActivityIndicator color="#22C55E" />
                    ) : (
                      <>
                        <Ionicons name="checkmark-circle" size={28} color="#22C55E" />
                        <Text style={styles.approveConfirmButtonText}>Approve</Text>
                      </>
                    )}
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.rejectButton}
                    onPress={() => {
                      onClose();
                      onReject(quote);
                    }}
                  >
                    <Ionicons name="close-circle" size={28} color="#EF4444" />
                    <Text style={styles.rejectButtonText}>Reject</Text>
                  </TouchableOpacity>
                </>
              )}

              {isAdmin && isApproved && (
                <TouchableOpacity
                  style={styles.editQuoteButton}
                  onPress={() => {
                    onClose();
                    onEdit(quote);
                  }}
                >
                  <Ionicons name="create-outline" size={28} color="#4CAF50" />
                  <Text style={styles.editQuoteButtonText}>Edit</Text>
                </TouchableOpacity>
              )}

              {isApproved && (
                <TouchableOpacity
                  style={styles.historyButton}
                  onPress={() => onViewHistory(quote.id)}
                  disabled={loadingHistory}
                >
                  {loadingHistory ? (
                    <ActivityIndicator color="#64748B" size="small" />
                  ) : (
                    <>
                      <Ionicons name="time-outline" size={28} color="#64748B" />
                      <Text style={styles.historyButtonText}>History</Text>
                    </>
                  )}
                </TouchableOpacity>
              )}

              <TouchableOpacity
                style={[styles.exportButton, !canEdit && !isApproved ? { flex: 1 } : {}]}
                onPress={onExportPdf}
                disabled={generatingPdf}
              >
                {generatingPdf ? (
                  <ActivityIndicator color="#960018" />
                ) : (
                  <>
                    <Ionicons name="download-outline" size={28} color="#960018" />
                    <Text style={styles.exportButtonText}>Export PDF</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>

            {/* Attachments Section - Admin Only */}
            {!isCustomer && quote.products?.some((p: any) => p.attachments?.length > 0) && (
              <View style={styles.attachmentsSection}>
                <Text style={styles.attachmentsSectionTitle}>
                  <Ionicons name="attach" size={18} color="#1E293B" /> Attachments
                </Text>

                {quote.products.map((product: any, pIdx: number) =>
                  product.attachments?.length > 0 ? (
                    <View key={pIdx} style={styles.productAttachments}>
                      <Text style={styles.productAttachmentLabel}>
                        {product.product_name || `Product ${pIdx + 1}`}
                      </Text>
                      {product.attachments.map((att: any, aIdx: number) => (
                        <TouchableOpacity
                          key={aIdx}
                          style={styles.attachmentDownloadBtn}
                          onPress={() =>
                            onDownloadAttachment(quote.id, pIdx, aIdx, att.name || `attachment_${aIdx}`)
                          }
                        >
                          <Ionicons
                            name={att.type === 'image' ? 'image' : 'document'}
                            size={16}
                            color="#960018"
                          />
                          <Text style={styles.attachmentDownloadText} numberOfLines={1}>
                            {att.name || `Attachment ${aIdx + 1}`}
                          </Text>
                          <Ionicons name="download" size={16} color="#960018" />
                        </TouchableOpacity>
                      ))}
                    </View>
                  ) : null
                )}

                {quote.products.reduce((sum: number, p: any) => sum + (p.attachments?.length || 0), 0) > 1 && (
                  <TouchableOpacity
                    style={styles.downloadAllZipBtn}
                    onPress={() => onDownloadAllAsZip(quote.id, quote.quote_number || quote.id)}
                  >
                    <Ionicons name="archive" size={20} color="#fff" />
                    <Text style={styles.downloadAllZipText}>Download All as ZIP</Text>
                  </TouchableOpacity>
                )}
              </View>
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
    backgroundColor: '#1a1f36',
    padding: 20,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  rfqReference: {
    fontSize: 12,
    color: '#0066cc',
    marginTop: 2,
    fontWeight: '500',
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
  statusBadgeLarge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 8,
  },
  statusTextLarge: {
    fontSize: 14,
    fontWeight: '700',
  },
  productCard: {
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  editableProductCard: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#960018',
  },
  editableProductHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  editableProductRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  deleteProductButton: {
    padding: 4,
  },
  productName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
  },
  productDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  productQty: {
    fontSize: 14,
    color: '#666',
  },
  productPrice: {
    fontSize: 15,
    fontWeight: '600',
    color: '#960018',
  },
  specsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
    gap: 8,
  },
  specText: {
    fontSize: 12,
    color: '#666',
    backgroundColor: '#E0E0E0',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  remarkContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 10,
    padding: 10,
    backgroundColor: '#FEF3C7',
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#F59E0B',
  },
  remarkText: {
    flex: 1,
    fontSize: 13,
    color: '#92400E',
    lineHeight: 18,
  },
  qtyEditContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  qtyLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  qtyButton: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#e0e0e0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  qtyInput: {
    width: 50,
    height: 32,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    textAlign: 'center',
    fontSize: 14,
    backgroundColor: '#fff',
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
  pendingPriceMessage: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    padding: 16,
    borderRadius: 12,
    gap: 12,
  },
  pendingPriceText: {
    flex: 1,
    fontSize: 14,
    color: '#92400E',
    lineHeight: 20,
  },
  deliveryText: {
    fontSize: 14,
    color: '#333',
  },
  discountModeToggle: {
    flexDirection: 'row',
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    padding: 4,
    gap: 4,
    marginBottom: 16,
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
  itemDiscountContainer: {
    gap: 8,
  },
  itemDiscountRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  itemDiscountName: {
    flex: 1,
    fontSize: 14,
    color: '#333',
    marginRight: 12,
  },
  calculatedFreightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F1F5F9',
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
  },
  calculatedFreightLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  calculatedFreightValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
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
  editableInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: '#0F172A',
  },
  inputError: {
    borderColor: '#DC3545',
  },
  errorText: {
    fontSize: 12,
    color: '#DC3545',
    marginTop: 4,
  },
  freightLoadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
  },
  freightLoadingText: {
    fontSize: 14,
    color: '#666',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  infoLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
    flex: 1,
    textAlign: 'right',
    marginLeft: 16,
  },
  notesText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
  dateText: {
    fontSize: 12,
    color: '#666',
  },
  detailActionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 20,
    marginBottom: 30,
  },
  approveConfirmButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E8F5E9',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
    minWidth: 120,
  },
  approveConfirmButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#22C55E',
  },
  rejectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFEBEE',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
    minWidth: 120,
  },
  rejectButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#EF4444',
  },
  editQuoteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E8F5E9',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
    minWidth: 100,
  },
  editQuoteButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4CAF50',
  },
  historyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F1F5F9',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
    minWidth: 100,
  },
  historyButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748B',
  },
  exportButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF5F5',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
    minWidth: 120,
  },
  exportButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#960018',
  },
  attachmentsSection: {
    marginTop: 20,
    padding: 16,
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginBottom: 30,
  },
  attachmentsSectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1E293B',
    marginBottom: 12,
  },
  productAttachments: {
    marginBottom: 12,
  },
  productAttachmentLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#64748B',
    marginBottom: 8,
  },
  attachmentDownloadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginBottom: 8,
    gap: 8,
  },
  attachmentDownloadText: {
    flex: 1,
    fontSize: 14,
    color: '#334155',
  },
  downloadAllZipBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 12,
    gap: 10,
  },
  downloadAllZipText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
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
  termRow: {
    marginBottom: 16,
  },
  termLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  termPickerContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  termOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
    gap: 6,
  },
  termOptionSelected: {
    borderColor: '#960018',
    backgroundColor: '#FFF5F5',
  },
  termOptionText: {
    fontSize: 13,
    color: '#666',
  },
  termOptionTextSelected: {
    color: '#960018',
    fontWeight: '600',
  },
});

export default QuoteDetailModal;
