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

interface QuoteProduct {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  specifications?: any;
  calculated_discount?: number;
}

interface Quote {
  id: string;
  quote_number?: string;
  customer_name: string;
  customer_email: string;
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
  };
  products: QuoteProduct[];
  subtotal: number;
  total_discount: number;
  packing_charges?: number;
  shipping_cost: number;
  delivery_location?: string;
  total_price: number;
  status: string;
  notes?: string;
  cost_breakdown?: any;
  pricing_details?: any;
  freight_details?: any;
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
  const [savingEdit, setSavingEdit] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    fetchQuotes();
  }, []);

  const fetchQuotes = async () => {
    try {
      const response = await api.get('/quotes');
      setQuotes(response.data);
    } catch (error: any) {
      console.error('Error fetching quotes:', error);
      Alert.alert('Error', 'Failed to load quotes');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchQuotes();
  }, []);

  // Edit quote functions
  const openEditQuote = (quote: Quote) => {
    setEditingQuote(quote);
    setEditedProducts([...quote.products]);
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

  const calculateEditedTotal = () => {
    const subtotal = editedProducts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
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
  };

  const saveEditedQuote = async () => {
    if (!editingQuote) return;
    
    setSavingEdit(true);
    try {
      const totals = calculateEditedTotal();
      const updateData = {
        products: editedProducts,
        subtotal: totals.subtotal,
        total_discount: totals.discountAmount,
        packing_charges: totals.packingCharges,
        total_price: totals.total,
      };
      
      await api.put(`/quotes/${editingQuote.id}`, updateData);
      Alert.alert('Success', 'Quote updated successfully');
      setEditingQuote(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update quote');
    } finally {
      setSavingEdit(false);
    }
  };

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
    const productsHtml = quote.products.map((product, index) => `
      <tr>
        <td style="padding: 12px; border-bottom: 1px solid #eee;">${index + 1}</td>
        <td style="padding: 12px; border-bottom: 1px solid #eee;">
          <strong>${product.product_name || product.product_id}</strong>
          ${product.specifications ? `
            <br><small style="color: #666;">
              ${product.specifications.pipe_diameter ? `Pipe: ${product.specifications.pipe_diameter}mm` : ''}
              ${product.specifications.shaft_diameter ? ` | Shaft: ${product.specifications.shaft_diameter}mm` : ''}
              ${product.specifications.bearing ? ` | Bearing: ${product.specifications.bearing}` : ''}
            </small>
          ` : ''}
        </td>
        <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">${product.quantity}</td>
        <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">Rs. ${product.unit_price?.toFixed(2)}</td>
        <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">Rs. ${(product.unit_price * product.quantity)?.toFixed(2)}</td>
      </tr>
    `).join('');

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; color: #333; }
          .header { text-align: center; margin-bottom: 30px; border-bottom: 3px solid #960018; padding-bottom: 20px; }
          .logo { font-size: 28px; font-weight: bold; color: #000; }
          .logo span { color: #960018; }
          .company-name { font-size: 12px; color: #666; margin-top: 5px; }
          .quote-title { font-size: 24px; color: #960018; margin-top: 15px; }
          .quote-info { display: flex; justify-content: space-between; margin-bottom: 20px; }
          .info-box { background: #f5f5f5; padding: 15px; border-radius: 8px; width: 48%; }
          .info-label { font-size: 12px; color: #666; }
          .info-value { font-size: 14px; font-weight: bold; margin-top: 5px; }
          table { width: 100%; border-collapse: collapse; margin: 20px 0; }
          th { background: #960018; color: white; padding: 12px; text-align: left; }
          .summary { margin-top: 30px; }
          .summary-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
          .summary-label { color: #666; }
          .summary-value { font-weight: bold; }
          .total-row { background: #960018; color: white; padding: 15px; border-radius: 8px; margin-top: 10px; }
          .total-row .summary-label, .total-row .summary-value { color: white; }
          .total-row .summary-value { font-size: 20px; }
          .footer { margin-top: 40px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }
          .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }
          .status-pending { background: #E3F2FD; color: #1976D2; }
          .status-approved { background: #E8F5E9; color: #388E3C; }
          .discount { color: #4CAF50; }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="logo">C<span>O</span>NVER<span>O</span></div>
          <div class="company-name">SOLUTIONS</div>
          <div class="quote-title">QUOTATION</div>
        </div>

        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
          <div class="info-box" style="width: 48%;">
            <div class="info-label">Quote Number</div>
            <div class="info-value" style="color: #960018;">${quote.quote_number || `#${quote.id.slice(-6).toUpperCase()}`}</div>
            <div class="info-label" style="margin-top: 10px;">Date</div>
            <div class="info-value">${quote.created_at_ist || formatDate(quote.created_at)}</div>
            <div class="info-label" style="margin-top: 10px;">Status</div>
            <div class="info-value">
              <span class="status-badge status-${quote.status?.toLowerCase()}">${quote.status?.toUpperCase()}</span>
            </div>
          </div>
          <div class="info-box" style="width: 48%;">
            <div class="info-label">Bill To</div>
            <div class="info-value">${quote.customer_details?.company || quote.customer_details?.name || quote.customer_name}</div>
            ${quote.customer_details?.address ? `
              <div style="font-size: 12px; color: #555; margin-top: 5px; line-height: 1.5;">
                ${quote.customer_details.address}${quote.customer_details.city ? `<br>${quote.customer_details.city}` : ''}${quote.customer_details.state ? `, ${quote.customer_details.state}` : ''}${quote.customer_details.pincode ? ` - ${quote.customer_details.pincode}` : ''}
              </div>
            ` : ''}
            ${quote.customer_details?.gst_number ? `
              <div style="margin-top: 8px; padding: 5px 10px; background: #E3F2FD; border-radius: 4px; display: inline-block;">
                <span style="font-size: 11px; color: #1565C0;"><strong>GSTIN:</strong> ${quote.customer_details.gst_number}</span>
              </div>
            ` : ''}
            ${quote.customer_details?.phone || quote.customer_details?.email ? `
              <div style="font-size: 11px; color: #666; margin-top: 8px;">
                ${quote.customer_details.phone ? `<span>Ph: ${quote.customer_details.phone}</span>` : ''}
                ${quote.customer_details.phone && quote.customer_details.email ? ' | ' : ''}
                ${quote.customer_details.email ? `<span>${quote.customer_details.email}</span>` : ''}
              </div>
            ` : ''}
          </div>
        </div>

        <h3 style="color: #333; border-bottom: 2px solid #960018; padding-bottom: 10px;">Products</h3>
        <table>
          <thead>
            <tr>
              <th style="width: 5%;">#</th>
              <th style="width: 40%;">Product</th>
              <th style="width: 15%; text-align: center;">Qty</th>
              <th style="width: 20%; text-align: right;">Unit Price</th>
              <th style="width: 20%; text-align: right;">Total</th>
            </tr>
          </thead>
          <tbody>
            ${productsHtml}
          </tbody>
        </table>

        <div class="summary">
          <h3 style="color: #333; border-bottom: 2px solid #960018; padding-bottom: 10px;">Summary</h3>
          <div class="summary-row">
            <span class="summary-label">Subtotal</span>
            <span class="summary-value">Rs. ${quote.subtotal?.toFixed(2)}</span>
          </div>
          ${quote.total_discount > 0 ? `
            <div class="summary-row">
              <span class="summary-label discount">Discount (${quote.subtotal > 0 ? ((quote.total_discount / quote.subtotal) * 100).toFixed(1) : 0}%)</span>
              <span class="summary-value discount">- Rs. ${quote.total_discount?.toFixed(2)}</span>
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
          <div class="summary-row" style="border-top: 1px solid #ddd; padding-top: 10px; margin-top: 10px;">
            <span class="summary-label"><strong>Taxable Amount</strong></span>
            <span class="summary-value"><strong>Rs. ${((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0)).toFixed(2)}</strong></span>
          </div>
          <div class="summary-row">
            <span class="summary-label">CGST (9%)</span>
            <span class="summary-value">Rs. ${(((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0)) * 0.09).toFixed(2)}</span>
          </div>
          <div class="summary-row">
            <span class="summary-label">SGST (9%)</span>
            <span class="summary-value">Rs. ${(((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0)) * 0.09).toFixed(2)}</span>
          </div>
          <div class="total-row" style="display: flex; justify-content: space-between;">
            <span class="summary-label">GRAND TOTAL (Incl. GST)</span>
            <span class="summary-value">Rs. ${(((quote.subtotal || 0) - (quote.total_discount || 0) + (quote.packing_charges || 0) + (quote.shipping_cost || 0)) * 1.18).toFixed(2)}</span>
          </div>
        </div>

        ${quote.delivery_location ? `
          <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px;">
            <strong>Delivery Location:</strong> Pincode ${quote.delivery_location}
          </div>
        ` : ''}

        ${quote.notes ? `
          <div style="margin-top: 20px; padding: 15px; background: #FFE4E6; border-radius: 8px;">
            <strong>Notes:</strong> ${quote.notes}
          </div>
        ` : ''}

        <div class="footer">
          <p><strong>CONVERO SOLUTIONS</strong></p>
          <p>Conveyor Roller Manufacturer</p>
          <p>www.convero.in</p>
          <p style="margin-top: 15px; font-size: 10px;">This is a computer generated quotation.</p>
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

  const renderQuote = ({ item }: { item: Quote }) => (
    <TouchableOpacity
      style={styles.quoteCard}
      onPress={() => setSelectedQuote(item)}
    >
      <View style={styles.quoteHeader}>
        <View style={styles.quoteInfo}>
          <Text style={styles.quoteId}>{item.quote_number || `Quote #${item.id.slice(-6).toUpperCase()}`}</Text>
          <Text style={styles.quoteDate}>{item.created_at_ist || formatDate(item.created_at)}</Text>
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
          <Text style={[styles.discountBadge, { color: '#4CAF50', fontWeight: 'bold' }]}>
            Discount: {item.subtotal > 0 ? ((item.total_discount / item.subtotal) * 100).toFixed(1) : 0}%
          </Text>
        </View>
        <Text style={styles.totalPrice}>Rs. {item.total_price?.toFixed(2) || '0.00'}</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading quotes...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My Quotes</Text>
        <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
          <Ionicons name="refresh" size={24} color="#960018" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={quotes}
        renderItem={renderQuote}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#960018" />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>No quotes yet</Text>
            <Text style={styles.emptySubtext}>
              Go to Calculator tab to create your first quote
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
              <Text style={styles.modalTitle}>
                {selectedQuote?.quote_number || `Quote #${selectedQuote?.id.slice(-6).toUpperCase()}`}
              </Text>
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
                          <Text style={styles.productPrice}>Rs. {(product.unit_price * product.quantity).toFixed(2)}</Text>
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
                      </View>
                    ))}
                  </View>

                  {/* Pricing Summary */}
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
                    <Text style={styles.dateText}>Created: {formatDate(selectedQuote.created_at)}</Text>
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
                  
                  {/* Edit Quote Button */}
                  <TouchableOpacity 
                    style={[styles.exportButton, { backgroundColor: '#FF9500', marginTop: 12 }]}
                    onPress={() => {
                      setSelectedQuote(null);
                      openEditQuote(selectedQuote);
                    }}
                  >
                    <Ionicons name="pencil" size={24} color="#fff" />
                    <Text style={styles.exportButtonText}>Edit Quote</Text>
                  </TouchableOpacity>
                </>
              )}
            </ScrollView>
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
              <Text style={styles.modalTitle}>Edit Quote</Text>
              <TouchableOpacity onPress={() => setEditingQuote(null)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.modalBody}>
              {editingQuote && (
                <>
                  {/* Products with editable quantity */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Products</Text>
                    {editedProducts.map((product, index) => (
                      <View key={index} style={styles.editProductRow}>
                        <View style={styles.editProductInfo}>
                          <Text style={styles.editProductName}>{product.product_name || product.product_id}</Text>
                          <Text style={styles.editProductPrice}>Rs. {product.unit_price?.toFixed(2)}/unit</Text>
                        </View>
                        <View style={styles.qtyInputContainer}>
                          <Text style={styles.qtyLabel}>Qty:</Text>
                          <TextInput
                            style={styles.qtyInput}
                            value={product.quantity.toString()}
                            onChangeText={(text) => updateProductQuantity(index, text)}
                            keyboardType="numeric"
                          />
                        </View>
                      </View>
                    ))}
                  </View>

                  {/* Editable Discount */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Discount</Text>
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

                  {/* Calculated Totals */}
                  <View style={styles.detailSection}>
                    <Text style={styles.sectionTitle}>Totals</Text>
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabel}>Subtotal</Text>
                      <Text style={styles.pricingValue}>Rs. {calculateEditedTotal().subtotal.toFixed(2)}</Text>
                    </View>
                    <View style={styles.pricingRow}>
                      <Text style={styles.pricingLabelGreen}>Discount ({editedDiscount}%)</Text>
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
    marginBottom: 8,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  customerName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
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
});
