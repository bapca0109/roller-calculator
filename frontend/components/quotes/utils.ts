// Utility functions for quotes
import { Quote, QuoteProduct, PACKING_TYPES } from './types';

export const getStatusColor = (status: string): string => {
  switch (status?.toLowerCase()) {
    case 'approved':
      return '#10B981';
    case 'rejected':
      return '#EF4444';
    case 'pending':
      return '#F59E0B';
    case 'processing':
      return '#FF9500';
    default:
      return '#007AFF';
  }
};

export const getStatusIcon = (status: string): string => {
  switch (status?.toLowerCase()) {
    case 'approved':
      return 'checkmark-circle';
    case 'rejected':
      return 'close-circle';
    case 'processing':
      return 'time';
    default:
      return 'hourglass';
  }
};

export const formatDate = (dateString: string): string => {
  try {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
};

export const getPackingPercent = (packingType: string, customPercent: string): number => {
  if (packingType === 'custom') {
    return parseFloat(customPercent) || 0;
  }
  const option = PACKING_TYPES.find(p => p.value === packingType);
  return option?.percent || 1;
};

export const calculateTotals = (
  products: QuoteProduct[],
  useItemDiscount: boolean,
  totalDiscountPercent: string,
  itemDiscounts: { [key: number]: string },
  packingType: string,
  customPackingPercent: string,
  freightAmount: number
) => {
  const subtotal = products.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
  
  let discountAmount = 0;
  if (useItemDiscount) {
    products.forEach((product, index) => {
      const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
      const itemSubtotal = product.unit_price * product.quantity;
      discountAmount += itemSubtotal * (itemDiscountPct / 100);
    });
  } else {
    const discountPct = parseFloat(totalDiscountPercent) || 0;
    discountAmount = subtotal * (discountPct / 100);
  }
  
  const afterDiscount = subtotal - discountAmount;
  const packingPercent = getPackingPercent(packingType, customPackingPercent);
  const packingCharges = afterDiscount * (packingPercent / 100);
  const taxableAmount = afterDiscount + packingCharges + freightAmount;
  const total = taxableAmount * 1.18; // Include 18% GST
  
  return {
    subtotal,
    discountAmount,
    afterDiscount,
    packingCharges,
    freightAmount,
    taxableAmount,
    total
  };
};

export const formatCurrency = (amount: number): string => {
  return `Rs. ${amount.toFixed(2)}`;
};
