import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  Modal,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

interface Customer {
  id: string;
  name: string;
  company?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  gst_number?: string;
  notes?: string;
  customer_type?: string;
}

interface Quote {
  id: string;
  quote_number: string;
  status: string;
  total_price: number;
  created_at: string;
  products?: any[];
}

interface GSTCaptcha {
  session_id: string;
  captcha_image: string;
}

interface GSTData {
  gstin: string;
  legal_name: string;
  trade_name: string;
  status: string;
  address: {
    full: string;
    street: string;
    city: string;
    state: string;
    pincode: string;
  };
  registration_date: string;
  constitution_of_business: string;
  taxpayer_type: string;
}

const emptyCustomer: Omit<Customer, 'id'> = {
  name: '',
  company: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  state: '',
  pincode: '',
  gst_number: '',
  notes: '',
};

export default function CustomersScreen() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [formData, setFormData] = useState<Omit<Customer, 'id'>>(emptyCustomer);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'registered' | 'quoted'>('all');
  
  // Customer Quotes Modal state
  const [quotesModalVisible, setQuotesModalVisible] = useState(false);
  const [selectedCustomerForQuotes, setSelectedCustomerForQuotes] = useState<Customer | null>(null);
  const [customerQuotes, setCustomerQuotes] = useState<Quote[]>([]);
  const [quotesLoading, setQuotesLoading] = useState(false);
  
  // GST Lookup state
  const [gstModalVisible, setGstModalVisible] = useState(false);
  const [gstinInput, setGstinInput] = useState('');
  const [captchaData, setCaptchaData] = useState<GSTCaptcha | null>(null);
  const [captchaInput, setCaptchaInput] = useState('');
  const [gstLoading, setGstLoading] = useState(false);
  const [gstVerifying, setGstVerifying] = useState(false);

  useEffect(() => {
    fetchCustomers();
  }, [filterType]);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      const params = filterType !== 'all' ? `?customer_type=${filterType}` : '';
      const response = await api.get(`/customers${params}`);
      setCustomers(response.data.customers || []);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch customers');
    } finally {
      setLoading(false);
    }
  };

  const fetchCustomerQuotes = async (customer: Customer) => {
    setSelectedCustomerForQuotes(customer);
    setQuotesModalVisible(true);
    setQuotesLoading(true);
    
    try {
      const response = await api.get(`/customers/${customer.id}/quotes`);
      setCustomerQuotes(response.data.quotes || []);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch customer quotes');
      setCustomerQuotes([]);
    } finally {
      setQuotesLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      Alert.alert('Error', 'Customer name is required');
      return;
    }

    try {
      setSaving(true);
      if (editingCustomer) {
        await api.put(`/customers/${editingCustomer.id}`, formData);
        Alert.alert('Success', 'Customer updated successfully');
      } else {
        await api.post('/customers', formData);
        Alert.alert('Success', 'Customer created successfully');
      }
      setModalVisible(false);
      setEditingCustomer(null);
      setFormData(emptyCustomer);
      fetchCustomers();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save customer');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (customer: Customer) => {
    setEditingCustomer(customer);
    setFormData({
      name: customer.name,
      company: customer.company || '',
      email: customer.email || '',
      phone: customer.phone || '',
      address: customer.address || '',
      city: customer.city || '',
      state: customer.state || '',
      pincode: customer.pincode || '',
      gst_number: customer.gst_number || '',
      notes: customer.notes || '',
    });
    setModalVisible(true);
  };

  const handleDelete = (customer: Customer) => {
    Alert.alert(
      'Delete Customer',
      `Are you sure you want to delete "${customer.name}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`/customers/${customer.id}`);
              fetchCustomers();
              Alert.alert('Success', 'Customer deleted');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to delete');
            }
          },
        },
      ]
    );
  };

  const handleAddNew = () => {
    setEditingCustomer(null);
    setFormData(emptyCustomer);
    setModalVisible(true);
  };

  // State for existing customer found by GSTIN
  const [existingGstCustomer, setExistingGstCustomer] = useState<Customer | null>(null);
  const [searchingGstin, setSearchingGstin] = useState(false);

  // GST Lookup functions
  const openGstLookup = () => {
    setGstinInput('');
    setCaptchaData(null);
    setCaptchaInput('');
    setExistingGstCustomer(null);
    setGstModalVisible(true);
  };

  // Quick search by GSTIN - check database first
  const searchGstinInDatabase = async (gstin: string) => {
    if (gstin.length !== 15) {
      setExistingGstCustomer(null);
      return;
    }
    
    setSearchingGstin(true);
    try {
      const response = await api.get(`/customers/search/gstin/${gstin.toUpperCase()}`);
      if (response.data.found) {
        setExistingGstCustomer(response.data.customer);
      } else {
        setExistingGstCustomer(null);
      }
    } catch (error) {
      setExistingGstCustomer(null);
    } finally {
      setSearchingGstin(false);
    }
  };

  // Handle GSTIN input change with search
  const handleGstinInputChange = (text: string) => {
    const upperText = text.toUpperCase();
    setGstinInput(upperText);
    if (upperText.length === 15) {
      searchGstinInDatabase(upperText);
    } else {
      setExistingGstCustomer(null);
    }
  };

  // Open existing customer for editing
  const editExistingGstCustomer = () => {
    if (existingGstCustomer) {
      setEditingCustomer(existingGstCustomer);
      setFormData({
        name: existingGstCustomer.name,
        company: existingGstCustomer.company || '',
        email: existingGstCustomer.email || '',
        phone: existingGstCustomer.phone || '',
        address: existingGstCustomer.address || '',
        city: existingGstCustomer.city || '',
        state: existingGstCustomer.state || '',
        pincode: existingGstCustomer.pincode || '',
        gst_number: existingGstCustomer.gst_number || '',
        notes: existingGstCustomer.notes || '',
      });
      setGstModalVisible(false);
      setModalVisible(true);
    }
  };

  const fetchCaptcha = async () => {
    setGstLoading(true);
    try {
      const response = await api.get('/gst/captcha');
      if (response.data.success) {
        setCaptchaData({
          session_id: response.data.session_id,
          captcha_image: response.data.captcha_image,
        });
      } else {
        Alert.alert('Error', response.data.error || 'Failed to fetch captcha');
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch captcha from GST portal');
    } finally {
      setGstLoading(false);
    }
  };

  const verifyGstin = async () => {
    if (!gstinInput || gstinInput.length !== 15) {
      Alert.alert('Error', 'Please enter a valid 15-character GSTIN');
      return;
    }
    if (!captchaInput) {
      Alert.alert('Error', 'Please enter the captcha');
      return;
    }
    if (!captchaData?.session_id) {
      Alert.alert('Error', 'Session expired. Please refresh captcha.');
      return;
    }

    setGstVerifying(true);
    try {
      const response = await api.post('/gst/verify', {
        session_id: captchaData.session_id,
        gstin: gstinInput.toUpperCase(),
        captcha: captchaInput,
      });

      if (response.data.success) {
        const gstData = response.data.data;
        // Fill form with GST data
        setFormData({
          name: gstData.trade_name || gstData.legal_name || '',
          company: gstData.legal_name || '',
          email: '',
          phone: '',
          address: gstData.address?.full || gstData.address?.street || '',
          city: gstData.address?.city || '',
          state: gstData.address?.state || '',
          pincode: gstData.address?.pincode || '',
          gst_number: gstData.gstin || gstinInput.toUpperCase(),
          notes: `Status: ${gstData.status}. Type: ${gstData.taxpayer_type}. Reg: ${gstData.registration_date}`,
        });
        setGstModalVisible(false);
        setModalVisible(true);
        Alert.alert('Success', 'GST details fetched! Please review and save.');
      }
    } catch (error: any) {
      Alert.alert('Verification Failed', error.response?.data?.detail || 'Invalid GSTIN or captcha. Please try again.');
      // Refresh captcha on failure
      fetchCaptcha();
      setCaptchaInput('');
    } finally {
      setGstVerifying(false);
    }
  };

  const filteredCustomers = customers.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.company?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.phone?.includes(searchQuery)
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading customers...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Customers</Text>
        <Text style={styles.headerSubtitle}>{customers.length} customers</Text>
      </View>

      <View style={styles.searchContainer}>
        <Ionicons name="search" size={20} color="#666" />
        <TextInput
          style={styles.searchInput}
          placeholder="Search customers..."
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Ionicons name="close-circle" size={20} color="#666" />
          </TouchableOpacity>
        )}
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterContainer}>
        <TouchableOpacity
          style={[styles.filterTab, filterType === 'all' && styles.filterTabActive]}
          onPress={() => setFilterType('all')}
        >
          <Text style={[styles.filterTabText, filterType === 'all' && styles.filterTabTextActive]}>
            All
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterTab, filterType === 'registered' && styles.filterTabActive]}
          onPress={() => setFilterType('registered')}
        >
          <Ionicons 
            name="person-add-outline" 
            size={16} 
            color={filterType === 'registered' ? '#FFFFFF' : '#64748B'} 
          />
          <Text style={[styles.filterTabText, filterType === 'registered' && styles.filterTabTextActive]}>
            Registered
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterTab, filterType === 'quoted' && styles.filterTabActive]}
          onPress={() => setFilterType('quoted')}
        >
          <Ionicons 
            name="document-text-outline" 
            size={16} 
            color={filterType === 'quoted' ? '#FFFFFF' : '#64748B'} 
          />
          <Text style={[styles.filterTabText, filterType === 'quoted' && styles.filterTabTextActive]}>
            Quoted
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {filteredCustomers.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="people-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>No customers found</Text>
            <Text style={styles.emptySubtext}>Add your first customer</Text>
          </View>
        ) : (
          filteredCustomers.map((customer) => (
            <View key={customer.id} style={styles.customerCard}>
              <TouchableOpacity 
                style={styles.customerInfo}
                onPress={() => customer.customer_type === 'quoted' ? fetchCustomerQuotes(customer) : null}
                activeOpacity={customer.customer_type === 'quoted' ? 0.7 : 1}
              >
                <View style={styles.customerHeader}>
                  <Text style={styles.customerName}>{customer.name}</Text>
                  {customer.customer_type === 'quoted' && (
                    <View style={styles.quotedBadge}>
                      <Ionicons name="checkmark-circle" size={12} color="#4CAF50" />
                      <Text style={styles.quotedBadgeText}>Quoted</Text>
                    </View>
                  )}
                </View>
                {customer.company && (
                  <Text style={styles.customerCompany}>{customer.company}</Text>
                )}
                {customer.phone && (
                  <View style={styles.infoRow}>
                    <Ionicons name="call-outline" size={14} color="#666" />
                    <Text style={styles.infoText}>{customer.phone}</Text>
                  </View>
                )}
                {customer.email && (
                  <View style={styles.infoRow}>
                    <Ionicons name="mail-outline" size={14} color="#666" />
                    <Text style={styles.infoText}>{customer.email}</Text>
                  </View>
                )}
                {customer.city && (
                  <View style={styles.infoRow}>
                    <Ionicons name="location-outline" size={14} color="#666" />
                    <Text style={styles.infoText}>
                      {customer.city}{customer.state ? `, ${customer.state}` : ''}
                    </Text>
                  </View>
                )}
                {customer.gst_number && (
                  <View style={styles.infoRow}>
                    <Ionicons name="document-text-outline" size={14} color="#666" />
                    <Text style={styles.infoText}>GST: {customer.gst_number}</Text>
                  </View>
                )}
                {customer.customer_type === 'quoted' && (
                  <TouchableOpacity 
                    style={styles.viewQuotesBtn}
                    onPress={() => fetchCustomerQuotes(customer)}
                  >
                    <Ionicons name="document-text" size={16} color="#960018" />
                    <Text style={styles.viewQuotesBtnText}>View Quotes</Text>
                  </TouchableOpacity>
                )}
              </TouchableOpacity>
              <View style={styles.customerActions}>
                <TouchableOpacity
                  style={styles.actionBtn}
                  onPress={() => handleEdit(customer)}
                >
                  <Ionicons name="pencil" size={18} color="#960018" />
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.actionBtn}
                  onPress={() => handleDelete(customer)}
                >
                  <Ionicons name="trash-outline" size={18} color="#C41E3A" />
                </TouchableOpacity>
              </View>
            </View>
          ))
        )}
        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* Floating Action Buttons */}
      <View style={styles.fabContainer}>
        <TouchableOpacity style={styles.fabSecondary} onPress={openGstLookup}>
          <Ionicons name="search" size={22} color="#fff" />
          <Text style={styles.fabSecondaryText}>GST</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.fab} onPress={handleAddNew}>
          <Ionicons name="add" size={28} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* GST Lookup Modal */}
      <Modal
        visible={gstModalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setGstModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setGstModalVisible(false)}>
              <Text style={styles.cancelBtn}>Cancel</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>Fetch from GSTIN</Text>
            <View style={{ width: 50 }} />
          </View>

          <ScrollView style={styles.modalContent}>
            <View style={styles.gstInfoBox}>
              <Ionicons name="information-circle-outline" size={20} color="#960018" />
              <Text style={styles.gstInfoText}>
                Enter GSTIN to find existing customer or fetch from GST portal
              </Text>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>GSTIN (15 characters)</Text>
              <View style={styles.gstInputRow}>
                <TextInput
                  style={[styles.input, { flex: 1, marginBottom: 0 }]}
                  value={gstinInput}
                  onChangeText={handleGstinInputChange}
                  placeholder="e.g., 27AAACE8661R1Z5"
                  maxLength={15}
                  autoCapitalize="characters"
                />
                {searchingGstin && (
                  <ActivityIndicator size="small" color="#960018" style={{ marginLeft: 10 }} />
                )}
              </View>
            </View>

            {/* Show existing customer if found */}
            {existingGstCustomer && (
              <View style={styles.existingCustomerCard}>
                <View style={styles.existingCustomerHeader}>
                  <Ionicons name="checkmark-circle" size={20} color="#2E7D32" />
                  <Text style={styles.existingCustomerLabel}>Customer Found!</Text>
                </View>
                <View style={styles.existingCustomerInfo}>
                  <Text style={styles.existingCustomerName}>{existingGstCustomer.name}</Text>
                  {existingGstCustomer.company && (
                    <Text style={styles.existingCustomerCompany}>{existingGstCustomer.company}</Text>
                  )}
                  {existingGstCustomer.city && (
                    <Text style={styles.existingCustomerLocation}>
                      {existingGstCustomer.city}{existingGstCustomer.state ? `, ${existingGstCustomer.state}` : ''}
                    </Text>
                  )}
                </View>
                <TouchableOpacity style={styles.selectExistingBtn} onPress={editExistingGstCustomer}>
                  <Ionicons name="create" size={18} color="#fff" />
                  <Text style={styles.selectExistingBtnText}>View / Edit Customer</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* Show add new customer option if GSTIN not found */}
            {!existingGstCustomer && gstinInput.length === 15 && !searchingGstin && (
              <View style={styles.newCustomerSection}>
                <View style={styles.notFoundHeader}>
                  <Ionicons name="alert-circle-outline" size={20} color="#F57C00" />
                  <Text style={styles.newCustomerLabel}>Customer not found in database</Text>
                </View>
                <Text style={styles.notFoundHint}>
                  Click below to add this customer manually with GSTIN pre-filled.
                </Text>
                <TouchableOpacity 
                  style={styles.addManuallyBtn}
                  onPress={() => {
                    setFormData({
                      ...emptyCustomer,
                      gst_number: gstinInput,
                    });
                    setGstModalVisible(false);
                    setModalVisible(true);
                  }}
                >
                  <Ionicons name="add-circle" size={20} color="#fff" />
                  <Text style={styles.addManuallyBtnText}>Add Customer Manually</Text>
                </TouchableOpacity>
              </View>
            )}

            {gstinInput.length > 0 && gstinInput.length < 15 && (
              <Text style={styles.gstHintText}>
                {15 - gstinInput.length} more characters needed
              </Text>
            )}

            <View style={styles.gstHelpBox}>
              <Text style={styles.gstHelpTitle}>What is GSTIN?</Text>
              <Text style={styles.gstHelpText}>
                GSTIN is a 15-digit unique identification number assigned to GST registered businesses in India.
                Example: 27AAACE8661R1Z5
              </Text>
            </View>
          </ScrollView>
        </View>
      </Modal>

      {/* Add/Edit Customer Modal */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <Text style={styles.cancelBtn}>Cancel</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>
              {editingCustomer ? 'Edit Customer' : 'New Customer'}
            </Text>
            <TouchableOpacity onPress={handleSave} disabled={saving}>
              <Text style={[styles.saveBtn, saving && styles.saveBtnDisabled]}>
                {saving ? 'Saving...' : 'Save'}
              </Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalContent}>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Name *</Text>
              <TextInput
                style={styles.input}
                value={formData.name}
                onChangeText={(text) => setFormData({ ...formData, name: text })}
                placeholder="Customer name"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Company</Text>
              <TextInput
                style={styles.input}
                value={formData.company}
                onChangeText={(text) => setFormData({ ...formData, company: text })}
                placeholder="Company name"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Phone</Text>
              <TextInput
                style={styles.input}
                value={formData.phone}
                onChangeText={(text) => setFormData({ ...formData, phone: text })}
                placeholder="Phone number"
                keyboardType="phone-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Email</Text>
              <TextInput
                style={styles.input}
                value={formData.email}
                onChangeText={(text) => setFormData({ ...formData, email: text })}
                placeholder="Email address"
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Address</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={formData.address}
                onChangeText={(text) => setFormData({ ...formData, address: text })}
                placeholder="Street address"
                multiline
                numberOfLines={2}
              />
            </View>

            <View style={styles.row}>
              <View style={[styles.inputGroup, { flex: 1, marginRight: 8 }]}>
                <Text style={styles.inputLabel}>City</Text>
                <TextInput
                  style={styles.input}
                  value={formData.city}
                  onChangeText={(text) => setFormData({ ...formData, city: text })}
                  placeholder="City"
                />
              </View>
              <View style={[styles.inputGroup, { flex: 1, marginLeft: 8 }]}>
                <Text style={styles.inputLabel}>State</Text>
                <TextInput
                  style={styles.input}
                  value={formData.state}
                  onChangeText={(text) => setFormData({ ...formData, state: text })}
                  placeholder="State"
                />
              </View>
            </View>

            <View style={styles.row}>
              <View style={[styles.inputGroup, { flex: 1, marginRight: 8 }]}>
                <Text style={styles.inputLabel}>Pincode</Text>
                <TextInput
                  style={styles.input}
                  value={formData.pincode}
                  onChangeText={(text) => setFormData({ ...formData, pincode: text })}
                  placeholder="Pincode"
                  keyboardType="numeric"
                  maxLength={6}
                />
              </View>
              <View style={[styles.inputGroup, { flex: 1, marginLeft: 8 }]}>
                <Text style={styles.inputLabel}>GST Number</Text>
                <TextInput
                  style={styles.input}
                  value={formData.gst_number}
                  onChangeText={(text) => setFormData({ ...formData, gst_number: text.toUpperCase() })}
                  placeholder="GST Number"
                  autoCapitalize="characters"
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Notes</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={formData.notes}
                onChangeText={(text) => setFormData({ ...formData, notes: text })}
                placeholder="Additional notes"
                multiline
                numberOfLines={3}
              />
            </View>

            <View style={styles.modalBottomSpacer} />
          </ScrollView>
        </View>
      </Modal>

      {/* Customer Quotes Modal */}
      <Modal
        visible={quotesModalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setQuotesModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setQuotesModalVisible(false)}>
              <Text style={styles.cancelBtn}>Close</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>Customer Quotes</Text>
            <View style={{ width: 50 }} />
          </View>

          <ScrollView style={styles.modalContent}>
            {selectedCustomerForQuotes && (
              <View style={styles.customerQuotesHeader}>
                <Text style={styles.customerQuotesName}>{selectedCustomerForQuotes.name}</Text>
                {selectedCustomerForQuotes.company && (
                  <Text style={styles.customerQuotesCompany}>{selectedCustomerForQuotes.company}</Text>
                )}
              </View>
            )}

            {quotesLoading ? (
              <View style={styles.quotesLoadingContainer}>
                <ActivityIndicator size="large" color="#960018" />
                <Text style={styles.quotesLoadingText}>Loading quotes...</Text>
              </View>
            ) : customerQuotes.length === 0 ? (
              <View style={styles.noQuotesContainer}>
                <Ionicons name="document-text-outline" size={48} color="#ccc" />
                <Text style={styles.noQuotesText}>No quotes found for this customer</Text>
              </View>
            ) : (
              customerQuotes.map((quote) => (
                <View key={quote.id} style={styles.quoteCard}>
                  <View style={styles.quoteCardHeader}>
                    <Text style={styles.quoteNumber}>{quote.quote_number}</Text>
                    <View style={[
                      styles.quoteStatusBadge,
                      quote.status === 'approved' ? styles.quoteStatusApproved : styles.quoteStatusPending
                    ]}>
                      <Text style={[
                        styles.quoteStatusText,
                        quote.status === 'approved' ? styles.quoteStatusTextApproved : styles.quoteStatusTextPending
                      ]}>
                        {quote.status === 'approved' ? 'Approved' : 'Pending'}
                      </Text>
                    </View>
                  </View>
                  <View style={styles.quoteCardBody}>
                    <View style={styles.quoteDetail}>
                      <Text style={styles.quoteDetailLabel}>Amount</Text>
                      <Text style={styles.quoteDetailValue}>{formatCurrency(quote.total_price || 0)}</Text>
                    </View>
                    <View style={styles.quoteDetail}>
                      <Text style={styles.quoteDetailLabel}>Date</Text>
                      <Text style={styles.quoteDetailValue}>{formatDate(quote.created_at)}</Text>
                    </View>
                    <View style={styles.quoteDetail}>
                      <Text style={styles.quoteDetailLabel}>Items</Text>
                      <Text style={styles.quoteDetailValue}>{quote.products?.length || 0} products</Text>
                    </View>
                  </View>
                </View>
              ))
            )}

            <View style={styles.modalBottomSpacer} />
          </ScrollView>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  header: {
    backgroundColor: '#960018',
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 4,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 16,
    paddingHorizontal: 12,
    borderRadius: 10,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 16,
  },
  content: {
    flex: 1,
    paddingHorizontal: 16,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  customerCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  customerInfo: {
    flex: 1,
  },
  customerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  customerCompany: {
    fontSize: 14,
    color: '#960018',
    marginTop: 2,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    gap: 6,
  },
  infoText: {
    fontSize: 13,
    color: '#666',
  },
  customerActions: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  actionBtn: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#f5f5f5',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#960018',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  bottomSpacer: {
    height: 100,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingTop: 60,
    paddingBottom: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#333',
  },
  cancelBtn: {
    fontSize: 16,
    color: '#666',
  },
  saveBtn: {
    fontSize: 16,
    fontWeight: '600',
    color: '#960018',
  },
  saveBtnDisabled: {
    opacity: 0.5,
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: '#666',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#E5E5EA',
  },
  textArea: {
    minHeight: 60,
    textAlignVertical: 'top',
  },
  row: {
    flexDirection: 'row',
  },
  modalBottomSpacer: {
    height: 40,
  },
  fabContainer: {
    position: 'absolute',
    right: 20,
    bottom: 30,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  fabSecondary: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#960018',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 25,
    gap: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  fabSecondaryText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  gstInfoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF5F6',
    padding: 12,
    borderRadius: 8,
    marginBottom: 20,
    gap: 10,
    borderWidth: 1,
    borderColor: '#FFD0D6',
  },
  gstInfoText: {
    flex: 1,
    fontSize: 13,
    color: '#333',
    lineHeight: 18,
  },
  captchaLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 30,
    gap: 10,
  },
  captchaLoadingText: {
    fontSize: 14,
    color: '#666',
  },
  captchaSection: {
    marginBottom: 16,
  },
  captchaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E5EA',
    padding: 10,
    marginBottom: 12,
    gap: 10,
  },
  captchaImage: {
    flex: 1,
    height: 60,
    backgroundColor: '#f5f5f5',
    borderRadius: 4,
  },
  refreshCaptchaBtn: {
    padding: 8,
  },
  loadCaptchaBtn: {
    backgroundColor: '#f5f5f5',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  loadCaptchaBtnText: {
    color: '#960018',
    fontSize: 14,
    fontWeight: '600',
  },
  verifyBtn: {
    backgroundColor: '#960018',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    marginTop: 8,
    marginBottom: 24,
  },
  verifyBtnDisabled: {
    opacity: 0.5,
  },
  verifyBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  gstHelpBox: {
    backgroundColor: '#f0f0f0',
    padding: 16,
    borderRadius: 8,
    marginTop: 16,
  },
  gstHelpTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  gstHelpText: {
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
  },
  gstInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  existingCustomerCard: {
    backgroundColor: '#E8F5E9',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#A5D6A7',
  },
  existingCustomerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  existingCustomerLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2E7D32',
  },
  existingCustomerInfo: {
    marginBottom: 12,
  },
  existingCustomerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  existingCustomerCompany: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  existingCustomerLocation: {
    fontSize: 13,
    color: '#888',
    marginTop: 2,
  },
  selectExistingBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2E7D32',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  selectExistingBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  newCustomerSection: {
    backgroundColor: '#FFF8E1',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#FFE082',
  },
  newCustomerLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: '#F57C00',
    marginBottom: 12,
  },
  gstHintText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
    marginBottom: 16,
  },
  notFoundHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  notFoundHint: {
    fontSize: 13,
    color: '#666',
    marginBottom: 16,
    lineHeight: 18,
  },
  addManuallyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    padding: 14,
    borderRadius: 10,
    gap: 8,
  },
  addManuallyBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#FFFFFF',
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  filterTab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#F1F5F9',
    gap: 6,
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
    color: '#FFFFFF',
  },
  // Customer Header with Badge
  customerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  quotedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    gap: 4,
  },
  quotedBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#4CAF50',
  },
  viewQuotesBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
    gap: 6,
    backgroundColor: '#FFF5F5',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  viewQuotesBtnText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#960018',
  },
  // Customer Quotes Modal Styles
  customerQuotesHeader: {
    backgroundColor: '#F8FAFC',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  customerQuotesName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
  },
  customerQuotesCompany: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 4,
  },
  quotesLoadingContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  quotesLoadingText: {
    marginTop: 16,
    fontSize: 14,
    color: '#64748B',
  },
  noQuotesContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  noQuotesText: {
    marginTop: 16,
    fontSize: 16,
    color: '#94A3B8',
  },
  quoteCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  quoteCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  quoteNumber: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  quoteStatusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  quoteStatusApproved: {
    backgroundColor: '#DCFCE7',
  },
  quoteStatusPending: {
    backgroundColor: '#FEF3C7',
  },
  quoteStatusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  quoteStatusTextApproved: {
    color: '#4CAF50',
  },
  quoteStatusTextPending: {
    color: '#F59E0B',
  },
  quoteCardBody: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  quoteDetail: {
    flex: 1,
  },
  quoteDetailLabel: {
    fontSize: 11,
    color: '#94A3B8',
    marginBottom: 2,
  },
  quoteDetailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
});
