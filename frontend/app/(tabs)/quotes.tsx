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
  approved_at?: string;
  approved_by?: string;
  created_at: string;
  created_at_ist?: string;
  updated_at: string;
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
  const [useItemDiscounts, setUseItemDiscounts] = useState(false);
  const [bulkDiscountPercent, setBulkDiscountPercent] = useState<string>('0');
  const [savingEdit, setSavingEdit] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'approved'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Approval success popup state
  const [showApprovalSuccess, setShowApprovalSuccess] = useState(false);
  const [approvedQuoteNumber, setApprovedQuoteNumber] = useState('');
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

  // Open quote detail and mark as read
  const openQuoteDetail = (quote: Quote) => {
    setSelectedQuote(quote);
    // Mark as read if admin and quote is pending RFQ and unread
    const isRfq = quote.quote_number?.startsWith('RFQ/');
    if (isAdmin && quote.status === 'pending' && isRfq && !quote.read_by_admin) {
      markAsRead(quote.id);
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
  };

  const updateProductQuantity = (index: number, newQty: string) => {
    const qty = parseInt(newQty) || 0;
    const updated = [...editedProducts];
    updated[index] = { ...updated[index], quantity: qty };
    setEditedProducts(updated);
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
      const packingCharges = editingQuote?.packing_charges || 0;
      const packingPercent = editingQuote?.subtotal > 0 ? (packingCharges / editingQuote.subtotal * 100) : 0;
      const newPacking = afterDiscount * packingPercent / 100;
      return {
        subtotal,
        discountAmount: totalItemDiscount,
        afterDiscount,
        packingCharges: newPacking,
        total: afterDiscount + newPacking + (editingQuote?.shipping_cost || 0)
      };
    } else {
      // Use total discount percentage
      subtotal = editedProducts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
      const discountAmount = (subtotal * (parseFloat(editedDiscount) || 0)) / 100;
      const afterDiscount = subtotal - discountAmount;
      const packingCharges = editingQuote?.packing_charges || 0;
      const packingPercent = editingQuote?.subtotal > 0 ? (packingCharges / editingQuote.subtotal * 100) : 0;
      const newPacking = afterDiscount * packingPercent / 100;
      return {
        subtotal,
        discountAmount,
        afterDiscount,
        packingCharges: newPacking,
        total: afterDiscount + newPacking + (editingQuote?.shipping_cost || 0)
      };
    }
  };

  const saveEditedQuote = async () => {
    if (!editingQuote) return;
    
    setSavingEdit(true);
    try {
      const totals = calculateEditedTotal();
      const updateData: any = {
        products: editedProducts,
        subtotal: totals.subtotal,
        total_discount: totals.discountAmount,
        use_item_discounts: useItemDiscounts,
        packing_charges: totals.packingCharges,
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

  // Approve RFQ function
  const approveRfq = async (quote: Quote) => {
    // Use Alert.alert for cross-platform compatibility (iOS, Android, Web)
    Alert.alert(
      'Approve RFQ',
      `Are you sure you want to approve "${quote.quote_number}" and convert it to a Quote?`,
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Approve',
          style: 'default',
          onPress: async () => {
            setApprovingId(quote.id);
            try {
              const response = await api.post(`/quotes/${quote.id}/approve`);
              // Show success popup
              setApprovedQuoteNumber(response.data.new_quote_number || quote.quote_number);
              setShowApprovalSuccess(true);
              fetchQuotes();
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to approve RFQ');
            } finally {
              setApprovingId(null);
            }
          },
        },
      ]
    );
  };

  // Filter quotes based on active tab and search query
  const getFilteredQuotes = () => {
    let filtered = quotes;
    
    // First filter by tab
    if (!isCustomer) {
      switch (activeTab) {
        case 'pending':
          filtered = filtered.filter(q => q.quote_number?.startsWith('RFQ') && q.status?.toLowerCase() !== 'approved');
          break;
        case 'approved':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'approved');
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
    const displayDate = isApproved && quote.approved_at 
      ? formatDate(quote.approved_at)
      : (quote.created_at_ist || formatDate(quote.created_at));
    
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
    
    // Dynamic table header - ALWAYS uppercase to match PDF export
    const tableHeader = useItemDiscounts ? `
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
    `;
    
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

        <!-- Summary -->
        <div class="summary-section">
          <div class="summary-table">
            <div class="summary-row">
              <span class="summary-label">Subtotal</span>
              <span class="summary-value">Rs. ${(quote.subtotal || 0).toFixed(2)}</span>
            </div>
            ${discount > 0 ? `
              <div class="summary-row discount-row">
                <span class="summary-label">${discountLabel}</span>
                <span class="summary-value">- Rs. ${discount.toFixed(2)}</span>
              </div>
            ` : ''}
            ${quote.packing_charges && quote.packing_charges > 0 ? `
              <div class="summary-row">
                <span class="summary-label">Packing Charges</span>
                <span class="summary-value">Rs. ${quote.packing_charges?.toFixed(2)}</span>
              </div>
            ` : ''}
            ${quote.shipping_cost > 0 ? `
              <div class="summary-row">
                <span class="summary-label">Freight Charges</span>
                <span class="summary-value">Rs. ${quote.shipping_cost?.toFixed(2)}</span>
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

        ${quote.delivery_location ? `
          <div class="delivery-box">
            <strong>Delivery Location:</strong> PIN Code ${quote.delivery_location}
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
    const canApprove = isAdmin && isRfq && !isApproved;
    
    // Debug log for each quote card
    console.log(`Quote ${item.quote_number}: isRfq=${isRfq}, isApproved=${isApproved}, isAdmin=${isAdmin}, canApprove=${canApprove}`);
    
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
            {isApproved && item.approved_at 
              ? formatDate(item.approved_at)
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
      
      {/* Approve Button for RFQs - RED before approval */}
      {canApprove && (
        <TouchableOpacity 
          style={styles.approveButtonRed}
          onPress={() => approveRfq(item)}
          disabled={approvingId === item.id}
        >
          {approvingId === item.id ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="checkmark-circle" size={18} color="#fff" />
              <Text style={styles.approveButtonText}>Approve & Generate Quote</Text>
            </>
          )}
        </TouchableOpacity>
      )}
      
      {/* Show Approved badge for approved quotes - GREEN */}
      {isApproved && isRfq && (
        <View style={styles.approvedBadge}>
          <Ionicons name="checkmark-circle" size={18} color="#fff" />
          <Text style={styles.approveButtonText}>Approved</Text>
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
        visible={!!selectedQuote}
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

                  {/* Products */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Products</Text>
                    {selectedQuote.products.map((product, index) => (
                      <View key={index} style={styles.productCard}>
                        <Text style={styles.productName}>{product.product_name || product.product_id}</Text>
                        <View style={styles.productDetails}>
                          <Text style={styles.productQty}>Qty: {product.quantity}</Text>
                          {/* Hide price for customers unless quote is approved */}
                          {(!isCustomer || selectedQuote.status === 'approved') && (
                            <Text style={styles.productPrice}>Rs. {(product.unit_price * product.quantity).toFixed(2)}</Text>
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
                    ))}
                  </View>

                  {/* Pricing Summary - Hidden for customers on pending RFQs */}
                  {(!isCustomer || selectedQuote.status === 'approved') && (
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Pricing Summary</Text>
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Subtotal</Text>
                      <Text style={styles.pricingValue}>Rs. {selectedQuote.subtotal?.toFixed(2)}</Text>
                    </View>
                    {selectedQuote.total_discount > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabelGreen}>
                          Discount ({selectedQuote.subtotal > 0 ? ((selectedQuote.total_discount / selectedQuote.subtotal) * 100).toFixed(1) : 0}%)
                        </Text>
                        <Text style={styles.pricingValueGreen}>- Rs. {selectedQuote.total_discount?.toFixed(2)}</Text>
                      </View>
                    )}
                    {selectedQuote.packing_charges && selectedQuote.packing_charges > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>Packing</Text>
                        <Text style={styles.pricingValue}>Rs. {selectedQuote.packing_charges?.toFixed(2)}</Text>
                      </View>
                    )}
                    {selectedQuote.shipping_cost > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>Freight</Text>
                        <Text style={styles.pricingValue}>Rs. {selectedQuote.shipping_cost?.toFixed(2)}</Text>
                      </View>
                    )}
                    
                    {/* Taxable Amount */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Taxable Amount</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0) + (selectedQuote.packing_charges || 0)).toFixed(2)}
                      </Text>
                    </View>
                    
                    {/* GST 18% */}
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>GST (18%)</Text>
                      <Text style={styles.pricingValue}>
                        Rs. {(((selectedQuote.subtotal || 0) - (selectedQuote.total_discount || 0) + (selectedQuote.packing_charges || 0)) * 0.18).toFixed(2)}
                      </Text>
                    </View>
                    
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
                      {selectedQuote.status?.toLowerCase() === 'approved' && selectedQuote.approved_at 
                        ? `Approved: ${formatDate(selectedQuote.approved_at)}`
                        : `Created: ${formatDate(selectedQuote.created_at)}`}
                    </Text>
                  </View>

                  {/* Export PDF Button */}
                  <TouchableOpacity 
                    style={styles.exportButton}
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
                  
                  {/* Edit Quote Button - Admin Only */}
                  {!isCustomer && (
                    <TouchableOpacity 
                      style={[styles.exportButton, { backgroundColor: '#FF9500', marginTop: 12 }]}
                      onPress={() => {
                        setSelectedQuote(null);
                        openEditQuote(selectedQuote);
                      }}
                    >
                      <Ionicons name="pencil" size={24} color="#fff" />
                      <Text style={styles.exportButtonText}>Edit {docLabel}</Text>
                    </TouchableOpacity>
                  )}
                </>
              )}
            </ScrollView>
          </View>
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
                                onChangeText={(text) => updateProductQuantity(index, text)}
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

                  {/* Calculated Totals */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Summary</Text>
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Subtotal</Text>
                      <Text style={styles.pricingValue}>Rs. {calculateEditedTotal().subtotal.toFixed(2)}</Text>
                    </View>
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabelGreen}>
                        {useItemDiscounts ? 'Item Discounts (Total)' : `Discount (${editedDiscount}%)`}
                      </Text>
                      <Text style={styles.pricingValueGreen}>- Rs. {calculateEditedTotal().discountAmount.toFixed(2)}</Text>
                    </View>
                    {calculateEditedTotal().packingCharges > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>Packing</Text>
                        <Text style={styles.pricingValue}>Rs. {calculateEditedTotal().packingCharges.toFixed(2)}</Text>
                      </View>
                    )}
                    {editingQuote.shipping_cost > 0 && (
                      <View style={styles.pricingRow}>
                        <Text style={styles.pricingLabel}>Shipping</Text>
                        <Text style={styles.pricingValue}>Rs. {editingQuote.shipping_cost.toFixed(2)}</Text>
                      </View>
                    )}
                    <View style={[styles.pricingRow, styles.totalRow]}>
                      <Text style={styles.totalLabel}>Total</Text>
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
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
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
    marginTop: 20,
    marginBottom: 30,
    gap: 10,
  },
  exportButtonText: {
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
});
