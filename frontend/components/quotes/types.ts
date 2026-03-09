// Shared types for quote-related components

export interface QuoteProduct {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  specifications?: any;
  calculated_discount?: number;
  item_discount_percent?: number;
  remark?: string;
  attachments?: Array<{
    name: string;
    type: string;
    base64?: string;
  }>;
}

export interface Quote {
  id: string;
  quote_number?: string;
  customer_code?: string;
  customer_name: string;
  customer_email: string;
  customer_company?: string;
  customer_details?: {
    name?: string;
    company?: string;
    email?: string;
    phone?: string;
    address?: string;
    city?: string;
    state?: string;
    pincode?: string;
    gst_number?: string;
    customer_code?: string;
  };
  products: QuoteProduct[];
  subtotal: number;
  total_discount: number;
  use_item_discounts?: boolean;
  discount_percent?: number;
  packing_charges?: number;
  packing_type?: string;
  shipping_cost: number;
  delivery_location?: string;
  total_price: number;
  status: string;
  notes?: string;
  cost_breakdown?: any;
  pricing_details?: any;
  freight_details?: any;
  read_by_admin?: boolean;
  original_rfq_number?: string;
  customer_rfq_no?: string;
  approved_at?: string;
  approved_at_ist?: string;
  approved_by?: string;
  rejected_at?: string;
  rejected_by?: string;
  rejection_reason?: string;
  rejection_reason_text?: string;
  rejection_message?: string;
  revision_history?: RevisionHistoryEntry[];
  created_at: string;
  created_at_ist?: string;
  updated_at: string;
}

export interface RevisionHistoryEntry {
  timestamp: string;
  changed_by: string;
  changed_by_name?: string;
  action: string;
  changes: Record<string, { old: string; new: string }>;
  summary: string;
}

// Props for modal components
export interface QuoteModalBaseProps {
  visible: boolean;
  onClose: () => void;
}

export interface QuoteDetailModalProps extends QuoteModalBaseProps {
  quote: Quote | null;
  isAdmin: boolean;
  isCustomer: boolean;
  onApprove: (quote: Quote) => void;
  onReject: (quote: Quote) => void;
  onEdit: (quote: Quote) => void;
  onViewHistory: (quoteId: string) => void;
  onDownloadPdf: (quote: Quote) => void;
  generatingPdf: boolean;
}

export interface ApproveModalProps extends QuoteModalBaseProps {
  quote: Quote | null;
  onConfirmApprove: (quote?: Quote) => Promise<void>;
  onReject: (quote: Quote) => void;
  approvingId: string | null;
  // Editable state props
  editableProducts: QuoteProduct[];
  setEditableProducts: (products: QuoteProduct[]) => void;
  editPackingType: string;
  setEditPackingType: (type: string) => void;
  customPackingPercent: string;
  setCustomPackingPercent: (percent: string) => void;
  editDeliveryPincode: string;
  setEditDeliveryPincode: (pincode: string) => void;
  customFreightAmount: string;
  setCustomFreightAmount: (amount: string) => void;
  useItemDiscount: boolean;
  setUseItemDiscount: (use: boolean) => void;
  totalDiscountPercent: string;
  setTotalDiscountPercent: (percent: string) => void;
  itemDiscounts: { [key: number]: string };
  setItemDiscounts: (discounts: { [key: number]: string }) => void;
  pincodeValid: boolean;
  pincodeError: string;
  freightLoading: boolean;
  onPincodeChange: (pincode: string) => void;
}

export interface RejectModalProps extends QuoteModalBaseProps {
  quote: Quote | null;
  onConfirmReject: () => Promise<void>;
  rejectingId: string | null;
  selectedReason: string | null;
  setSelectedReason: (reason: string | null) => void;
}

export interface EditQuoteModalProps extends QuoteModalBaseProps {
  quote: Quote | null;
  onSaveAndMail: () => Promise<void>;
  savingEdit: boolean;
  // Editable state
  editedProducts: QuoteProduct[];
  setEditedProducts: (products: QuoteProduct[]) => void;
  useItemDiscounts: boolean;
  setUseItemDiscounts: (use: boolean) => void;
  editedDiscount: string;
  setEditedDiscount: (discount: string) => void;
  bulkDiscountPercent: string;
  setBulkDiscountPercent: (percent: string) => void;
  editedFreight: string;
  setEditedFreight: (freight: string) => void;
  editedPackingType: string;
  setEditedPackingType: (type: string) => void;
  customPackingPercent: string;
  setCustomPackingPercent: (percent: string) => void;
  calculateEditedTotal: () => {
    subtotal: number;
    discountAmount: number;
    afterDiscount: number;
    packingCharges: number;
    taxableAmount: number;
    total: number;
  };
}

export interface RevisionHistoryModalProps extends QuoteModalBaseProps {
  history: RevisionHistoryEntry[];
  loading: boolean;
}

export interface ApprovalSuccessModalProps extends QuoteModalBaseProps {
  quoteNumber: string;
}

// Helper type for discount modes
export type DiscountMode = 'total' | 'item-wise';

// Packing type options
export const PACKING_TYPES = [
  { label: 'Standard (1%)', value: 'standard', percent: 1 },
  { label: 'Pallet (4%)', value: 'pallet', percent: 4 },
  { label: 'Wooden Box (8%)', value: 'wooden_box', percent: 8 },
  { label: 'Custom', value: 'custom', percent: 0 },
];

// Reject reasons
export const REJECT_REASONS = [
  { id: 'pricing', label: 'Pricing not acceptable' },
  { id: 'specs', label: 'Specifications not available' },
  { id: 'stock', label: 'Out of stock' },
  { id: 'lead_time', label: 'Lead time too long' },
  { id: 'minimum_order', label: 'Below minimum order quantity' },
  { id: 'other', label: 'Other reason' },
];
