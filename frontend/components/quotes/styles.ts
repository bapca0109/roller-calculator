// Shared styles for quote components
import { StyleSheet } from 'react-native';

export const quoteStyles = StyleSheet.create({
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  modalScroll: {
    padding: 16,
  },
  
  // Section styles
  detailSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  
  // Status styles
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
  
  // Product card styles
  productCard: {
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
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
  
  // Specs container
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
  
  // Remark styles
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
  
  // Pricing rows
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
  pricingLabelGreen: {
    fontSize: 14,
    color: '#4CAF50',
  },
  pricingValueGreen: {
    fontSize: 14,
    fontWeight: '500',
    color: '#4CAF50',
  },
  
  // Total row
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    marginTop: 8,
    paddingTop: 12,
  },
  totalLabel2: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  totalValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  
  // Buttons
  exportButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 16,
    borderRadius: 12,
    gap: 10,
    flex: 1,
  },
  exportButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  
  // Actions row
  detailActionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 20,
    marginBottom: 30,
  },
  
  // Editable product styles
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
  deleteProductButton: {
    padding: 4,
  },
  editableProductRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  
  // Discount mode toggle
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
  
  // Info rows
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
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
  },
  
  // Packing options
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
  
  // Approve/Reject buttons
  approveRejectButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20,
    marginBottom: 20,
  },
  approveConfirmButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
  },
  approveConfirmButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  rejectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DC3545',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    flex: 1,
  },
  rejectButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  
  // Attachments
  attachmentsSection: {
    marginTop: 20,
    padding: 16,
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  attachmentsSectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1E293B',
    marginBottom: 12,
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
  
  // Pending price message
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
  
  // RFQ Reference
  rfqReference: {
    fontSize: 12,
    color: '#0066cc',
    marginTop: 2,
    fontWeight: '500',
  },
  
  // Freight input styles
  freightInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 16,
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
  freightInputPrefix: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
    marginRight: 4,
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
  
  // Edit product card styles
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
  
  // Bulk discount
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
  
  // History button
  historyButton: {
    backgroundColor: '#475569',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 12,
    gap: 8,
  },
  historyButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  
  // Save buttons
  saveEditButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 20,
    marginBottom: 30,
    gap: 10,
  },
  saveEditButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  saveAndMailButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 16,
    gap: 8,
  },
  saveRevisionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2196F3',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 12,
    gap: 8,
  },
});
