import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
  Modal,
  ScrollView,
  Platform,
  TextInput,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface QuoteProduct {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  specifications?: any;
  calculated_discount?: number;
  item_discount_percent?: number;  // Per-item discount percentage
  remark?: string;
  attachments?: Array<{
    name: string;
    type: string;
    base64?: string;
  }>;
}

interface Quote {
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
  use_item_discounts?: boolean;  // Toggle for per-item vs total discount
  discount_percent?: number;  // Overall discount percentage
  packing_charges?: number;
  packing_type?: string;  // standard, pallet, wooden_box
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
  revision_history?: RevisionHistoryEntry[];  // Track all changes made
  created_at: string;
  created_at_ist?: string;
  updated_at: string;
}

interface RevisionHistoryEntry {
  timestamp: string;
  changed_by: string;
  changed_by_name?: string;
  action: string;
  changes: Record<string, { old: string; new: string }>;
  summary: string;
}

export default function QuotesScreen() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [editingQuote, setEditingQuote] = useState<Quote | null>(null);
  const [editedProducts, setEditedProducts] = useState<QuoteProduct[]>([]);
  const [editedDiscount, setEditedDiscount] = useState<string>('0');
  const [editedFreight, setEditedFreight] = useState<string>('0');  // Editable freight for Edit Quote modal
  const [editedPackingType, setEditedPackingType] = useState<string>('standard');  // Editable packing type
  const [useItemDiscounts, setUseItemDiscounts] = useState(false);
  const [bulkDiscountPercent, setBulkDiscountPercent] = useState<string>('0');
  const [savingEdit, setSavingEdit] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approveModalQuote, setApproveModalQuote] = useState<Quote | null>(null);
  const [freightPercent, setFreightPercent] = useState<string>('0');
  const [customFreightAmount, setCustomFreightAmount] = useState<string>('');
  const [useCustomFreight, setUseCustomFreight] = useState(false);
  const [calculatedFreightFromPincode, setCalculatedFreightFromPincode] = useState<number>(0);
  const [freightLoading, setFreightLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Approval success popup state
  const [showApprovalSuccess, setShowApprovalSuccess] = useState(false);
  const [approvedQuoteNumber, setApprovedQuoteNumber] = useState('');
  
  // Rejection modal state
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectingQuote, setRejectingQuote] = useState<Quote | null>(null);
  const [selectedRejectReason, setSelectedRejectReason] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  
  // Revision history state
  const [showRevisionHistory, setShowRevisionHistory] = useState(false);
  const [revisionHistory, setRevisionHistory] = useState<RevisionHistoryEntry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // Edit RFQ modal state for viewing items
  const [editPackingType, setEditPackingType] = useState<string>('standard');
  const [editDeliveryPincode, setEditDeliveryPincode] = useState<string>('');
  const [customPackingPercent, setCustomPackingPercent] = useState<string>('');
  const [editableProducts, setEditableProducts] = useState<QuoteProduct[]>([]);
  const [pincodeError, setPincodeError] = useState<string>('');
  const [pincodeValid, setPincodeValid] = useState<boolean>(true);
  
  // Discount editing state
  const [useItemDiscount, setUseItemDiscount] = useState<boolean>(false);
  const [totalDiscountPercent, setTotalDiscountPercent] = useState<string>('0');
  const [itemDiscounts, setItemDiscounts] = useState<{[key: number]: string}>({});
  
  const { user, loading: authLoading } = useAuth();
  
  // Check if user is customer - show RFQ terminology
  const isCustomer = user?.role === 'customer';
  const isAdmin = user?.role === 'admin';
  const docLabel = isCustomer ? 'RFQ' : 'Quote';
  
  // Debug log
  console.log('QuotesScreen - user:', user, 'isCustomer:', isCustomer, 'isAdmin:', isAdmin, 'authLoading:', authLoading);

  // Authenticated file download function
  const downloadAttachment = async (quoteId: string, productIdx: number, attachmentIdx: number, filename: string) => {
    try {
      const token = await AsyncStorage.getItem('token');
      const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const url = `${baseUrl}/api/quotes/${quoteId}/attachments/${productIdx}/${attachmentIdx}/download`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      
      const blob = await response.blob();
      
      // Create download link
      if (Platform.OS === 'web') {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        Alert.alert('Info', 'File download is available on web only');
      }
    } catch (error: any) {
      console.error('Download error:', error);
      Alert.alert('Download Failed', error.message || 'Failed to download attachment');
    }
  };

  // Download all attachments as ZIP
  const downloadAllAsZip = async (quoteId: string, quoteNumber: string) => {
    try {
      const token = await AsyncStorage.getItem('token');
      const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const url = `${baseUrl}/api/quotes/${quoteId}/attachments/download-all`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      
      const blob = await response.blob();
      
      // Create download link
      if (Platform.OS === 'web') {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `${quoteNumber.replace(/\//g, '-')}_attachments.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        Alert.alert('Info', 'File download is available on web only');
      }
    } catch (error: any) {
      console.error('Download error:', error);
      Alert.alert('Download Failed', error.message || 'Failed to download attachments');
    }
  };

  useEffect(() => {
    // Only fetch quotes when auth is loaded and user exists
    if (!authLoading && user) {
      fetchQuotes();
    }
  }, [authLoading, user]);

  // Recalculate freight when discount changes (if freight is percentage-based)
  useEffect(() => {
    // Only recalculate if we're in approval mode and using freight percentage
    if ((selectedQuote || approveModalQuote) && !useCustomFreight && parseFloat(freightPercent) > 0) {
      // Freight percentage mode - recalculate based on new discount
      // The calculateFreightAmount function already handles this
      // Just trigger a re-render by updating a dummy state or relying on deps
    }
  }, [totalDiscountPercent, itemDiscounts, useItemDiscount, freightPercent, useCustomFreight]);

  const fetchQuotes = async () => {
    try {
      const response = await api.get('/quotes');
      setQuotes(response.data);
    } catch (error: any) {
      console.error('Error fetching quotes:', error);
      Alert.alert('Error', `Failed to load ${docLabel.toLowerCase()}s`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Mark RFQ as read by admin
  const markAsRead = async (quoteId: string) => {
    if (!isAdmin) return;
    
    try {
      await api.post(`/quotes/${quoteId}/mark-read`);
      // Update local state to reflect read status
      setQuotes(prevQuotes => 
        prevQuotes.map(q => 
          q.id === quoteId ? { ...q, read_by_admin: true } : q
        )
      );
    } catch (error) {
      console.error('Error marking quote as read:', error);
    }
  };

  // Fetch revision history for a quote
  const fetchRevisionHistory = async (quoteId: string) => {
    setLoadingHistory(true);
    try {
      const response = await api.get(`/quotes/${quoteId}/history`);
      const history = response.data.history || [];
      
      // Transform old format to new format if needed
      const transformedHistory: RevisionHistoryEntry[] = history.map((entry: any) => {
        // Check if it's old format (has 'revision' field) or new format (has 'action' field)
        if (entry.revision && !entry.action) {
          // Old format - transform to new format
          return {
            timestamp: entry.revised_at || '',
            changed_by: entry.revised_by || 'Unknown',
            changed_by_name: entry.revised_by || 'Unknown',
            action: 'revised',
            changes: {
              'Discount %': { old: '', new: `${entry.discount_percent || 0}%` },
              'Discount Amount': { old: '', new: `Rs. ${(entry.discount_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` },
              'Total Price': { old: '', new: `Rs. ${(entry.total_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` },
            },
            summary: `${entry.revision}: ${entry.notes || 'Quote revised'}`
          };
        }
        // New format - return as is
        return entry;
      });
      
      setRevisionHistory(transformedHistory);
      setShowRevisionHistory(true);
    } catch (error) {
      console.error('Error fetching revision history:', error);
      Alert.alert('Error', 'Failed to load revision history');
    } finally {
      setLoadingHistory(false);
    }
  };

  // Format revision timestamp
  const formatRevisionDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  // Open quote detail and mark as read
  const openQuoteDetail = (quote: Quote) => {
    setSelectedQuote(quote);
    // Initialize editable fields for admin
    setEditPackingType(quote.packing_type || 'standard');
    setEditDeliveryPincode(quote.delivery_location || '');
    setFreightPercent(quote.freight_details?.freight_percent?.toString() || '0');
    setCustomFreightAmount(quote.shipping_cost?.toString() || '0');
    setUseCustomFreight(false);
    setCustomPackingPercent('');
    setEditableProducts([...(quote.products || [])]);
    setPincodeError('');
    setPincodeValid(true);
    setCalculatedFreightFromPincode(0);
    // Initialize discount state
    setUseItemDiscount(quote.use_item_discounts || false);
    setTotalDiscountPercent(quote.discount_percent?.toString() || '0');
    // Initialize item discounts from products - use item_discount_percent field
    const discounts: {[key: number]: string} = {};
    quote.products?.forEach((p, idx) => {
      discounts[idx] = p.item_discount_percent?.toString() || '0';
    });
    setItemDiscounts(discounts);
    // Mark as read if admin and quote is pending RFQ and unread
    const isRfq = quote.quote_number?.startsWith('RFQ/');
    if (isAdmin && quote.status === 'pending' && isRfq && !quote.read_by_admin) {
      markAsRead(quote.id);
    }
    // DON'T auto-calculate freight from pincode here - use the original freight
    // The calculateFreightAmount function will recalculate based on discount changes
    // Just validate the pincode if it exists
    if (quote.delivery_location && quote.delivery_location.length === 6) {
      setTimeout(async () => {
        await validatePincode(quote.delivery_location!);
      }, 100);
    }
  };

  // Validate pincode using API
  const validatePincode = async (pincode: string) => {
    if (!pincode || pincode.length !== 6) {
      setPincodeError('Pincode must be 6 digits');
      setPincodeValid(false);
      return false;
    }
    
    try {
      const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const data = await response.json();
      
      if (data[0]?.Status === 'Success') {
        setPincodeError('');
        setPincodeValid(true);
        return true;
      } else {
        setPincodeError('Invalid pincode');
        setPincodeValid(false);
        return false;
      }
    } catch (error) {
      console.error('Pincode validation error:', error);
      setPincodeError('Unable to validate pincode');
      setPincodeValid(false);
      return false;
    }
  };

  // Handle pincode change with validation and freight calculation
  const handlePincodeChange = async (pincode: string) => {
    setEditDeliveryPincode(pincode);
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      // Validate pincode
      validatePincode(pincode);
      // Calculate freight automatically
      const productsToUse = editableProducts.length > 0 ? editableProducts : 
        (selectedQuote?.products || []);
      if (productsToUse.length > 0) {
        await calculateFreightFromPincode(pincode, productsToUse);
      }
    } else if (pincode.length > 0) {
      setPincodeError('Pincode must be 6 digits');
      setPincodeValid(false);
      setCalculatedFreightFromPincode(0);
    } else {
      setPincodeError('');
      setPincodeValid(true);
      setCalculatedFreightFromPincode(0);
    }
  };

  // Update product quantity
  const updateProductQuantity = (index: number, newQty: number | string) => {
    const qty = typeof newQty === 'string' ? parseInt(newQty) || 0 : newQty;
    if (qty < 1) return;
    const updatedProducts = [...editableProducts];
    updatedProducts[index] = {
      ...updatedProducts[index],
      quantity: qty
    };
    setEditableProducts(updatedProducts);
  };

  // Update quantity in editedProducts (for Edit Quote modal on approved quotes)
  const updateEditedProductQuantity = (index: number, newQty: string) => {
    const qty = parseInt(newQty) || 0;
    if (qty < 1) return;
    const updated = [...editedProducts];
    updated[index] = { ...updated[index], quantity: qty };
    setEditedProducts(updated);
  };

  // Delete product from list
  const deleteProduct = (index: number) => {
    if (editableProducts.length <= 1) {
      Alert.alert('Error', 'Cannot delete the last item. At least one item is required.');
      return;
    }
    const updatedProducts = editableProducts.filter((_, i) => i !== index);
    setEditableProducts(updatedProducts);
  };

  // Calculate editable subtotal
  const calculateEditableSubtotal = () => {
    return editableProducts.reduce((sum, product) => {
      return sum + (product.unit_price * product.quantity);
    }, 0);
  };

  // Calculate total discount based on mode
  const calculateTotalDiscount = () => {
    const subtotal = calculateEditableSubtotal();
    
    if (!useItemDiscount) {
      // Total discount mode
      const discountPct = parseFloat(totalDiscountPercent) || 0;
      return subtotal * (discountPct / 100);
    } else {
      // Item-wise discount mode
      return editableProducts.reduce((total, product, index) => {
        const itemSubtotal = product.unit_price * product.quantity;
        const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
        return total + (itemSubtotal * (itemDiscountPct / 100));
      }, 0);
    }
  };

  // Get unread count for badge - only count RFQs (customer-generated)
  const unreadCount = quotes.filter(q => 
    q.status === 'pending' && 
    q.quote_number?.startsWith('RFQ/') && 
    !q.read_by_admin
  ).length;

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchQuotes();
  }, []);

  // Edit quote functions
  const openEditQuote = (quote: Quote) => {
    setEditingQuote(quote);
    setEditedProducts([...quote.products]);
    setUseItemDiscounts(quote.use_item_discounts || false);
    // Calculate current discount percentage from the quote
    const discountPercent = quote.subtotal > 0 
      ? ((quote.total_discount / quote.subtotal) * 100).toFixed(1)
      : '0';
    setEditedDiscount(discountPercent);
    // Initialize freight with existing value
    setEditedFreight((quote.shipping_cost || 0).toString());
    // Initialize packing type - handle custom_X format
    const packingType = quote.packing_type || 'standard';
    if (packingType.startsWith('custom_')) {
      setEditedPackingType('custom');
      setCustomPackingPercent(packingType.split('_')[1] || '0');
    } else {
      setEditedPackingType(packingType);
      setCustomPackingPercent('');
    }
  };

  const updateProductItemDiscount = (index: number, newDiscount: string) => {
    const discount = parseFloat(newDiscount) || 0;
    const updated = [...editedProducts];
    updated[index] = { ...updated[index], item_discount_percent: Math.min(100, Math.max(0, discount)) };
    setEditedProducts(updated);
  };

  const applyDiscountToAllItems = () => {
    const discount = parseFloat(bulkDiscountPercent) || 0;
    const clampedDiscount = Math.min(100, Math.max(0, discount));
    const updated = editedProducts.map(p => ({
      ...p,
      item_discount_percent: clampedDiscount
    }));
    setEditedProducts(updated);
  };

  const calculateEditedTotal = () => {
    let subtotal = 0;
    let totalItemDiscount = 0;
    
    // Helper function to get packing percent from editedPackingType
    const getPackingPercent = () => {
      if (editedPackingType === 'standard') return 1;
      if (editedPackingType === 'pallet') return 4;
      if (editedPackingType === 'wooden_box') return 8;
      if (editedPackingType === 'custom') return parseFloat(customPackingPercent) || 0;
      if (editedPackingType.startsWith('custom_')) return parseFloat(editedPackingType.split('_')[1]) || 0;
      return 0;
    };
    
    if (useItemDiscounts) {
      // Calculate with item-level discounts
      editedProducts.forEach(p => {
        const itemDiscountPercent = p.item_discount_percent || 0;
        const lineOriginal = p.unit_price * p.quantity;
        const lineDiscounted = lineOriginal * (1 - itemDiscountPercent / 100);
        subtotal += lineOriginal; // Subtotal is before discounts
        totalItemDiscount += (lineOriginal - lineDiscounted);
      });
      
      const afterDiscount = subtotal - totalItemDiscount;
      const packingPercent = getPackingPercent();
      const newPacking = afterDiscount * packingPercent / 100;
      const freightAmount = parseFloat(editedFreight) || 0;
      const taxableAmount = afterDiscount + newPacking + freightAmount;
      const grandTotal = taxableAmount * 1.18; // Include 18% GST
      return {
        subtotal,
        discountAmount: totalItemDiscount,
        afterDiscount,
        packingCharges: newPacking,
        taxableAmount,
        total: grandTotal // Grand total with GST
      };
    } else {
      // Use total discount percentage
      subtotal = editedProducts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
      const discountAmount = (subtotal * (parseFloat(editedDiscount) || 0)) / 100;
      const afterDiscount = subtotal - discountAmount;
      const packingPercent = getPackingPercent();
      const newPacking = afterDiscount * packingPercent / 100;
      const freightAmount = parseFloat(editedFreight) || 0;
      const taxableAmount = afterDiscount + newPacking + freightAmount;
      const grandTotal = taxableAmount * 1.18; // Include 18% GST
      return {
        subtotal,
        discountAmount,
        afterDiscount,
        packingCharges: newPacking,
        taxableAmount,
        total: grandTotal // Grand total with GST
      };
    }
  };

  const saveEditedQuote = async () => {
    if (!editingQuote) return;
    
    setSavingEdit(true);
    try {
      const totals = calculateEditedTotal();
      const freightAmount = parseFloat(editedFreight) || 0;
      
      // Determine packing type string for storage
      const packingTypeToSave = editedPackingType === 'custom' 
        ? `custom_${customPackingPercent}` 
        : editedPackingType;
      
      const updateData: any = {
        products: editedProducts,
        subtotal: totals.subtotal,
        total_discount: totals.discountAmount,
        use_item_discounts: useItemDiscounts,
        packing_charges: totals.packingCharges,
        packing_type: packingTypeToSave,  // Include edited packing type
        shipping_cost: freightAmount,  // Include edited freight
        total_price: totals.total,
      };
      
      // Only include discount_percent if using total discount mode
      if (!useItemDiscounts) {
        updateData.discount_percent = parseFloat(editedDiscount) || 0;
      }
      
      await api.put(`/quotes/${editingQuote.id}`, updateData);
      Alert.alert('Success', `${docLabel} updated successfully`);
      setEditingQuote(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || `Failed to update ${docLabel.toLowerCase()}`);
    } finally {
      setSavingEdit(false);
    }
  };

  // Save revision and send email (for approved quotes)
  const saveRevisionAndMail = async () => {
    if (!editingQuote) return;
    
    setSavingRevision(true);
    try {
      const response = await api.post(`/quotes/${editingQuote.id}/revise`, {
        discount_percent: parseFloat(editedDiscount) || 0,
        notes: `Revised by admin`
      });
      
      Alert.alert(
        'Quote Revised Successfully!',
        `${response.data.revision}\nNew Total: Rs. ${response.data.new_total_price.toFixed(2)}\n\nEmail sent to customer and admin.`
      );
      setEditingQuote(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create revision');
    } finally {
      setSavingRevision(false);
    }
  };

  // Calculate freight amount - simple calculation based on admin input
  const calculateFreightAmount = () => {
    const quote = approveModalQuote || selectedQuote;
    if (!quote) return 0;
    
    // If custom freight amount is entered, use it directly
    if (useCustomFreight) {
      return parseFloat(customFreightAmount) || 0;
    }
    
    // Calculate freight as percentage of discounted subtotal ONLY
    const percent = parseFloat(freightPercent) || 0;
    if (percent === 0) return 0;
    
    // Get current subtotal from editable products
    const currentSubtotal = editableProducts.length > 0 
      ? editableProducts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0)
      : (quote.subtotal || 0);
    
    // Calculate discount based on admin's entered values
    let currentDiscount = 0;
    if (useItemDiscount) {
      currentDiscount = editableProducts.reduce((total, product, index) => {
        const itemSubtotal = product.unit_price * product.quantity;
        const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
        return total + (itemSubtotal * (itemDiscountPct / 100));
      }, 0);
    } else {
      const discountPct = parseFloat(totalDiscountPercent) || 0;
      currentDiscount = currentSubtotal * (discountPct / 100);
    }
    
    const discountedSubtotal = currentSubtotal - currentDiscount;
    
    // Freight = Discounted Subtotal × freight%
    return discountedSubtotal * (percent / 100);
  };

  // Calculate freight based on pincode and product weight
  const calculateFreightFromPincode = async (pincode: string, products: any[]) => {
    if (!pincode || pincode.length !== 6) {
      setCalculatedFreightFromPincode(0);
      return;
    }
    
    // Calculate total weight from products
    // Weight can be in multiple places: weight_kg, base_weight_kg, specifications.weight_kg, cost_breakdown.total_weight_kg
    const totalWeight = products.reduce((sum, p) => {
      let weight = 0;
      
      // Try different sources for weight
      if (p.weight_kg) {
        weight = p.weight_kg;
      } else if (p.base_weight_kg) {
        weight = p.base_weight_kg;
      } else if (p.specifications?.weight_kg) {
        weight = p.specifications.weight_kg;
      } else if (p.cost_breakdown?.single_roller_weight_kg) {
        weight = p.cost_breakdown.single_roller_weight_kg;
      } else if (p.pricing_details?.single_roller_weight_kg) {
        weight = p.pricing_details.single_roller_weight_kg;
      } else {
        // Estimate weight based on roller type if no weight data available
        // Average weight: Carrying ~5kg, Impact ~7kg, Return ~4kg
        const rollerType = p.specifications?.roller_type || p.product_name?.toLowerCase() || '';
        if (rollerType.includes('impact')) {
          weight = 7;
        } else if (rollerType.includes('return')) {
          weight = 4;
        } else {
          weight = 5; // Default carrying roller
        }
      }
      
      return sum + (weight * (p.quantity || 1));
    }, 0);
    
    if (totalWeight === 0) {
      setCalculatedFreightFromPincode(0);
      return;
    }
    
    setFreightLoading(true);
    try {
      // Call backend to calculate freight
      const response = await api.post('/calculate-freight', {
        pincode: pincode,
        total_weight_kg: totalWeight
      });
      
      if (response.data && response.data.freight_charges) {
        setCalculatedFreightFromPincode(response.data.freight_charges);
        // Auto-set as custom amount for clarity
        setCustomFreightAmount(response.data.freight_charges.toFixed(2));
        setUseCustomFreight(true);
      }
    } catch (error) {
      console.error('Freight calculation error:', error);
      setCalculatedFreightFromPincode(0);
    } finally {
      setFreightLoading(false);
    }
  };

  // Handle pincode change and calculate freight
  const handleDeliveryPincodeChange = async (pincode: string) => {
    setEditDeliveryPincode(pincode);
    
    // Validate pincode format
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      // Validate pincode
      validatePincode(pincode);
      
      // Calculate freight - prefer editableProducts (from approval modal) over original quote products
      const productsToUse = editableProducts.length > 0 ? editableProducts : 
        (approveModalQuote?.products || selectedQuote?.products || []);
      
      if (productsToUse.length > 0) {
        await calculateFreightFromPincode(pincode, productsToUse);
      }
    } else {
      setCalculatedFreightFromPincode(0);
    }
  };

  // Approve RFQ with freight
  const confirmApproveRfq = async (quoteOverride?: Quote) => {
    // Use quoteOverride if passed directly, otherwise use state
    const quote = quoteOverride || approveModalQuote || selectedQuote;
    if (!quote) return;
    
    // Validate pincode before approving
    if (editDeliveryPincode && !pincodeValid) {
      Alert.alert('Error', 'Please enter a valid pincode before approving.');
      return;
    }
    
    setApprovingId(quote.id);
    try {
      // Use editableProducts if available, otherwise fall back to quote's original products
      const productsToUse = editableProducts.length > 0 ? editableProducts : (quote.products || []);
      
      // Calculate updated subtotal from products (original, before discount)
      const updatedSubtotal = productsToUse.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
      
      // Calculate discount values FIRST
      // NOTE: When admin enters discount (total or item-wise), system-calculated discount is replaced
      let totalDiscountAmount = 0;
      let updatedProducts = [...productsToUse];
      
      if (useItemDiscount) {
        // Item-wise discount mode - update each product with its discount
        updatedProducts = productsToUse.map((product, index) => {
          const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
          const itemSubtotal = product.unit_price * product.quantity;
          const itemDiscountAmount = itemSubtotal * (itemDiscountPct / 100);
          totalDiscountAmount += itemDiscountAmount;
          return {
            ...product,
            item_discount_percent: itemDiscountPct,
            calculated_discount: 0  // Clear system discount - admin discount replaces it
          };
        });
      } else {
        // Total discount mode
        const discountPct = parseFloat(totalDiscountPercent) || 0;
        totalDiscountAmount = updatedSubtotal * (discountPct / 100);
        // Apply the same discount percentage to all items
        updatedProducts = productsToUse.map(product => ({
          ...product,
          item_discount_percent: parseFloat(totalDiscountPercent) || 0,
          calculated_discount: 0  // Clear system discount - admin discount replaces it
        }));
      }
      
      // Calculate discounted subtotal (after discount)
      const discountedSubtotal = updatedSubtotal - totalDiscountAmount;
      
      // Calculate packing charges based on DISCOUNTED subtotal
      let packingPercent = 0;
      if (editPackingType === 'standard') packingPercent = 1;
      else if (editPackingType === 'pallet') packingPercent = 4;
      else if (editPackingType === 'wooden_box') packingPercent = 8;
      else if (editPackingType === 'custom') packingPercent = parseFloat(customPackingPercent) || 0;
      
      const packingCharges = discountedSubtotal * (packingPercent / 100);
      
      // Get freight amount directly from custom input
      const freightAmount = parseFloat(customFreightAmount) || 0;
      
      // Calculate final total price
      const taxableAmount = discountedSubtotal + packingCharges + freightAmount;
      const gst = taxableAmount * 0.18;
      const totalPrice = taxableAmount * 1.18;
      
      // First update the quote with products, freight, packing and discount details
      await api.put(`/quotes/${quote.id}`, {
        products: updatedProducts,
        subtotal: updatedSubtotal,
        total_discount: totalDiscountAmount,
        use_item_discounts: useItemDiscount,
        discount_percent: useItemDiscount ? 0 : (parseFloat(totalDiscountPercent) || 0),
        packing_charges: packingCharges,
        shipping_cost: freightAmount,
        packing_type: editPackingType === 'custom' ? `custom_${customPackingPercent}` : editPackingType,
        delivery_location: editDeliveryPincode,
        total_price: totalPrice,
        freight_details: {
          freight_amount: freightAmount
        }
      });
      
      // Then approve
      const response = await api.post(`/quotes/${quote.id}/approve`);
      setApprovedQuoteNumber(response.data.new_quote_number || quote.quote_number);
      setShowApprovalSuccess(true);
      setApproveModalQuote(null);
      setSelectedQuote(null);
      fetchQuotes();
      setActiveTab('approved'); // Switch to approved tab
    } catch (error: any) {
      console.error('Approve RFQ error:', error);
      Alert.alert('Error', error.response?.data?.detail || 'Failed to approve RFQ');
    } finally {
      setApprovingId(null);
    }
  };

  // Approve RFQ function - open modal for freight input
  const approveRfq = async (quote: Quote) => {
    console.log('Opening approve modal for:', quote.quote_number);
    // Close the details modal first
    setSelectedQuote(null);
    setApproveModalQuote(quote);
    const existingFreightPercent = quote.freight_details?.freight_percent || 0;
    setFreightPercent(existingFreightPercent.toString());
    setCustomFreightAmount(quote.shipping_cost?.toString() || '0');
    setUseCustomFreight(false);
    // Set packing and delivery from quote
    setEditPackingType(quote.packing_type || 'standard');
    setEditDeliveryPincode(quote.delivery_location || '');
    // Initialize editable products for approval modal
    setEditableProducts([...(quote.products || [])]);
    // Reset freight calculation state
    setCalculatedFreightFromPincode(0);
    setPincodeError('');
    setPincodeValid(true);
    // Initialize discount state
    setUseItemDiscount(quote.use_item_discounts || false);
    setTotalDiscountPercent(quote.discount_percent?.toString() || '0');
    const discounts: {[key: number]: string} = {};
    quote.products?.forEach((p, idx) => {
      discounts[idx] = p.item_discount_percent?.toString() || '0';
    });
    setItemDiscounts(discounts);
    // If there's an existing delivery pincode, auto-calculate freight
    if (quote.delivery_location && quote.delivery_location.length === 6) {
      // Validate and calculate freight after a short delay to let state settle
      setTimeout(async () => {
        await validatePincode(quote.delivery_location!);
        if (quote.products && quote.products.length > 0) {
          await calculateFreightFromPincode(quote.delivery_location!, quote.products);
        }
      }, 100);
    }
  };
  
  // Open reject modal
  const openRejectModal = (quote: Quote) => {
    setRejectingQuote(quote);
    setSelectedRejectReason(null);
    setShowRejectModal(true);
  };
  
  // Confirm reject RFQ
  const confirmRejectRfq = async () => {
    if (!rejectingQuote || !selectedRejectReason) return;
    
    setRejectingId(rejectingQuote.id);
    try {
      await api.post(`/quotes/${rejectingQuote.id}/reject`, {
        reason: selectedRejectReason
      });
      
      Alert.alert('Success', 'RFQ has been rejected and the customer has been notified.');
      setShowRejectModal(false);
      setRejectingQuote(null);
      setSelectedRejectReason(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to reject RFQ');
    } finally {
      setRejectingId(null);
    }
  };

  // Filter quotes based on active tab and search query
  const getFilteredQuotes = () => {
    let filtered = quotes;
    
    // First filter by tab
    if (!isCustomer) {
      switch (activeTab) {
        case 'pending':
          filtered = filtered.filter(q => q.quote_number?.startsWith('RFQ') && q.status?.toLowerCase() !== 'approved' && q.status?.toLowerCase() !== 'rejected');
          break;
        case 'approved':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'approved');
          break;
        case 'rejected':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'rejected');
          break;
        default:
          break;
      }
    }
    
    // Then filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(q => {
        // Search by quote number
        if (q.quote_number?.toLowerCase().includes(query)) return true;
        // Search by customer name
        if (q.customer_name?.toLowerCase().includes(query)) return true;
        // Search by company
        if (q.customer_company?.toLowerCase().includes(query)) return true;
        if (q.customer_details?.company?.toLowerCase().includes(query)) return true;
        // Search by email
        if (q.customer_email?.toLowerCase().includes(query)) return true;
        // Search by phone
        if (q.customer_details?.phone?.toLowerCase().includes(query)) return true;
        // Search by GST
        if (q.customer_details?.gst_number?.toLowerCase().includes(query)) return true;
        // Search by city/state
        if (q.customer_details?.city?.toLowerCase().includes(query)) return true;
        if (q.customer_details?.state?.toLowerCase().includes(query)) return true;
        // Search by product names
        if (q.products?.some(p => p.product_name?.toLowerCase().includes(query))) return true;
        // Search by status
        if (q.status?.toLowerCase().includes(query)) return true;
        return false;
      });
    }
    
    // Sort by date - newest first
    filtered.sort((a, b) => {
      const dateA = new Date(a.approved_at || a.created_at || 0).getTime();
      const dateB = new Date(b.approved_at || b.created_at || 0).getTime();
      return dateB - dateA; // Descending order (newest first)
    });
    
    return filtered;
  };

  // Export search results to CSV
  const exportSearchResults = (type: string) => {
    const filteredQuotes = getFilteredQuotes();
    if (filteredQuotes.length === 0) {
      Alert.alert('No Data', 'No results to export');
      return;
    }

    // Create CSV content
    const headers = ['Quote Number', 'Customer Name', 'Company', 'Status', 'Total Price', 'Items', 'Date'];
    const rows = filteredQuotes.map(q => [
      q.quote_number || '',
      q.customer_name || '',
      q.customer_company || q.customer_details?.company || '',
      q.status || 'Pending',
      `Rs. ${(q.total_price || 0).toFixed(2)}`,
      (q.products?.length || 0).toString(),
      q.created_at ? new Date(q.created_at).toLocaleDateString('en-IN') : ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Download CSV
    if (Platform.OS === 'web') {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quotes_export_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      Alert.alert('Success', `Exported ${filteredQuotes.length} quotes to CSV`);
    } else {
      Alert.alert('Export', 'CSV export is available on web. Please use the web version for exports.');
    }
  };

  const pendingRfqCount = quotes.filter(q => q.quote_number?.startsWith('RFQ') && q.status?.toLowerCase() !== 'approved').length;

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return '#34C759';
      case 'rejected':
        return '#C41E3A';
      case 'processing':
        return '#FF9500';
      default:
        return '#007AFF';
    }
  };

  const getStatusIcon = (status: string): any => {
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

  const formatDate = (dateString: string) => {
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

  const generatePdfHtml = (quote: Quote) => {
    // Determine document label based on quote number prefix
    const isRfq = quote.quote_number?.startsWith('RFQ');
    const pdfDocLabel = isRfq ? 'RFQ' : 'Quotation';
    const pdfDocLabelFull = isRfq ? 'REQUEST FOR QUOTATION' : 'QUOTATION';
    
    // Use approval date for approved quotes, otherwise use created date
    const isApproved = quote.status?.toLowerCase() === 'approved';
    const displayDate = isApproved && (quote.approved_at_ist || quote.approved_at)
      ? (quote.approved_at_ist || formatDate(quote.approved_at))
      : (quote.created_at_ist || formatDate(quote.created_at));
    
    // Check if prices should be hidden (for customers viewing unapproved quotes)
    const shouldHidePrices = isCustomer && !isApproved;
    
    // ALWAYS use item-level discount format for PDF display
    // This shows: SR. | ITEM CODE | QTY | RATE | DISC % | VALUE AFTER DISC | TOTAL
    const useItemDiscounts = true;  // Always show per-item discount columns in PDF
    
    // Calculate totals with item discounts
    let calculatedSubtotal = 0;
    let totalItemDiscount = 0;
    
    const productsHtml = quote.products.map((product, index) => {
      // Use actual item discount if available, otherwise calculate from total discount
      const hasItemDiscounts = quote.use_item_discounts && product.item_discount_percent !== undefined;
      let itemDiscountPercent = 0;
      
      if (hasItemDiscounts) {
        itemDiscountPercent = product.item_discount_percent || 0;
      } else if (quote.total_discount > 0 && quote.subtotal > 0) {
        // Calculate per-item discount from total discount percentage
        itemDiscountPercent = (quote.total_discount / quote.subtotal) * 100;
      }
      
      const valueAfterDiscount = product.unit_price * (1 - itemDiscountPercent / 100);
      const lineTotal = product.quantity * valueAfterDiscount;
      const originalAmount = product.quantity * product.unit_price;
      const itemDiscountAmount = originalAmount - lineTotal;
      
      calculatedSubtotal += lineTotal;
      totalItemDiscount += itemDiscountAmount;
      
      // For customers with unapproved quotes, hide all pricing
      if (shouldHidePrices) {
        return `
          <tr>
            <td class="cell-center">${index + 1}</td>
            <td class="cell-left">
              <div class="product-name">${product.product_id}</div>
              ${product.specifications ? `
                <div class="product-specs">
                  ${product.specifications.roller_type ? `Type: ${product.specifications.roller_type}` : ''}
                  ${product.specifications.pipe_diameter ? ` | Pipe: ${product.specifications.pipe_diameter}mm` : ''}
                  ${product.specifications.shaft_diameter ? ` | Shaft: ${product.specifications.shaft_diameter}mm` : ''}
                  ${product.specifications.bearing ? ` | Bearing: ${product.specifications.bearing}` : ''}
                </div>
              ` : ''}
              ${product.remark ? `<div class="product-remark">Note: ${product.remark}</div>` : ''}
            </td>
            <td class="cell-center">${product.quantity}</td>
          </tr>
        `;
      }
      
      if (useItemDiscounts) {
        return `
          <tr>
            <td class="cell-center">${index + 1}</td>
            <td class="cell-left">
              <div class="product-name">${product.product_id}</div>
              ${product.specifications ? `
                <div class="product-specs">
                  ${product.specifications.roller_type ? `Type: ${product.specifications.roller_type}` : ''}
                  ${product.specifications.pipe_diameter ? ` | Pipe: ${product.specifications.pipe_diameter}mm` : ''}
                  ${product.specifications.shaft_diameter ? ` | Shaft: ${product.specifications.shaft_diameter}mm` : ''}
                  ${product.specifications.bearing ? ` | Bearing: ${product.specifications.bearing}` : ''}
                </div>
              ` : ''}
              ${product.remark ? `<div class="product-remark">Note: ${product.remark}</div>` : ''}
            </td>
            <td class="cell-center">${product.quantity}</td>
            <td class="cell-right">Rs. ${product.unit_price?.toFixed(2)}</td>
            <td class="cell-center">${itemDiscountPercent.toFixed(1)}%</td>
            <td class="cell-right">Rs. ${valueAfterDiscount.toFixed(2)}</td>
            <td class="cell-right"><strong>Rs. ${lineTotal.toFixed(2)}</strong></td>
          </tr>
        `;
      } else {
        return `
          <tr>
            <td class="cell-center">${index + 1}</td>
            <td class="cell-left">
              <div class="product-name">${product.product_name || product.product_id}</div>
              ${product.specifications ? `
                <div class="product-specs">
                  ${product.specifications.roller_type ? `Type: ${product.specifications.roller_type}` : ''}
                  ${product.specifications.pipe_diameter ? ` | Pipe: ${product.specifications.pipe_diameter}mm` : ''}
                  ${product.specifications.shaft_diameter ? ` | Shaft: ${product.specifications.shaft_diameter}mm` : ''}
                  ${product.specifications.bearing ? ` | Bearing: ${product.specifications.bearing}` : ''}
                </div>
              ` : ''}
              ${product.remark ? `<div class="product-remark">Note: ${product.remark}</div>` : ''}
            </td>
            <td class="cell-center">${product.quantity}</td>
            <td class="cell-right">Rs. ${product.unit_price?.toFixed(2)}</td>
            <td class="cell-right"><strong>Rs. ${(product.unit_price * product.quantity)?.toFixed(2)}</strong></td>
          </tr>
        `;
      }
    }).join('');

    // Calculate discount based on mode
    const discount = useItemDiscounts ? totalItemDiscount : (quote.total_discount || 0);
    const subtotalAfterDiscount = useItemDiscounts ? calculatedSubtotal : ((quote.subtotal || 0) - (quote.total_discount || 0));
    const taxableAmount = subtotalAfterDiscount + (quote.packing_charges || 0);
    const cgst = taxableAmount * 0.09;
    const sgst = taxableAmount * 0.09;
    const grandTotal = (taxableAmount + (quote.shipping_cost || 0)) * 1.18;
    
    // Dynamic table header - for customers with unapproved quotes, hide pricing columns
    const tableHeader = shouldHidePrices ? `
      <tr>
        <th style="width: 8%;">SR.</th>
        <th style="width: 72%; text-align: left;">ITEM CODE / DESCRIPTION</th>
        <th style="width: 20%;">QTY</th>
      </tr>
    ` : (useItemDiscounts ? `
      <tr>
        <th style="width: 5%;">SR.</th>
        <th style="width: 25%; text-align: left;">ITEM CODE</th>
        <th style="width: 8%;">QTY</th>
        <th style="width: 15%; text-align: right;">RATE</th>
        <th style="width: 12%;">DISC %</th>
        <th style="width: 17%; text-align: right;">VALUE AFTER DISC</th>
        <th style="width: 18%; text-align: right;">TOTAL</th>
      </tr>
    ` : `
      <tr>
        <th style="width: 5%;">#</th>
        <th style="width: 45%; text-align: left;">Description</th>
        <th style="width: 10%;">Qty</th>
        <th style="width: 20%; text-align: right;">Unit Price</th>
        <th style="width: 20%; text-align: right;">Amount</th>
      </tr>
    `);
    
    // Discount label
    const discountLabel = useItemDiscounts ? 'Item Discounts (Total)' : `Discount (${quote.subtotal > 0 ? ((quote.total_discount / quote.subtotal) * 100).toFixed(1) : 0}%)`;

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            color: #1a1a1a; 
            font-size: 11px;
            line-height: 1.4;
            padding: 15px;
          }
          
          /* Header */
          .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding-bottom: 15px;
            border-bottom: 2px solid #960018;
            margin-bottom: 15px;
          }
          .logo-section { }
          .logo {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -1px;
            color: #1a1a1a;
          }
          .logo span { color: #960018; }
          .company-tagline {
            font-size: 9px;
            color: #666;
            letter-spacing: 3px;
            margin-top: 2px;
          }
          .doc-type {
            text-align: right;
          }
          .doc-title {
            font-size: 18px;
            font-weight: 700;
            color: #960018;
            letter-spacing: 1px;
          }
          .doc-number {
            font-size: 13px;
            font-weight: 600;
            color: #333;
            margin-top: 3px;
          }
          .doc-date {
            font-size: 10px;
            color: #666;
            margin-top: 2px;
          }
          .doc-ref {
            font-size: 10px;
            color: #0066cc;
            margin-top: 3px;
            font-weight: 500;
          }
          
          /* Info Boxes */
          .info-section {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            gap: 15px;
          }
          .info-box {
            flex: 1;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background: #fafafa;
          }
          .info-box-title {
            font-size: 8px;
            font-weight: 600;
            color: #960018;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 4px;
          }
          .info-company {
            font-size: 12px;
            font-weight: 600;
            color: #1a1a1a;
          }
          .info-address {
            font-size: 10px;
            color: #555;
            margin-top: 4px;
            line-height: 1.5;
          }
          .info-gst {
            display: inline-block;
            margin-top: 6px;
            padding: 3px 8px;
            background: #e8f4fc;
            border-radius: 3px;
            font-size: 9px;
            color: #0066cc;
            font-weight: 500;
          }
          .info-contact {
            font-size: 9px;
            color: #666;
            margin-top: 6px;
          }
          
          /* Products Table */
          .section-title {
            font-size: 10px;
            font-weight: 600;
            color: #960018;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 8px 0;
            border-bottom: 1px solid #960018;
            margin-bottom: 0;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
          }
          th {
            background: #960018;
            color: white;
            padding: 8px 10px;
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          td {
            padding: 8px 10px;
            border-bottom: 1px solid #eee;
            font-size: 10px;
          }
          .cell-center { text-align: center; }
          .cell-right { text-align: right; }
          .cell-left { text-align: left; }
          .product-name { font-weight: 500; color: #1a1a1a; }
          .product-specs { font-size: 9px; color: #666; margin-top: 3px; }
          .product-remark { font-size: 9px; color: #0066cc; margin-top: 3px; font-style: italic; }
          
          /* Summary */
          .summary-section {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 15px;
          }
          .summary-table {
            width: 280px;
          }
          .summary-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 10px;
            border-bottom: 1px solid #eee;
          }
          .summary-label { color: #555; font-size: 10px; }
          .summary-value { font-weight: 500; font-size: 10px; }
          .discount-row { color: #28a745; }
          .total-row {
            background: #960018;
            color: white;
            border-radius: 4px;
            margin-top: 5px;
            padding: 10px;
          }
          .total-row .summary-label,
          .total-row .summary-value {
            color: white;
            font-size: 12px;
            font-weight: 600;
          }
          
          /* Delivery */
          .delivery-box {
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 10px;
          }
          
          /* Terms Section */
          .terms-container {
            margin-top: 20px;
            page-break-inside: avoid;
          }
          .terms-section {
            margin-bottom: 15px;
          }
          .terms-title {
            font-size: 11px;
            font-weight: 700;
            color: #960018;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 8px 0;
            border-bottom: 2px solid #960018;
            margin-bottom: 10px;
          }
          .terms-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
          }
          .term-item {
            padding: 8px;
            background: #fafafa;
            border-left: 3px solid #960018;
            font-size: 9px;
            line-height: 1.5;
          }
          .term-item-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
          }
          .term-item-text {
            color: #555;
          }
          .terms-full-width {
            grid-column: span 2;
          }
          
          /* Footer */
          .footer {
            margin-top: 25px;
            padding-top: 15px;
            border-top: 2px solid #960018;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
          }
          .footer-left {
            font-size: 9px;
            color: #666;
          }
          .footer-company {
            font-weight: 600;
            color: #1a1a1a;
            font-size: 11px;
          }
          .footer-right {
            text-align: right;
          }
          .footer-signature {
            border-top: 1px solid #333;
            padding-top: 5px;
            font-size: 9px;
            color: #333;
            font-weight: 500;
          }
          .footer-note {
            font-size: 8px;
            color: #999;
            margin-top: 10px;
            text-align: center;
          }
          
          @media print {
            body { padding: 10px; }
            .terms-container { page-break-before: auto; }
          }
        </style>
      </head>
      <body>
        <!-- Header -->
        <div class="header">
          <div class="logo-section">
            <div class="logo">C<span>O</span>NVER<span>O</span></div>
            <div class="company-tagline">SOLUTIONS</div>
          </div>
          <div class="doc-type">
            <div class="doc-title">${pdfDocLabelFull}</div>
            <div class="doc-number">${quote.quote_number || `#${quote.id.slice(-6).toUpperCase()}`}</div>
            ${quote.original_rfq_number ? `<div class="doc-ref">Ref: ${quote.original_rfq_number}</div>` : ''}
            <div class="doc-date">${displayDate}</div>
          </div>
        </div>

        <!-- Info Section -->
        <div class="info-section">
          <div class="info-box">
            <div class="info-box-title">From</div>
            <div class="info-company">Convero Solutions</div>
            <div class="info-address">
              Conveyor Roller Manufacturer<br>
              Ahmedabad, Gujarat - India
            </div>
            <div class="info-contact">
              info@convero.in | www.convero.in
            </div>
          </div>
          <div class="info-box">
            <div class="info-box-title">Bill To</div>
            ${quote.customer_code ? `<div class="customer-code" style="color: #960018; font-weight: bold; margin-bottom: 4px;">Customer Code: ${quote.customer_code}</div>` : ''}
            <div class="info-company">${quote.customer_company || quote.customer_details?.company || quote.customer_details?.name || quote.customer_name}</div>
            ${quote.customer_details?.address ? `
              <div class="info-address">
                ${quote.customer_details.address}${quote.customer_details.city ? `<br>${quote.customer_details.city}` : ''}${quote.customer_details.state ? `, ${quote.customer_details.state}` : ''}${quote.customer_details.pincode ? ` - ${quote.customer_details.pincode}` : ''}
              </div>
            ` : ''}
            ${quote.customer_details?.gst_number ? `
              <div class="info-gst">GSTIN: ${quote.customer_details.gst_number}</div>
            ` : ''}
            ${quote.customer_details?.phone || quote.customer_details?.email ? `
              <div class="info-contact">
                ${quote.customer_details.phone ? `Ph: ${quote.customer_details.phone}` : ''}
                ${quote.customer_details.phone && quote.customer_details.email ? ' | ' : ''}
                ${quote.customer_details.email || ''}
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Products Table -->
        <div class="section-title">Product Details</div>
        <table>
          <thead>
            ${tableHeader}
          </thead>
          <tbody>
            ${productsHtml}
          </tbody>
        </table>

        ${shouldHidePrices ? `
        <!-- Pricing Pending Notice for Customers -->
        <div class="delivery-box" style="background: #fff5f5; border-left: 3px solid #960018; text-align: center; padding: 20px;">
          <strong style="color: #960018; font-size: 14px;">Pricing Pending Approval</strong>
          <div style="margin-top: 8px; color: #666; font-size: 11px;">
            Pricing details will be available once your RFQ is reviewed and approved by our team.
          </div>
        </div>
        ` : `
        <!-- Summary -->
        <div class="summary-section">
          <div class="summary-table">
            <div class="summary-row">
              <span class="summary-label">Subtotal</span>
              <span class="summary-value">Rs. ${((quote.subtotal || 0) - (quote.total_discount || 0)).toFixed(2)}</span>
            </div>
            ${quote.packing_charges && quote.packing_charges > 0 ? `
              <div class="summary-row">
                <span class="summary-label">Packing Charges (${(((quote.packing_charges || 0) / ((quote.subtotal || 1) - (quote.total_discount || 0))) * 100).toFixed(1)}%)</span>
                <span class="summary-value">Rs. ${quote.packing_charges?.toFixed(2)}</span>
              </div>
            ` : ''}
            ${(quote.shipping_cost || 0) > 0 ? `
            <div class="summary-row">
              <span class="summary-label">Freight Charges</span>
              <span class="summary-value">Rs. ${(quote.shipping_cost || 0).toFixed(2)}</span>
            </div>
            ` : ''}
            <div class="summary-row" style="background: #f5f5f5;">
              <span class="summary-label"><strong>Taxable Amount</strong></span>
              <span class="summary-value"><strong>Rs. ${taxableAmount.toFixed(2)}</strong></span>
            </div>
            <div class="summary-row">
              <span class="summary-label">CGST @ 9%</span>
              <span class="summary-value">Rs. ${cgst.toFixed(2)}</span>
            </div>
            <div class="summary-row">
              <span class="summary-label">SGST @ 9%</span>
              <span class="summary-value">Rs. ${sgst.toFixed(2)}</span>
            </div>
            <div class="total-row">
              <span class="summary-label">GRAND TOTAL</span>
              <span class="summary-value">Rs. ${grandTotal.toFixed(2)}</span>
            </div>
          </div>
        </div>
        `}

        ${(quote.packing_type || quote.delivery_location) ? `
          <div class="delivery-box" style="display: flex; gap: 40px; flex-wrap: wrap;">
            ${quote.packing_type ? `
              <div>
                <strong>Packing Type:</strong> ${
                  quote.packing_type === 'standard' ? 'Standard (1%)' :
                  quote.packing_type === 'pallet' ? 'Pallet (4%)' :
                  quote.packing_type === 'wooden_box' ? 'Wooden Box (8%)' :
                  quote.packing_type
                }
              </div>
            ` : ''}
            ${quote.delivery_location ? `
              <div>
                <strong>Delivery Pincode:</strong> ${quote.delivery_location}
              </div>
            ` : ''}
            ${quote.customer_rfq_no ? `
              <div>
                <strong>Customer Ref:</strong> ${quote.customer_rfq_no}
              </div>
            ` : ''}
          </div>
        ` : ''}

        ${quote.notes ? `
          <div class="delivery-box" style="background: #fff5f5; border-left: 3px solid #960018;">
            <strong>Notes:</strong> ${quote.notes}
          </div>
        ` : ''}

        <!-- Terms & Conditions -->
        <div class="terms-container">
          <div class="terms-section">
            <div class="terms-title">Commercial Terms</div>
            <div class="terms-grid">
              <div class="term-item">
                <div class="term-item-title">Payment Terms</div>
                <div class="term-item-text">25% advance payment required at order confirmation. Remaining 75% payable against Proforma Invoice prior to dispatch.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Freight</div>
                <div class="term-item-text">Freight charges applicable as per selection. If no PIN code selected, delivery terms: Ex-Works – Convero Solutions, Ahmedabad.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Color Charges</div>
                <div class="term-item-text">Any color other than black shall be charged extra at 2%.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Quotation Validity</div>
                <div class="term-item-text">This quotation is valid for 30 days from date of issue.</div>
              </div>
            </div>
          </div>

          <div class="terms-section">
            <div class="terms-title">Technical Specifications</div>
            <div class="terms-grid">
              <div class="term-item">
                <div class="term-item-title">Pipe</div>
                <div class="term-item-text">IS-9295 ERW steel tubes for idlers of belt conveyors. Tolerances as per relevant IS standards.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Shaft</div>
                <div class="term-item-text">Material grade EN8.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Bearing</div>
                <div class="term-item-text">As per selection made in the application.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Circlip</div>
                <div class="term-item-text">Conforming to IS-3075 standard.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Housing</div>
                <div class="term-item-text">Deep drawn CRCA sheet conforming to IS-513, thickness 3.15 mm.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Seal Set</div>
                <div class="term-item-text">Self-designed Nylon-6 seal with metal cap, filled with EP-2 lithium-based grease for water/dust protection.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Rubber Ring</div>
                <div class="term-item-text">Shore hardness: 50-60. Impact rubber ring thickness may vary from drawings.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Painting</div>
                <div class="term-item-text">One coat black synthetic enamel (40 microns). Rust preventive coating on machined parts.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Packing</div>
                <div class="term-item-text">As per selection made in the application.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">TIR (Total Indicated Runout)</div>
                <div class="term-item-text">Shall not exceed 1.6 mm as per IS-8598.</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="footer">
          <div class="footer-left">
            <div class="footer-company">CONVERO SOLUTIONS</div>
            <div>Conveyor Roller Manufacturer</div>
            <div>www.convero.in</div>
          </div>
          <div class="footer-right">
            <div style="height: 40px;"></div>
            <div class="footer-signature">Authorized Signatory</div>
          </div>
        </div>
        
        <div class="footer-note">
          This is a computer-generated quotation. E&OE (Errors and Omissions Excepted)
        </div>
      </body>
      </html>
    `;
  };

  const exportToPdf = async () => {
    if (!selectedQuote) return;
    
    setGeneratingPdf(true);
    try {
      const html = generatePdfHtml(selectedQuote);
      
      if (Platform.OS === 'web') {
        // For web, open in new window and trigger print
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(html);
          printWindow.document.close();
          printWindow.focus();
          setTimeout(() => {
            printWindow.print();
          }, 500);
        } else {
          Alert.alert('Error', 'Please allow popups to export PDF');
        }
      } else {
        // For mobile, use Print.printAsync which opens native print dialog
        // User can save to Files from there
        await Print.printAsync({
          html,
        });
      }
    } catch (error: any) {
      console.error('PDF generation error:', error);
      Alert.alert('PDF Error', error.message || 'Failed to generate PDF');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const renderQuote = ({ item }: { item: Quote }) => {
    const isRfq = item.quote_number?.startsWith('RFQ/');
    const isApproved = item.status?.toLowerCase() === 'approved';
    const isRejected = item.status?.toLowerCase() === 'rejected';
    const canApprove = isAdmin && isRfq && !isApproved && !isRejected;
    
    // Debug log for each quote card
    console.log(`Quote ${item.quote_number}: isRfq=${isRfq}, isApproved=${isApproved}, isRejected=${isRejected}, isAdmin=${isAdmin}, canApprove=${canApprove}`);
    
    // Check if this is an unread pending RFQ (for admin) - only for customer RFQs
    const isUnread = isAdmin && item.status === 'pending' && isRfq && item.read_by_admin !== true;
    
    // Debug log
    if (isRfq) {
      console.log(`RFQ ${item.quote_number}: isUnread=${isUnread}, read_by_admin=${item.read_by_admin}, isAdmin=${isAdmin}`);
    }
    
    return (
    <TouchableOpacity
      style={[styles.quoteCard, isUnread && styles.unreadQuoteCard]}
      onPress={() => openQuoteDetail(item)}
    >
      <View style={styles.quoteHeader}>
        <View style={styles.quoteInfo}>
          <View style={styles.quoteIdRow}>
            {/* Unread indicator dot */}
            {isUnread && (
              <View style={styles.unreadDot} />
            )}
            <Text style={[styles.quoteId, isUnread && styles.unreadQuoteId]}>{item.quote_number || `${docLabel} #${item.id.slice(-6).toUpperCase()}`}</Text>
            {item.original_rfq_number && (
              <Text style={styles.rfqRefInCard}>({item.original_rfq_number})</Text>
            )}
          </View>
          <Text style={styles.quoteDate}>
            {isApproved && (item.approved_at_ist || item.approved_at)
              ? (item.approved_at_ist || formatDate(item.approved_at))
              : (item.created_at_ist || formatDate(item.created_at))}
          </Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: `${getStatusColor(item.status)}20` }]}>
          <Ionicons name={getStatusIcon(item.status)} size={16} color={getStatusColor(item.status)} />
          <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
            {item.status?.charAt(0).toUpperCase() + item.status?.slice(1)}
          </Text>
        </View>
      </View>

      {/* Customer & Company Name */}
      <View style={styles.customerRow}>
        {item.customer_code && (
          <View style={styles.customerCodeBadge}>
            <Text style={styles.customerCodeText}>{item.customer_code}</Text>
          </View>
        )}
        <Ionicons name="person-outline" size={16} color="#64748B" />
        <Text style={styles.customerName}>{item.customer_name || 'Unknown Customer'}</Text>
      </View>
      {(item.customer_details?.company || item.customer_company) && (
        <View style={styles.companyRow}>
          <Ionicons name="business-outline" size={16} color="#64748B" />
          <Text style={styles.companyName}>{item.customer_details?.company || item.customer_company}</Text>
        </View>
      )}

      <View style={styles.productsList}>
        {item.products.slice(0, 2).map((product, index) => (
          <Text key={index} style={styles.productItem} numberOfLines={1}>
            • {product.product_name || product.product_id} (Qty: {product.quantity})
          </Text>
        ))}
        {item.products.length > 2 && (
          <Text style={styles.moreProducts}>+{item.products.length - 2} more items</Text>
        )}
      </View>

      <View style={styles.quoteFooter}>
        <View>
          <Text style={styles.totalLabel}>{item.products.length} item{item.products.length !== 1 ? 's' : ''}</Text>
          {/* Admin always sees discount, Customer sees it only for approved quotes */}
          {(!isCustomer || isApproved) && (
            <Text style={[styles.discountBadge, { color: '#4CAF50', fontWeight: 'bold' }]}>
              Discount: {item.subtotal > 0 ? ((item.total_discount / item.subtotal) * 100).toFixed(1) : 0}%
            </Text>
          )}
        </View>
        {/* Admin always sees price, Customer sees it only for approved quotes */}
        {(!isCustomer || isApproved) && <Text style={styles.totalPrice}>Rs. {item.total_price?.toFixed(2) || '0.00'}</Text>}
      </View>
      
      {/* Show Approved badge for approved quotes - GREEN */}
      {isApproved && isRfq && (
        <View style={styles.approvedBadge}>
          <Ionicons name="checkmark-circle" size={18} color="#fff" />
          <Text style={styles.approveButtonText}>Approved</Text>
        </View>
      )}
      
      {/* Show Rejected badge for rejected quotes - RED */}
      {isRejected && isRfq && (
        <View style={styles.rejectedBadge}>
          <Ionicons name="close-circle" size={18} color="#fff" />
          <Text style={styles.approveButtonText}>Rejected</Text>
        </View>
      )}
    </TouchableOpacity>
    );
  };

  // Show loading until auth is ready
  if (authLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  if (loading && !refreshing) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading {docLabel.toLowerCase()}s...</Text>
      </View>
    );
  }

  // If Edit Quote is active, render full screen edit view using Modal
  if (approveModalQuote) {
    return (
      <Modal
        visible={true}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setApproveModalQuote(null)}
      >
        <View style={{ flex: 1, backgroundColor: '#fff' }}>
          <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }}>
            <View style={[styles.modalHeader, { backgroundColor: '#fff' }]}>
              <Text style={styles.modalTitle}>Edit Quote</Text>
              <TouchableOpacity onPress={() => setApproveModalQuote(null)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>
            <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={{paddingBottom: 120, backgroundColor: '#fff'}}>
          {/* RFQ Info */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>RFQ Details</Text>
            <Text style={styles.approveQuoteNumber}>{approveModalQuote.quote_number}</Text>
            <Text style={styles.approveCustomerName}>{approveModalQuote.customer_name}</Text>
            {approveModalQuote.customer_company && (
              <Text style={styles.approveCompanyName}>{approveModalQuote.customer_company}</Text>
            )}
          </View>

          {/* Products List */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Items Requested ({approveModalQuote.products?.length || 0})</Text>
            {approveModalQuote.products?.map((product, idx) => (
              <View key={idx} style={styles.editProductItem}>
                <View style={styles.editProductHeader}>
                  <Text style={styles.editProductName}>{product.product_name}</Text>
                  <Text style={styles.editProductQty}>Qty: {product.quantity}</Text>
                </View>
                <View style={styles.editProductDetails}>
                  <Text style={styles.editProductPrice}>Unit Price: Rs. {product.unit_price?.toFixed(2)}</Text>
                  <Text style={styles.editProductTotal}>Total: Rs. {(product.unit_price * product.quantity)?.toFixed(2)}</Text>
                </View>
                {product.remarks && (
                  <Text style={styles.editProductRemarks}>Remarks: {product.remarks}</Text>
                )}
              </View>
            ))}
            <View style={[styles.subtotalRow, { backgroundColor: '#fff' }]}>
              <Text style={styles.subtotalLabel}>Subtotal:</Text>
              <Text style={styles.subtotalValue}>Rs. {((approveModalQuote.subtotal || 0) - (approveModalQuote.total_discount || 0)).toFixed(2)}</Text>
            </View>
          </View>

          {/* Packing Type Selection */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Packing Type</Text>
            <View style={[styles.packingOptions, { backgroundColor: '#fff' }]}>
              {[
                { value: 'standard', label: 'Standard (1%)' },
                { value: 'pallet', label: 'Pallet (4%)' },
                { value: 'wooden_box', label: 'Wooden Box (8%)' }
              ].map((option) => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.packingOption,
                    editPackingType === option.value && styles.packingOptionActive
                  ]}
                  onPress={() => setEditPackingType(option.value)}
                >
                  <Ionicons 
                    name={editPackingType === option.value ? 'radio-button-on' : 'radio-button-off'} 
                    size={20} 
                    color={editPackingType === option.value ? '#960018' : '#666'} 
                  />
                  <Text style={[
                    styles.packingOptionText,
                    editPackingType === option.value && styles.packingOptionTextActive
                  ]}>{option.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Freight Section */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Freight Charges</Text>
            
            {/* Delivery Pincode */}
            <View style={[styles.freightInputRow, { backgroundColor: '#fff' }]}>
              <Text style={styles.freightInputLabel}>Delivery Pincode:</Text>
              <TextInput
                style={[styles.freightInput, { flex: 1 }, pincodeError ? { borderColor: '#ef4444' } : {}]}
                value={editDeliveryPincode}
                onChangeText={handleDeliveryPincodeChange}
                keyboardType="numeric"
                placeholder="Enter pincode"
                maxLength={6}
              />
              {freightLoading && (
                <ActivityIndicator size="small" color="#8B0000" style={{ marginLeft: 8 }} />
              )}
            </View>
            {pincodeError ? (
              <Text style={{ color: '#ef4444', fontSize: 12, marginTop: 4, marginLeft: 4 }}>{pincodeError}</Text>
            ) : null}
            {calculatedFreightFromPincode > 0 && !freightLoading && (
              <Text style={{ color: '#059669', fontSize: 12, marginTop: 4, marginLeft: 4 }}>
                Auto-calculated freight: Rs. {calculatedFreightFromPincode.toFixed(2)} (based on weight & distance)
              </Text>
            )}
            
            {/* Freight Input - Custom Amount Only */}
            <View style={styles.freightInputRow}>
              <Text style={styles.freightInputLabel}>Freight Charges:</Text>
              <View style={styles.freightInputWrapper}>
                <Text style={styles.freightInputPrefix}>Rs.</Text>
                <TextInput
                  style={styles.freightInput}
                  value={customFreightAmount}
                  onChangeText={setCustomFreightAmount}
                  keyboardType="numeric"
                  placeholder="0"
                />
              </View>
            </View>
          </View>

          {/* Action Buttons */}
          <View style={[styles.approveRejectButtons, { backgroundColor: '#fff' }]}>
            {/* Approve Button */}
            <TouchableOpacity 
              style={styles.approveConfirmButton}
              onPress={confirmApproveRfq}
              disabled={approvingId === approveModalQuote.id}
            >
              {approvingId === approveModalQuote.id ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={24} color="#fff" />
                  <Text style={styles.approveConfirmButtonText}>Approve</Text>
                </>
              )}
            </TouchableOpacity>
            
            {/* Reject Button */}
            <TouchableOpacity 
              style={styles.rejectButton}
              onPress={() => {
                const quoteToReject = approveModalQuote;
                setApproveModalQuote(null);
                if (quoteToReject) {
                  openRejectModal(quoteToReject);
                }
              }}
            >
              <Ionicons name="close-circle" size={24} color="#fff" />
              <Text style={styles.rejectButtonText}>Reject</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
          </SafeAreaView>
        </View>
      </Modal>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My {docLabel}s</Text>
        <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
          <Ionicons name="refresh" size={24} color="#960018" />
        </TouchableOpacity>
      </View>

      {/* Search Bar - Admin Only */}
      {isAdmin && (
        <View style={styles.searchContainer}>
          <View style={styles.searchInputWrapper}>
            <Ionicons name="search-outline" size={20} color="#94A3B8" style={styles.searchIcon} />
            <TextInput
              style={styles.searchInput}
              placeholder="Search by name, quote #, company, GST..."
              placeholderTextColor="#94A3B8"
              value={searchQuery}
              onChangeText={setSearchQuery}
              autoCapitalize="none"
              autoCorrect={false}
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')} style={styles.searchClearBtn}>
                <Ionicons name="close-circle" size={20} color="#94A3B8" />
              </TouchableOpacity>
            )}
          </View>
          {searchQuery.length > 0 && (
            <View style={styles.searchResultsRow}>
              <Text style={styles.searchResultCount}>
                {getFilteredQuotes().length} result{getFilteredQuotes().length !== 1 ? 's' : ''} found
              </Text>
              {getFilteredQuotes().length > 0 && (
                <TouchableOpacity 
                  style={styles.exportResultsBtn}
                  onPress={() => exportSearchResults('quotes')}
                >
                  <Ionicons name="download-outline" size={16} color="#960018" />
                  <Text style={styles.exportResultsBtnText}>Export</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>
      )}

      {/* Admin Filter Tabs */}
      {isAdmin && (
        <View style={styles.filterTabs}>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'all' && styles.filterTabActive]}
            onPress={() => setActiveTab('all')}
          >
            <Text style={[styles.filterTabText, activeTab === 'all' && styles.filterTabTextActive]}>All</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'pending' && styles.filterTabActive]}
            onPress={() => setActiveTab('pending')}
          >
            <View style={styles.tabWithBadge}>
              <Text style={[styles.filterTabText, activeTab === 'pending' && styles.filterTabTextActive]}>
                RFQ {pendingRfqCount > 0 && `(${pendingRfqCount})`}
              </Text>
              {/* Unread badge */}
              {unreadCount > 0 && (
                <View style={styles.unreadBadge}>
                  <Text style={styles.unreadBadgeText}>{unreadCount > 99 ? '99+' : unreadCount}</Text>
                </View>
              )}
            </View>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'approved' && styles.filterTabActive]}
            onPress={() => setActiveTab('approved')}
          >
            <Text style={[styles.filterTabText, activeTab === 'approved' && styles.filterTabTextActive]}>Approved</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'rejected' && styles.filterTabActive]}
            onPress={() => setActiveTab('rejected')}
          >
            <Text style={[styles.filterTabText, activeTab === 'rejected' && styles.filterTabTextActive]}>Rejected</Text>
          </TouchableOpacity>
        </View>
      )}

      <FlatList
        data={getFilteredQuotes()}
        renderItem={renderQuote}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#960018" />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>No {docLabel.toLowerCase()}s yet</Text>
            <Text style={styles.emptySubtext}>
              Go to Calculator tab to create your first {docLabel.toLowerCase()}
            </Text>
          </View>
        }
      />

      {/* Quote Detail Modal */}
      <Modal
        visible={!!selectedQuote && !approveModalQuote}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setSelectedQuote(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>
                  {selectedQuote?.quote_number || `${docLabel} #${selectedQuote?.id.slice(-6).toUpperCase()}`}
                </Text>
                {selectedQuote?.original_rfq_number && (
                  <Text style={styles.rfqReference}>Ref: {selectedQuote.original_rfq_number}</Text>
                )}
              </View>
              <TouchableOpacity onPress={() => setSelectedQuote(null)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalScroll}>
              {selectedQuote && (
                <>
                  {/* Status */}
                  <View style={styles.detailSection}>
                    <View style={[styles.statusBadgeLarge, { backgroundColor: `${getStatusColor(selectedQuote.status)}20` }]}>
                      <Ionicons name={getStatusIcon(selectedQuote.status)} size={20} color={getStatusColor(selectedQuote.status)} />
                      <Text style={[styles.statusTextLarge, { color: getStatusColor(selectedQuote.status) }]}>
                        {selectedQuote.status?.toUpperCase()}
                      </Text>
                    </View>
                  </View>

                  {/* Products - Editable for Admin on Pending RFQs */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Products</Text>
                    {isAdmin && selectedQuote.quote_number?.startsWith('RFQ') && selectedQuote.status?.toLowerCase() !== 'approved' && selectedQuote.status?.toLowerCase() !== 'rejected' ? (
                      // Editable products for admin
                      editableProducts.map((product, index) => (
                        <View key={index} style={styles.editableProductCard}>
                          <View style={styles.editableProductHeader}>
                            <Text style={styles.productName}>{product.product_name || product.product_id}</Text>
                            <TouchableOpacity 
                              style={styles.deleteProductButton}
                              onPress={() => deleteProduct(index)}
                            >
                              <Ionicons name="trash-outline" size={20} color="#DC3545" />
                            </TouchableOpacity>
                          </View>
                          <View style={styles.editableProductRow}>
                            <View style={styles.qtyEditContainer}>
                              <Text style={styles.qtyLabel}>Qty:</Text>
                              <TouchableOpacity 
                                style={styles.qtyButton}
                                onPress={() => updateProductQuantity(index, product.quantity - 1)}
                              >
                                <Ionicons name="remove" size={18} color="#333" />
                              </TouchableOpacity>
                              <TextInput
                                style={styles.qtyInput}
                                value={product.quantity.toString()}
                                onChangeText={(text) => {
                                  const qty = parseInt(text) || 1;
                                  updateProductQuantity(index, qty);
                                }}
                                keyboardType="numeric"
                              />
                              <TouchableOpacity 
                                style={styles.qtyButton}
                                onPress={() => updateProductQuantity(index, product.quantity + 1)}
                              >
                                <Ionicons name="add" size={18} color="#333" />
                              </TouchableOpacity>
                            </View>
                            {/* Show price with discount info for editable products */}
                            {(() => {
                              const originalPrice = product.unit_price * product.quantity;
                              const discountPct = useItemDiscount 
                                ? (parseFloat(itemDiscounts[index] || '0') || 0)
                                : (parseFloat(totalDiscountPercent) || 0);
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
                            })()}
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
                      ))
                    ) : (
                      // Read-only products for non-admin or approved quotes
                      selectedQuote.products.map((product, index) => (
                        <View key={index} style={styles.productCard}>
                          <Text style={styles.productName}>{product.product_name || product.product_id}</Text>
                          <View style={styles.productDetails}>
                            <Text style={styles.productQty}>Qty: {product.quantity}</Text>
                            {/* Hide price for customers unless quote is approved - show discounted value */}
                            {(!isCustomer || selectedQuote.status === 'approved') && (
                              (() => {
                                const originalPrice = product.unit_price * product.quantity;
                                const discountPct = product.item_discount_percent || 0;
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
                              })()
                            )}
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
                          {/* Product Remark */}
                          {product.remark && (
                            <View style={styles.remarkContainer}>
                              <Ionicons name="chatbubble-outline" size={14} color="#64748B" />
                              <Text style={styles.remarkText}>{product.remark}</Text>
                            </View>
                          )}
                        </View>
                      ))
                    )}
                  </View>

                  {/* Pricing Summary - Hidden for customers on pending RFQs */}
                  {(!isCustomer || selectedQuote.status === 'approved') && (
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Pricing Summary</Text>
                    
                    {/* Subtotal (after discount) */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Subtotal</Text>
                      <Text style={styles.pricingValue}>Rs. {((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0)).toFixed(2)}</Text>
                    </View>
                    
                    {/* Packing Charges with % - use actual packing type percentage */}
                    {(selectedQuote.packing_charges || 0) > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>
                          Packing Charges ({
                            selectedQuote.packing_type === 'standard' ? '1' :
                            selectedQuote.packing_type === 'pallet' ? '4' :
                            selectedQuote.packing_type === 'wooden_box' ? '8' :
                            selectedQuote.packing_type?.startsWith('custom_') ? selectedQuote.packing_type.split('_')[1] :
                            '0'
                          }%)
                        </Text>
                        <Text style={styles.pricingValue}>Rs. {(selectedQuote.packing_charges || 0).toFixed(2)}</Text>
                      </View>
                    )}
                    
                    {/* Freight Charges */}
                    {(selectedQuote.shipping_cost || 0) > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>Freight Charges</Text>
                        <Text style={styles.pricingValue}>Rs. {(selectedQuote.shipping_cost || 0).toFixed(2)}</Text>
                      </View>
                    )}
                    
                    {/* Taxable Amount = Subtotal + Packing + Freight */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Taxable Amount</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0) + (selectedQuote.packing_charges || 0) + (selectedQuote.shipping_cost || 0)).toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* CGST @ 9% */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>CGST @ 9%</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {(((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0) + (selectedQuote.packing_charges || 0) + (selectedQuote.shipping_cost || 0)) * 0.09).toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* SGST @ 9% */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>SGST @ 9%</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {(((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0) + (selectedQuote.packing_charges || 0) + (selectedQuote.shipping_cost || 0)) * 0.09).toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* Grand Total */}
                    <View style={[styles.pricingRow, styles.totalRow]}>
                      <Text style={styles.totalLabel2}>GRAND TOTAL</Text>
                      <Text style={styles.totalValue}>
                        Rs. {(((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0) + (selectedQuote.packing_charges || 0) + (selectedQuote.shipping_cost || 0)) * 1.18).toFixed(2)}
                      </Text>
                    </View>
                  </View>
                  )}
                  
                  {/* Show message for customers on pending RFQs */}
                  {isCustomer && selectedQuote.status === 'pending' && (
                    <View style={styles.detailSection}>
                      <View style={styles.pendingPriceMessage}>
                        <Ionicons name="time-outline" size={24} color="#F59E0B" />
                        <Text style={styles.pendingPriceText}>
                          Pricing will be available once your RFQ is approved by admin
                        </Text>
                      </View>
                    </View>
                  )}

                  {/* Delivery */}
                  {selectedQuote.delivery_location && (
                    <View style={styles.detailSection}>
                      <Text style={styles.sectionTitle}>Delivery</Text>
                      <Text style={styles.deliveryText}>Pincode: {selectedQuote.delivery_location}</Text>
                    </View>
                  )}

                  {/* Discount Section - Editable for Admin on Pending RFQs */}
                  {isAdmin && selectedQuote.quote_number?.startsWith('RFQ') && selectedQuote.status?.toLowerCase() !== 'approved' && selectedQuote.status?.toLowerCase() !== 'rejected' && (
                    <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
                      <Text style={styles.sectionTitle}>Discount</Text>
                      
                      {/* Discount Mode Toggle */}
                      <View style={styles.discountModeToggle}>
                        <TouchableOpacity 
                          style={[styles.modeButton, !useItemDiscount && styles.modeButtonActive]}
                          onPress={() => setUseItemDiscount(false)}
                        >
                          <Ionicons name="calculator-outline" size={18} color={!useItemDiscount ? "#fff" : "#666"} />
                          <Text style={[styles.modeButtonText, !useItemDiscount && styles.modeButtonTextActive]}>
                            Total Discount
                          </Text>
                        </TouchableOpacity>
                        <TouchableOpacity 
                          style={[styles.modeButton, useItemDiscount && styles.modeButtonActive]}
                          onPress={() => setUseItemDiscount(true)}
                        >
                          <Ionicons name="list-outline" size={18} color={useItemDiscount ? "#fff" : "#666"} />
                          <Text style={[styles.modeButtonText, useItemDiscount && styles.modeButtonTextActive]}>
                            Item-wise
                          </Text>
                        </TouchableOpacity>
                      </View>

                      {/* Total Discount Input */}
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
                        // Item-wise Discount
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
                                    setItemDiscounts(prev => ({...prev, [index]: text}));
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

                      {/* Calculated Discount Amount */}
                      <View style={styles.calculatedFreightRow}>
                        <Text style={styles.calculatedFreightLabel}>Total Discount Amount:</Text>
                        <Text style={[styles.calculatedFreightValue, { color: '#4CAF50' }]}>
                          - Rs. {calculateTotalDiscount().toFixed(2)}
                        </Text>
                      </View>
                    </View>
                  )}

                  {/* Packing & Freight Details - Editable for Admin on Pending RFQs */}
                  {isAdmin && selectedQuote.quote_number?.startsWith('RFQ') && selectedQuote.status?.toLowerCase() !== 'approved' && selectedQuote.status?.toLowerCase() !== 'rejected' ? (
                    <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
                      <Text style={styles.sectionTitle}>Packing & Freight (Editable)</Text>
                      
                      {/* Packing Type Selection */}
                      <Text style={styles.fieldLabel}>Packing Type</Text>
                      <View style={styles.packingOptions}>
                        {[
                          { value: 'standard', label: 'Standard (1%)' },
                          { value: 'pallet', label: 'Pallet (4%)' },
                          { value: 'wooden_box', label: 'Wooden Box (8%)' },
                          { value: 'custom', label: 'Custom' }
                        ].map((option) => (
                          <TouchableOpacity
                            key={option.value}
                            style={[
                              styles.packingOption,
                              editPackingType === option.value && styles.packingOptionActive
                            ]}
                            onPress={() => setEditPackingType(option.value)}
                          >
                            <Ionicons 
                              name={editPackingType === option.value ? 'radio-button-on' : 'radio-button-off'} 
                              size={20} 
                              color={editPackingType === option.value ? '#960018' : '#666'} 
                            />
                            <Text style={[
                              styles.packingOptionText,
                              editPackingType === option.value && styles.packingOptionTextActive
                            ]}>{option.label}</Text>
                          </TouchableOpacity>
                        ))}
                      </View>
                      
                      {/* Custom Packing Percentage Input */}
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
                      
                      {/* Delivery Pincode with Validation */}
                      <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Delivery Pincode</Text>
                      <TextInput
                        style={[
                          styles.editableInput,
                          !pincodeValid && styles.inputError
                        ]}
                        value={editDeliveryPincode}
                        onChangeText={handlePincodeChange}
                        keyboardType="numeric"
                        placeholder="Enter pincode"
                        maxLength={6}
                      />
                      {pincodeError ? (
                        <Text style={styles.errorText}>{pincodeError}</Text>
                      ) : null}
                      {freightLoading && (
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 8 }}>
                          <ActivityIndicator size="small" color="#8B0000" />
                          <Text style={{ marginLeft: 8, color: '#666' }}>Calculating freight...</Text>
                        </View>
                      )}
                      {calculatedFreightFromPincode > 0 && !freightLoading && (
                        <Text style={{ color: '#059669', fontSize: 12, marginTop: 4 }}>
                          Auto-calculated freight: Rs. {calculatedFreightFromPincode.toFixed(2)} (based on weight & distance)
                        </Text>
                      )}
                      
                      {/* Freight Mode Toggle */}
                      <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Freight Charges</Text>
                      {/* Freight Input - Custom Amount Only */}
                      <View style={styles.freightInputRow}>
                        <Text style={styles.freightInputLabel}>Freight Charges:</Text>
                        <View style={styles.freightInputWrapper}>
                          <Text style={styles.freightInputPrefix}>Rs.</Text>
                          <TextInput
                            style={styles.freightInput}
                            value={customFreightAmount}
                            onChangeText={setCustomFreightAmount}
                            keyboardType="numeric"
                            placeholder="0"
                          />
                        </View>
                      </View>
                    </View>
                  ) : (
                    /* Read-only Packing & Freight for non-editable cases */
                    (selectedQuote.packing_type || selectedQuote.delivery_location) && (
                      <View style={styles.detailSection}>
                        <Text style={styles.sectionTitle}>Packing & Freight</Text>
                        {selectedQuote.packing_type && (
                          <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Packing Type:</Text>
                            <Text style={styles.infoValue}>
                              {selectedQuote.packing_type === 'standard' ? 'Standard (1%)' :
                               selectedQuote.packing_type === 'pallet' ? 'Pallet (4%)' :
                               selectedQuote.packing_type === 'wooden_box' ? 'Wooden Box (8%)' :
                               selectedQuote.packing_type}
                            </Text>
                          </View>
                        )}
                        {selectedQuote.delivery_location && (
                          <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Delivery Pincode:</Text>
                            <Text style={styles.infoValue}>{selectedQuote.delivery_location}</Text>
                          </View>
                        )}
                        {selectedQuote.shipping_cost > 0 && (
                          <View style={styles.infoRow}>
                            <Text style={styles.infoLabel}>Freight:</Text>
                            <Text style={styles.infoValue}>Rs. {selectedQuote.shipping_cost.toFixed(2)}</Text>
                          </View>
                        )}
                      </View>
                    )
                  )}

                  {/* Customer RFQ Reference */}
                  {selectedQuote.customer_rfq_no && (
                    <View style={styles.detailSection}>
                      <Text style={styles.sectionTitle}>Customer Reference</Text>
                      <Text style={styles.deliveryText}>{selectedQuote.customer_rfq_no}</Text>
                    </View>
                  )}

                  {/* Notes */}
                  {selectedQuote.notes && (
                    <View style={styles.detailSection}>
                      <Text style={styles.sectionTitle}>Notes</Text>
                      <Text style={styles.notesText}>{selectedQuote.notes}</Text>
                    </View>
                  )}

                  {/* Date */}
                  <View style={styles.detailSection}>
                    <Text style={styles.dateText}>
                      {selectedQuote.status?.toLowerCase() === 'approved' && (selectedQuote.approved_at_ist || selectedQuote.approved_at)
                        ? `Approved: ${selectedQuote.approved_at_ist || formatDate(selectedQuote.approved_at)}`
                        : `Created: ${selectedQuote.created_at_ist || formatDate(selectedQuote.created_at)}`}
                    </Text>
                  </View>

                  {/* Action Buttons Row */}
                  <View style={styles.detailActionsRow}>
                    {/* Approve & Reject Buttons - Admin only, for pending RFQs */}
                    {isAdmin && selectedQuote.quote_number?.startsWith('RFQ') && selectedQuote.status?.toLowerCase() !== 'approved' && selectedQuote.status?.toLowerCase() !== 'rejected' && (
                      <>
                        <TouchableOpacity 
                          style={styles.approveConfirmButton}
                          onPress={() => {
                            // Directly approve with current freight/packing values
                            confirmApproveRfq(selectedQuote);
                          }}
                          disabled={approvingId === selectedQuote.id}
                        >
                          {approvingId === selectedQuote.id ? (
                            <ActivityIndicator color="#fff" />
                          ) : (
                            <>
                              <Ionicons name="checkmark-circle" size={24} color="#fff" />
                              <Text style={styles.approveConfirmButtonText}>Approve</Text>
                            </>
                          )}
                        </TouchableOpacity>
                        
                        <TouchableOpacity 
                          style={styles.rejectButton}
                          onPress={() => {
                            setSelectedQuote(null);
                            openRejectModal(selectedQuote);
                          }}
                        >
                          <Ionicons name="close-circle" size={24} color="#fff" />
                          <Text style={styles.rejectButtonText}>Reject</Text>
                        </TouchableOpacity>
                      </>
                    )}

                    {/* Edit Quote Button - Admin only, for approved quotes */}
                    {isAdmin && selectedQuote.status?.toLowerCase() === 'approved' && (
                      <TouchableOpacity 
                        style={styles.editQuoteButton}
                        onPress={() => {
                          setSelectedQuote(null);
                          openEditQuote(selectedQuote);
                        }}
                      >
                        <Ionicons name="create-outline" size={24} color="#fff" />
                        <Text style={styles.editQuoteButtonText}>Edit Quote</Text>
                      </TouchableOpacity>
                    )}

                    {/* View History Button - Admin only */}
                    {isAdmin && (
                      <TouchableOpacity 
                        style={styles.historyButton}
                        onPress={() => fetchRevisionHistory(selectedQuote.id)}
                        disabled={loadingHistory}
                      >
                        {loadingHistory ? (
                          <ActivityIndicator color="#fff" size="small" />
                        ) : (
                          <>
                            <Ionicons name="time-outline" size={24} color="#fff" />
                            <Text style={styles.historyButtonText}>History</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    )}

                    {/* Export PDF Button */}
                    <TouchableOpacity 
                      style={[styles.exportButton, !(isAdmin && selectedQuote.quote_number?.startsWith('RFQ') && selectedQuote.status?.toLowerCase() !== 'approved' && selectedQuote.status?.toLowerCase() !== 'rejected') && !(isAdmin && selectedQuote.status?.toLowerCase() === 'approved') ? { flex: 1 } : {}]}
                      onPress={exportToPdf}
                      disabled={generatingPdf}
                    >
                      {generatingPdf ? (
                        <ActivityIndicator color="#fff" />
                      ) : (
                        <>
                          <Ionicons name="download-outline" size={24} color="#fff" />
                          <Text style={styles.exportButtonText}>Export PDF</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  </View>
                  
                  {/* Attachments Section - Admin Only */}
                  {!isCustomer && selectedQuote.products?.some((p: any) => p.attachments?.length > 0) && (
                    <View style={styles.attachmentsSection}>
                      <Text style={styles.attachmentsSectionTitle}>
                        <Ionicons name="attach" size={18} color="#1E293B" /> Attachments
                      </Text>
                      
                      {selectedQuote.products.map((product: any, pIdx: number) => (
                        product.attachments?.length > 0 && (
                          <View key={pIdx} style={styles.productAttachments}>
                            <Text style={styles.productAttachmentLabel}>{product.product_name || `Product ${pIdx + 1}`}</Text>
                            {product.attachments.map((att: any, aIdx: number) => (
                              <TouchableOpacity
                                key={aIdx}
                                style={styles.attachmentDownloadBtn}
                                onPress={() => downloadAttachment(selectedQuote.id, pIdx, aIdx, att.name || `attachment_${aIdx}`)}
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
                        )
                      ))}
                      
                      {/* Download All as ZIP */}
                      {selectedQuote.products.reduce((sum: number, p: any) => sum + (p.attachments?.length || 0), 0) > 1 && (
                        <TouchableOpacity
                          style={styles.downloadAllZipBtn}
                          onPress={() => downloadAllAsZip(selectedQuote.id, selectedQuote.quote_number || selectedQuote.id)}
                        >
                          <Ionicons name="archive" size={20} color="#fff" />
                          <Text style={styles.downloadAllZipText}>Download All as ZIP</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  )}
                </>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Reject Reason Modal */}
      <Modal
        visible={showRejectModal}
        animationType="fade"
        transparent={false}
        onRequestClose={() => setShowRejectModal(false)}
      >
        <View style={styles.editQuoteModalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Reject RFQ</Text>
            <TouchableOpacity onPress={() => setShowRejectModal(false)}>
              <Ionicons name="close" size={28} color="#333" />
            </TouchableOpacity>
          </View>
          <ScrollView style={styles.modalScroll}>
              {rejectingQuote && (
                <>
                  <Text style={styles.rejectModalSubtitle}>
                    Select a reason for rejecting {rejectingQuote.quote_number}
                  </Text>
                  
                  {/* Rejection Reason Options */}
                  <View style={styles.rejectReasonOptions}>
                    <TouchableOpacity
                      style={[
                        styles.rejectReasonOption,
                        selectedRejectReason === 'low_quantity' && styles.rejectReasonOptionActive
                      ]}
                      onPress={() => setSelectedRejectReason('low_quantity')}
                    >
                      <Ionicons 
                        name={selectedRejectReason === 'low_quantity' ? 'radio-button-on' : 'radio-button-off'} 
                        size={24} 
                        color={selectedRejectReason === 'low_quantity' ? '#960018' : '#666'} 
                      />
                      <Text style={[
                        styles.rejectReasonText,
                        selectedRejectReason === 'low_quantity' && styles.rejectReasonTextActive
                      ]}>Rejected due to low quantity</Text>
                    </TouchableOpacity>
                    
                    <TouchableOpacity
                      style={[
                        styles.rejectReasonOption,
                        selectedRejectReason === 'low_amount' && styles.rejectReasonOptionActive
                      ]}
                      onPress={() => setSelectedRejectReason('low_amount')}
                    >
                      <Ionicons 
                        name={selectedRejectReason === 'low_amount' ? 'radio-button-on' : 'radio-button-off'} 
                        size={24} 
                        color={selectedRejectReason === 'low_amount' ? '#960018' : '#666'} 
                      />
                      <Text style={[
                        styles.rejectReasonText,
                        selectedRejectReason === 'low_amount' && styles.rejectReasonTextActive
                      ]}>Rejected due to low amount</Text>
                    </TouchableOpacity>
                    
                    <TouchableOpacity
                      style={[
                        styles.rejectReasonOption,
                        selectedRejectReason === 'not_in_range' && styles.rejectReasonOptionActive
                      ]}
                      onPress={() => setSelectedRejectReason('not_in_range')}
                    >
                      <Ionicons 
                        name={selectedRejectReason === 'not_in_range' ? 'radio-button-on' : 'radio-button-off'} 
                        size={24} 
                        color={selectedRejectReason === 'not_in_range' ? '#960018' : '#666'} 
                      />
                      <Text style={[
                        styles.rejectReasonText,
                        selectedRejectReason === 'not_in_range' && styles.rejectReasonTextActive
                      ]}>Rejected due to product is not within the manufacturing range</Text>
                    </TouchableOpacity>
                  </View>
                  
                  {/* Confirm Reject Button */}
                  <TouchableOpacity 
                    style={[
                      styles.confirmRejectButton,
                      !selectedRejectReason && styles.confirmRejectButtonDisabled
                    ]}
                    onPress={confirmRejectRfq}
                    disabled={!selectedRejectReason || rejectingId === rejectingQuote.id}
                  >
                    {rejectingId === rejectingQuote.id ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="close-circle" size={24} color="#fff" />
                        <Text style={styles.confirmRejectButtonText}>Confirm Rejection</Text>
                      </>
                    )}
                  </TouchableOpacity>
                </>
              )}
            </ScrollView>
          </View>
      </Modal>

      {/* Approval Success Popup Modal */}
      <Modal
        visible={showApprovalSuccess}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setShowApprovalSuccess(false)}
      >
        <View style={styles.successModalOverlay}>
          <View style={styles.successModalContent}>
            <View style={styles.successIconContainer}>
              <Ionicons name="checkmark-circle" size={64} color="#4CAF50" />
            </View>
            <Text style={styles.successTitle}>Approved & Submitted!</Text>
            <Text style={styles.successMessage}>
              RFQ has been converted to Quote
            </Text>
            <Text style={styles.successQuoteNumber}>{approvedQuoteNumber}</Text>
            <Text style={styles.successSubtext}>
              The customer has been notified via email.
            </Text>
            <TouchableOpacity 
              style={styles.successButton}
              onPress={() => {
                setShowApprovalSuccess(false);
                setActiveTab('approved'); // Switch to approved tab
              }}
            >
              <Text style={styles.successButtonText}>View Approved Quotes</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.successCloseButton}
              onPress={() => setShowApprovalSuccess(false)}
            >
              <Text style={styles.successCloseText}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Edit Quote Modal */}
      <Modal
        visible={!!editingQuote}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setEditingQuote(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit {docLabel}</Text>
              <TouchableOpacity onPress={() => setEditingQuote(null)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.modalScroll}>
              {editingQuote && (
                <>
                  {/* Discount Mode Toggle */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Discount Mode</Text>
                    <View style={styles.discountModeToggle}>
                      <TouchableOpacity 
                        style={[styles.modeButton, !useItemDiscounts && styles.modeButtonActive]}
                        onPress={() => setUseItemDiscounts(false)}
                      >
                        <Ionicons name="calculator-outline" size={18} color={!useItemDiscounts ? "#fff" : "#666"} />
                        <Text style={[styles.modeButtonText, !useItemDiscounts && styles.modeButtonTextActive]}>
                          Total Discount
                        </Text>
                      </TouchableOpacity>
                      <TouchableOpacity 
                        style={[styles.modeButton, useItemDiscounts && styles.modeButtonActive]}
                        onPress={() => setUseItemDiscounts(true)}
                      >
                        <Ionicons name="list-outline" size={18} color={useItemDiscounts ? "#fff" : "#666"} />
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
                        <TouchableOpacity 
                          style={styles.bulkApplyButton}
                          onPress={applyDiscountToAllItems}
                        >
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
                                onChangeText={(text) => updateEditedProductQuantity(index, text)}
                                keyboardType="numeric"
                              />
                            </View>
                            
                            {useItemDiscounts && (
                              <View style={styles.inputGroup}>
                                <Text style={styles.inputLabel}>Disc %</Text>
                                <TextInput
                                  style={styles.smallInput}
                                  value={itemDiscount.toString()}
                                  onChangeText={(text) => updateProductItemDiscount(index, text)}
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

                  {/* Total Discount - Only show if not using item discounts */}
                  {!useItemDiscounts && (
                    <View style={styles.detailSection}>
                      <Text style={styles.sectionTitle}>Total Discount</Text>
                      <View style={styles.discountInputRow}>
                        <TextInput
                          style={styles.discountInput}
                          value={editedDiscount}
                          onChangeText={setEditedDiscount}
                          keyboardType="numeric"
                          placeholder="0"
                        />
                        <Text style={styles.discountPercent}>%</Text>
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
                    {editingQuote?.shipping_cost > 0 && parseFloat(editedFreight) !== editingQuote.shipping_cost && (
                      <Text style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                        Original freight: Rs. {editingQuote.shipping_cost.toFixed(2)}
                      </Text>
                    )}
                  </View>

                  {/* Packing Type Selection */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Packing Type</Text>
                    <View style={styles.packingOptions}>
                      {[
                        { value: 'standard', label: 'Standard (1%)' },
                        { value: 'pallet', label: 'Pallet (4%)' },
                        { value: 'wooden_box', label: 'Wooden Box (8%)' },
                        { value: 'custom', label: 'Custom' }
                      ].map((option) => (
                        <TouchableOpacity
                          key={option.value}
                          style={[
                            styles.packingOption,
                            editedPackingType === option.value && styles.packingOptionActive
                          ]}
                          onPress={() => setEditedPackingType(option.value)}
                        >
                          <Ionicons 
                            name={editedPackingType === option.value ? 'radio-button-on' : 'radio-button-off'} 
                            size={20} 
                            color={editedPackingType === option.value ? '#960018' : '#666'} 
                          />
                          <Text style={[
                            styles.packingOptionText,
                            editedPackingType === option.value && styles.packingOptionTextActive
                          ]}>{option.label}</Text>
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
                    {editingQuote?.packing_type && editedPackingType !== editingQuote.packing_type && (
                      <Text style={{ color: '#666', fontSize: 12, marginTop: 8 }}>
                        Original: {editingQuote.packing_type === 'standard' ? 'Standard (1%)' :
                                   editingQuote.packing_type === 'pallet' ? 'Pallet (4%)' :
                                   editingQuote.packing_type === 'wooden_box' ? 'Wooden Box (8%)' :
                                   editingQuote.packing_type}
                      </Text>
                    )}
                  </View>

                  {/* Calculated Totals */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Summary</Text>
                    
                    {/* Subtotal (after discount) */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Subtotal</Text>
                      <Text style={styles.pricingValue}>Rs. {(calculateEditedTotal().subtotal - calculateEditedTotal().discountAmount).toFixed(2)}</Text>
                    </View>
                    
                    {/* Packing Charges with % */}
                    {calculateEditedTotal().packingCharges > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>
                          Packing Charges ({((calculateEditedTotal().packingCharges / (calculateEditedTotal().subtotal - calculateEditedTotal().discountAmount || 1)) * 100).toFixed(1)}%)
                        </Text>
                        <Text style={styles.pricingValue}>Rs. {calculateEditedTotal().packingCharges.toFixed(2)}</Text>
                      </View>
                    )}
                    
                    {/* Freight Charges */}
                    {(parseFloat(editedFreight) || 0) > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>Freight Charges</Text>
                        <Text style={styles.pricingValue}>Rs. {(parseFloat(editedFreight) || 0).toFixed(2)}</Text>
                      </View>
                    )}
                    
                    {/* Taxable Amount */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Taxable Amount</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {calculateEditedTotal().taxableAmount.toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* CGST @ 9% */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>CGST @ 9%</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {(calculateEditedTotal().taxableAmount * 0.09).toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* SGST @ 9% */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>SGST @ 9%</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {(calculateEditedTotal().taxableAmount * 0.09).toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* Grand Total */}
                    <View style={[styles.pricingRow, styles.totalRow]}>
                      <Text style={styles.totalLabel}>GRAND TOTAL</Text>
                      <Text style={styles.totalValue}>Rs. {calculateEditedTotal().total.toFixed(2)}</Text>
                    </View>
                  </View>

                  {/* Save Button */}
                  <TouchableOpacity 
                    style={styles.saveEditButton}
                    onPress={saveEditedQuote}
                    disabled={savingEdit}
                  >
                    {savingEdit ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="checkmark" size={24} color="#fff" />
                        <Text style={styles.saveEditButtonText}>Save Changes</Text>
                      </>
                    )}
                  </TouchableOpacity>
                  
                  {/* Save Changes & Mail Button - Only for Approved Quotes */}
                  {editingQuote.status?.toLowerCase() === 'approved' && (
                    <TouchableOpacity 
                      style={styles.saveRevisionButton}
                      onPress={saveRevisionAndMail}
                      disabled={savingRevision}
                    >
                      {savingRevision ? (
                        <ActivityIndicator color="#fff" />
                      ) : (
                        <>
                          <Ionicons name="mail" size={24} color="#fff" />
                          <Text style={styles.saveEditButtonText}>Save Changes & Mail</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  )}
                  
                  {/* Show current revision if exists */}
                  {editingQuote.current_revision && (
                    <Text style={styles.revisionLabel}>
                      Current Revision: {editingQuote.current_revision}
                    </Text>
                  )}
                </>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Revision History Modal */}
      <Modal
        visible={showRevisionHistory}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowRevisionHistory(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '80%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Revision History</Text>
              <TouchableOpacity onPress={() => setShowRevisionHistory(false)}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={{ flex: 1 }}>
              {revisionHistory.length === 0 ? (
                <View style={{ padding: 40, alignItems: 'center' }}>
                  <Ionicons name="time-outline" size={48} color="#ccc" />
                  <Text style={{ color: '#666', marginTop: 12, fontSize: 16, textAlign: 'center' }}>
                    No revisions yet
                  </Text>
                  <Text style={{ color: '#999', marginTop: 4, fontSize: 14, textAlign: 'center' }}>
                    Changes made to this quote will appear here
                  </Text>
                </View>
              ) : (
                revisionHistory.map((entry, index) => (
                  <View key={index} style={styles.revisionEntry}>
                    <View style={styles.revisionHeader}>
                      <View style={styles.revisionTimeline}>
                        <View style={[styles.revisionDot, index === 0 && styles.revisionDotActive]} />
                        {index < revisionHistory.length - 1 && <View style={styles.revisionLine} />}
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.revisionDate}>
                          {formatRevisionDate(entry.timestamp)}
                        </Text>
                        <Text style={styles.revisionUser}>
                          by {entry.changed_by_name || entry.changed_by}
                        </Text>
                      </View>
                      <View style={[styles.revisionActionBadge, 
                        entry.action === 'approved' && { backgroundColor: '#E8F5E9' },
                        entry.action === 'rejected' && { backgroundColor: '#FFEBEE' },
                      ]}>
                        <Text style={[styles.revisionActionText,
                          entry.action === 'approved' && { color: '#2E7D32' },
                          entry.action === 'rejected' && { color: '#C62828' },
                        ]}>
                          {entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                        </Text>
                      </View>
                    </View>
                    
                    {/* Show changes */}
                    {Object.keys(entry.changes).length > 0 && (
                      <View style={styles.revisionChanges}>
                        {Object.entries(entry.changes).map(([field, values]: [string, any], cIdx) => (
                          <View key={cIdx} style={styles.revisionChangeRow}>
                            <Text style={styles.revisionChangeLabel}>{field}:</Text>
                            <View style={styles.revisionChangeValues}>
                              {values.old && (
                                <Text style={styles.revisionOldValue}>{values.old}</Text>
                              )}
                              {values.old && values.new && (
                                <Ionicons name="arrow-forward" size={14} color="#666" style={{ marginHorizontal: 8 }} />
                              )}
                              <Text style={styles.revisionNewValue}>{values.new}</Text>
                            </View>
                          </View>
                        ))}
                      </View>
                    )}
                    
                    {/* Show summary if no detailed changes */}
                    {Object.keys(entry.changes).length === 0 && entry.summary && (
                      <Text style={styles.revisionSummary}>{entry.summary}</Text>
                    )}
                  </View>
                ))
              )}
            </ScrollView>
            
            <TouchableOpacity 
              style={styles.closeHistoryButton}
              onPress={() => setShowRevisionHistory(false)}
            >
              <Text style={styles.closeHistoryButtonText}>Close</Text>
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
    backgroundColor: '#F5F5F5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
  },
  refreshButton: {
    padding: 8,
  },
  listContainer: {
    padding: 16,
    paddingBottom: 100,
  },
  quoteCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  quoteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  quoteInfo: {
    flex: 1,
  },
  quoteId: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  quoteIdRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  rfqRefInCard: {
    fontSize: 11,
    color: '#0066cc',
    fontWeight: '500',
  },
  unreadDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#EF4444',
  },
  unreadQuoteCard: {
    borderLeftWidth: 4,
    borderLeftColor: '#EF4444',
  },
  unreadQuoteId: {
    fontWeight: '800',
  },
  quoteDate: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  productsList: {
    marginBottom: 12,
  },
  productItem: {
    fontSize: 14,
    color: '#333',
    marginBottom: 4,
  },
  moreProducts: {
    fontSize: 13,
    color: '#666',
    fontStyle: 'italic',
  },
  customerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  customerCodeBadge: {
    backgroundColor: '#960018',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  customerCodeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  customerName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  companyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  companyName: {
    fontSize: 13,
    fontWeight: '500',
    color: '#960018',
  },
  quoteFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#EEE',
  },
  totalLabel: {
    fontSize: 14,
    color: '#666',
  },
  discountBadge: {
    fontSize: 12,
    color: '#4CAF50',
    fontWeight: '600',
    marginTop: 2,
  },
  totalPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  modalContainer: {
    backgroundColor: '#fff',
    borderRadius: 16,
    width: '100%',
    maxWidth: 600,
    maxHeight: '90%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 10,
  },
  fullScreenEditContainer: {
    flex: 1,
    backgroundColor: '#fff',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 99999,
  },
  editQuoteModalContainer: {
    flex: 1,
    backgroundColor: '#fff',
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
  rfqReference: {
    fontSize: 12,
    color: '#0066cc',
    marginTop: 2,
    fontWeight: '500',
  },
  modalScroll: {
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
  deliveryText: {
    fontSize: 14,
    color: '#333',
  },
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
  notesText: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
  },
  dateText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
  },
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
  // Detail Actions Row
  detailActionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 20,
    marginBottom: 30,
  },
  editQuoteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 12,
    gap: 8,
  },
  editQuoteButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  // Edit Quote Modal Styles
  editProductRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  editProductInfo: {
    flex: 1,
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
  qtyInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  qtyLabel: {
    fontSize: 14,
    color: '#666',
  },
  qtyInput: {
    width: 70,
    backgroundColor: '#F5F5F5',
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    textAlign: 'center',
  },
  discountInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  discountInput: {
    width: 100,
    backgroundColor: '#F5F5F5',
    borderWidth: 1,
    borderColor: '#4CAF50',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 18,
    textAlign: 'center',
  },
  discountPercent: {
    fontSize: 18,
    fontWeight: '600',
    color: '#4CAF50',
  },
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
  // Filter Tabs
  filterTabs: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 12,
    backgroundColor: '#F1F5F9',
    borderRadius: 10,
    padding: 4,
  },
  filterTab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  filterTabActive: {
    backgroundColor: '#960018',
  },
  filterTabText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#64748B',
  },
  filterTabTextActive: {
    color: '#fff',
  },
  tabWithBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  unreadBadge: {
    backgroundColor: '#EF4444',
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  unreadBadgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  // Approve Button - RED (before approval)
  approveButtonRed: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#C41E3A',
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  // Approved Badge - GREEN (after approval)
  approvedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  approveButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  // Save Revision Button - Blue
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
  revisionLabel: {
    fontSize: 14,
    color: '#FF9500',
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 12,
  },
  // Attachments Section Styles
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
  productAttachments: {
    marginBottom: 12,
  },
  productAttachmentLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
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
  // Approval Success Modal Styles
  successModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  successModalContent: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 30,
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 10,
  },
  successIconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#E8F5E9',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4CAF50',
    marginBottom: 10,
    textAlign: 'center',
  },
  successMessage: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
    textAlign: 'center',
  },
  successQuoteNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
    marginBottom: 15,
    textAlign: 'center',
  },
  successSubtext: {
    fontSize: 14,
    color: '#999',
    marginBottom: 25,
    textAlign: 'center',
  },
  successButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    paddingHorizontal: 30,
    borderRadius: 10,
    width: '100%',
    marginBottom: 12,
  },
  successButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    textAlign: 'center',
  },
  successCloseButton: {
    paddingVertical: 10,
  },
  successCloseText: {
    color: '#666',
    fontSize: 14,
    fontWeight: '600',
  },
  // Search Bar Styles
  searchContainer: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  searchInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  searchIcon: {
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 15,
    color: '#0F172A',
  },
  searchClearBtn: {
    padding: 4,
  },
  searchResultCount: {
    marginTop: 8,
    fontSize: 13,
    color: '#64748B',
    textAlign: 'center',
  },
  searchResultsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  exportResultsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF5F5',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 4,
    borderWidth: 1,
    borderColor: '#960018',
  },
  exportResultsBtnText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#960018',
  },
  // Discount mode toggle styles
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
  // Bulk discount styles
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
  // Approve Modal Styles
  approveQuoteNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
    marginBottom: 4,
  },
  approveCustomerName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginBottom: 4,
  },
  approveSubtotal: {
    fontSize: 14,
    color: '#666',
  },
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
  freightInputSuffix: {
    fontSize: 18,
    fontWeight: '600',
    color: '#960018',
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
  // New styles for Edit RFQ modal
  approveCompanyName: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  editProductItem: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#960018',
  },
  editProductHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  editProductName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  editProductQty: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
  },
  editProductDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  editProductPrice: {
    fontSize: 13,
    color: '#666',
  },
  editProductTotal: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  editProductRemarks: {
    fontSize: 12,
    color: '#888',
    fontStyle: 'italic',
    marginTop: 4,
  },
  subtotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  subtotalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  subtotalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
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
  approveRejectButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20,
    marginBottom: 20,
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
  // Reject Modal styles
  rejectModalSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
    textAlign: 'center',
  },
  rejectReasonOptions: {
    gap: 12,
  },
  rejectReasonOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    gap: 12,
  },
  rejectReasonOptionActive: {
    backgroundColor: '#fff5f5',
    borderColor: '#960018',
  },
  rejectReasonText: {
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  rejectReasonTextActive: {
    color: '#960018',
    fontWeight: '600',
  },
  confirmRejectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DC3545',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    marginTop: 24,
    marginBottom: 20,
  },
  confirmRejectButtonDisabled: {
    backgroundColor: '#ccc',
  },
  confirmRejectButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  // Rejected badge style
  rejectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DC3545',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  // Field label and editable input styles
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  editableInput: {
    backgroundColor: '#f8f9fa',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  inputError: {
    borderColor: '#DC3545',
    borderWidth: 2,
  },
  errorText: {
    color: '#DC3545',
    fontSize: 12,
    marginTop: 4,
  },
  customPackingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    gap: 12,
  },
  customPackingLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
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
  // Discount section styles
  itemDiscountContainer: {
    marginTop: 12,
    gap: 10,
  },
  itemDiscountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    padding: 10,
    borderRadius: 8,
  },
  itemDiscountName: {
    flex: 1,
    fontSize: 14,
    color: '#333',
    marginRight: 12,
  },
  // Revision History styles
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
  revisionEntry: {
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  revisionHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  revisionTimeline: {
    alignItems: 'center',
    width: 20,
  },
  revisionDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#ddd',
    borderWidth: 2,
    borderColor: '#fff',
  },
  revisionDotActive: {
    backgroundColor: '#960018',
  },
  revisionLine: {
    width: 2,
    flex: 1,
    backgroundColor: '#ddd',
    marginTop: 4,
    minHeight: 40,
  },
  revisionDate: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  revisionUser: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  revisionActionBadge: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  revisionActionText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1565C0',
  },
  revisionChanges: {
    marginTop: 12,
    marginLeft: 32,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
  },
  revisionChangeRow: {
    marginBottom: 8,
  },
  revisionChangeLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    marginBottom: 4,
  },
  revisionChangeValues: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  revisionOldValue: {
    fontSize: 13,
    color: '#C62828',
    textDecorationLine: 'line-through',
  },
  revisionNewValue: {
    fontSize: 13,
    color: '#2E7D32',
    fontWeight: '500',
  },
  revisionSummary: {
    marginTop: 8,
    marginLeft: 32,
    fontSize: 13,
    color: '#666',
    fontStyle: 'italic',
  },
  closeHistoryButton: {
    backgroundColor: '#960018',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 16,
    marginHorizontal: 16,
    marginBottom: 8,
  },
  closeHistoryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
