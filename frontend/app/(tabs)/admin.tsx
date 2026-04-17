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
  FlatList,
  Platform,
  Pressable,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '../../contexts/AuthContext';
import api, { cacheEvents } from '../../utils/api';

type MainTab = 'prices' | 'standards' | 'history' | 'users';
type PriceCategory = 'basic' | 'bearing' | 'housing' | 'seal' | 'circlip' | 'rubber' | 'locking';

interface Prices {
  basic_rates: {
    pipe_cost_per_kg: number;
    shaft_cost_per_kg: number;
  };
  bearing_costs: Record<string, Record<string, number>>;
  housing_costs: Record<string, number>;
  seal_costs: Record<string, number>;
  circlip_costs: Record<string, number>;
  rubber_ring_costs: Record<string, number>;
  locking_ring_costs: Record<string, number>;
}

interface StandardsCollection {
  collection: string;
  count: number;
}

interface StandardItem {
  [key: string]: any;
}

const COLLECTION_LABELS: Record<string, string> = {
  pipe_diameters: 'Pipe Diameters',
  shaft_diameters: 'Shaft Diameters',
  shaft_end_types: 'Shaft End Types',
  bearings: 'Bearings',
  housings: 'Housings',
  pipe_weights: 'Pipe Weights',
  roller_lengths: 'Roller Lengths',
  circlips: 'Circlips',
  rubber_lagging: 'Rubber Lagging',
  rubber_rings: 'Rubber Rings',
  locking_rings: 'Locking Rings',
  discount_slabs: 'Discount Slabs',
  freight_rates: 'Freight Rates',
  packing_options: 'Packing Options',
  gst_config: 'GST Config',
  raw_material_costs: 'Raw Materials',
};

export default function AdminScreen() {
  const { user } = useAuth();
  const [mainTab, setMainTab] = useState<MainTab>('prices');
  const [productType, setProductType] = useState<'roller' | 'pulley'>('roller');
  
  // Prices state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [prices, setPrices] = useState<Prices | null>(null);
  const [pulleyStandards, setPulleyStandards] = useState<any>(null);
  const [activeCategory, setActiveCategory] = useState<PriceCategory>('basic');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [refreshKey, setRefreshKey] = useState(0); // Force re-render after reset

  // Pulley price editing state
  const [pulleyEditKey, setPulleyEditKey] = useState<string | null>(null);
  const [pulleyEditValue, setPulleyEditValue] = useState('');
  const [pulleySaving, setPulleySaving] = useState(false);

  // Pulley bulk-edit state
  const [pulleyBulkMode, setPulleyBulkMode] = useState(false);
  const [pulleyBulkDraft, setPulleyBulkDraft] = useState<any>(null);

  // Price history state
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [historyFilter, setHistoryFilter] = useState<'all' | 'roller' | 'pulley'>('all');
  const [historyLoading, setHistoryLoading] = useState(false);

  // Users management state
  const [users, setUsers] = useState<any[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [assignableRoles, setAssignableRoles] = useState<string[]>([]);
  const [rolePickerEmail, setRolePickerEmail] = useState<string | null>(null);

  // Create user modal state
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState('sales_manager');
  const [newUserCompany, setNewUserCompany] = useState('');
  const [creatingUser, setCreatingUser] = useState(false);
  
  // Set as Default OTP state
  const [showSetDefaultModal, setShowSetDefaultModal] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otpValue, setOtpValue] = useState('');
  const [sendingOtp, setSendingOtp] = useState(false);
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [otpEmail, setOtpEmail] = useState('');
  
  // Standards state
  const [standardsSummary, setStandardsSummary] = useState<StandardsCollection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [collectionData, setCollectionData] = useState<StandardItem[]>([]);
  const [loadingStandards, setLoadingStandards] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<StandardItem | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<StandardItem | null>(null);
  const [editFormData, setEditFormData] = useState<Record<string, string>>({});
  const [savingStandard, setSavingStandard] = useState(false);

  // Pull-to-refresh state
  const [refreshing, setRefreshing] = useState(false);

  // Pull-to-refresh handler
  const onRefresh = async () => {
    setRefreshing(true);
    try {
      if (mainTab === 'prices') {
        if (productType === 'pulley') await fetchPulleyPricing();
        else await fetchPrices();
      } else {
        await fetchStandardsSummary();
      }
    } finally {
      setRefreshing(false);
    }
  };

  const fetchPulleyPricing = async () => {
    try {
      const response = await api.get('/pulley-pricing');
      setPulleyStandards(response.data);
    } catch (error) {
      console.error('Error fetching pulley pricing:', error);
    }
  };

  // ============= PULLEY PRICE EDIT HELPERS =============
  const startPulleyEdit = (editKey: string, value: number) => {
    setPulleyEditKey(editKey);
    setPulleyEditValue(String(value));
  };

  const cancelPulleyEdit = () => {
    setPulleyEditKey(null);
    setPulleyEditValue('');
  };

  // Set nested value immutably using path like ['pipe_rates', '219', '6']
  const setNestedPath = (obj: any, path: string[], value: any): any => {
    const copy: any = Array.isArray(obj) ? [...obj] : { ...(obj || {}) };
    if (path.length === 1) {
      copy[path[0]] = value;
      return copy;
    }
    copy[path[0]] = setNestedPath(copy[path[0]] || {}, path.slice(1), value);
    return copy;
  };

  const savePulleyEdit = async (path: string[]) => {
    const num = parseFloat(pulleyEditValue);
    if (isNaN(num) || num < 0) {
      Alert.alert('Invalid Value', 'Please enter a valid positive number');
      return;
    }
    try {
      setPulleySaving(true);
      const updated = setNestedPath(pulleyStandards || {}, path, num);
      // Strip mongo id if present
      if (updated._id) delete updated._id;
      if (updated.id) delete updated.id;
      await api.put('/pulley-pricing', updated);
      await fetchPulleyPricing();
      setPulleyEditKey(null);
      setPulleyEditValue('');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update pulley price');
    } finally {
      setPulleySaving(false);
    }
  };

  const handleResetPulleyPrices = () => {
    Alert.alert(
      'Reset Pulley Prices',
      'Reset all pulley prices to default values?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            try {
              setPulleySaving(true);
              await api.post('/pulley-pricing/reset');
              await fetchPulleyPricing();
              Alert.alert('Success', 'Pulley prices reset to default');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to reset');
            } finally {
              setPulleySaving(false);
            }
          },
        },
      ]
    );
  };

  const handleSetDefaultPulleyPrices = () => {
    Alert.alert(
      'Set as Default',
      'Save current pulley prices as the new default?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm',
          onPress: async () => {
            try {
              setPulleySaving(true);
              await api.post('/pulley-pricing/set-default');
              Alert.alert('Success', 'Current pulley prices saved as default');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to set default');
            } finally {
              setPulleySaving(false);
            }
          },
        },
      ]
    );
  };

  // ============= PULLEY BULK EDIT =============
  const enterBulkEdit = () => {
    if (!pulleyStandards) return;
    // Deep clone the current prices into draft (strip meta fields)
    const draft = JSON.parse(JSON.stringify(pulleyStandards));
    delete draft._id;
    delete draft.id;
    setPulleyBulkDraft(draft);
    setPulleyBulkMode(true);
  };

  const cancelBulkEdit = () => {
    setPulleyBulkMode(false);
    setPulleyBulkDraft(null);
  };

  const updateBulkValue = (path: string[], value: string) => {
    setPulleyBulkDraft((prev: any) => setNestedPath(prev || {}, path, value));
  };

  const saveBulkEdit = async () => {
    // Convert all string values to numbers and validate
    const draft = JSON.parse(JSON.stringify(pulleyBulkDraft));
    const walk = (obj: any) => {
      for (const k of Object.keys(obj)) {
        const v = obj[k];
        if (v && typeof v === 'object') walk(v);
        else {
          const n = parseFloat(v);
          if (isNaN(n) || n < 0) {
            throw new Error(`Invalid value "${v}"`);
          }
          obj[k] = n;
        }
      }
    };
    try {
      walk(draft);
    } catch (e: any) {
      Alert.alert('Invalid value', e.message || 'All values must be valid positive numbers');
      return;
    }
    try {
      setPulleySaving(true);
      await api.put('/pulley-pricing', draft);
      await fetchPulleyPricing();
      setPulleyBulkMode(false);
      setPulleyBulkDraft(null);
      Alert.alert('Success', 'All pulley prices saved');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save prices');
    } finally {
      setPulleySaving(false);
    }
  };

  // ============= PRICE HISTORY =============
  const fetchPriceHistory = async () => {
    try {
      setHistoryLoading(true);
      const params: any = { limit: 200 };
      if (historyFilter !== 'all') params.product_type = historyFilter;
      const response = await api.get('/price-history', { params });
      setHistoryItems(response.data.items || []);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch history');
    } finally {
      setHistoryLoading(false);
    }
  };

  // ============= USER MANAGEMENT =============
  const fetchUsers = async () => {
    try {
      setUsersLoading(true);
      const response = await api.get('/admin/users');
      setUsers(response.data.users || []);
      setAssignableRoles(response.data.assignable_roles || []);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch users');
    } finally {
      setUsersLoading(false);
    }
  };

  const updateUserRole = async (email: string, role: string) => {
    try {
      await api.put('/admin/users/role', { email, role });
      setRolePickerEmail(null);
      await fetchUsers();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update role');
    }
  };

  const createUser = async () => {
    const email = newUserEmail.trim().toLowerCase();
    if (!email || !newUserName.trim() || !newUserPassword) {
      Alert.alert('Missing fields', 'Email, Name and Password are required');
      return;
    }
    if (newUserPassword.length < 6) {
      Alert.alert('Weak password', 'Password must be at least 6 characters');
      return;
    }
    try {
      setCreatingUser(true);
      await api.post('/admin/users', {
        email,
        name: newUserName.trim(),
        password: newUserPassword,
        role: newUserRole,
        company: newUserCompany.trim() || null,
      });
      setShowCreateUser(false);
      setNewUserEmail(''); setNewUserName(''); setNewUserPassword(''); setNewUserCompany('');
      setNewUserRole('sales_manager');
      await fetchUsers();
      Alert.alert('User Created', `${email} is now active. Share the password with them.`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreatingUser(false);
    }
  };

  useEffect(() => {
    if (mainTab === 'prices') {
      fetchPrices();
    } else if (mainTab === 'standards') {
      fetchStandardsSummary();
    } else if (mainTab === 'history') {
      fetchPriceHistory();
    } else if (mainTab === 'users') {
      fetchUsers();
    }
    
    // Listen for global refresh events
    const handleRefresh = () => {
      console.log('[Admin] Received refresh event, refetching data...');
      if (mainTab === 'prices') {
        fetchPrices();
      } else if (mainTab === 'standards') {
        fetchStandardsSummary();
      } else if (mainTab === 'history') {
        fetchPriceHistory();
      } else if (mainTab === 'users') {
        fetchUsers();
      }
    };
    
    cacheEvents.on('refresh', handleRefresh);
    
    return () => {
      cacheEvents.off('refresh', handleRefresh);
    };
  }, [mainTab]);

  // Refetch history when filter changes
  useEffect(() => {
    if (mainTab === 'history') fetchPriceHistory();
  }, [historyFilter]);

  // ============= PRICES FUNCTIONS =============
  const fetchPrices = async () => {
    try {
      setLoading(true);
      const response = await api.get('/admin/prices');
      setPrices(response.data);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch prices');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdatePrice = async (category: string, key: string, subKey: string | null, value: number) => {
    try {
      setSaving(true);
      await api.post('/admin/prices/update', {
        category,
        key,
        sub_key: subKey,
        value,
      });
      await fetchPrices();
      setEditingKey(null);
      Alert.alert('Success', 'Price updated successfully');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update price');
    } finally {
      setSaving(false);
    }
  };

  const handleExportPrices = async (format: 'excel' | 'pdf' = 'excel') => {
    try {
      setSaving(true);
      const token = await AsyncStorage.getItem('token');
      const endpoint = format === 'pdf' ? '/admin/prices/export/pdf' : '/admin/prices/export';
      const extension = format === 'pdf' ? 'pdf' : 'xlsx';
      const filename = `convero_prices_${new Date().toISOString().slice(0, 10)}.${extension}`;
      
      if (Platform.OS === 'web') {
        // Web: Open URL directly
        const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
        window.open(`${backendUrl}/api${endpoint}?token=${token}`, '_blank');
        Alert.alert('Success', `${format.toUpperCase()} file download started`);
      } else {
        // Native: Use FileSystem and Sharing
        const FileSystem = require('expo-file-system/legacy');
        const Sharing = require('expo-sharing');
        
        const url = `${api.defaults.baseURL}${endpoint}?token=${token}`;
        const fileUri = `${FileSystem.cacheDirectory}${filename}`;
        
        const downloadResult = await FileSystem.downloadAsync(url, fileUri);
        
        if (downloadResult.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) {
            await Sharing.shareAsync(downloadResult.uri, {
              mimeType: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
              dialogTitle: `Share ${format.toUpperCase()} File`,
            });
          } else {
            Alert.alert('Download Complete', `File saved to: ${downloadResult.uri}`);
          }
        } else {
          throw new Error('Download failed');
        }
      }
    } catch (error: any) {
      console.error('Export error:', error);
      Alert.alert('Error', error.response?.data?.detail || 'Failed to export prices');
    } finally {
      setSaving(false);
    }
  };

  const handleImportPrices = async () => {
    try {
      if (Platform.OS === 'web') {
        // Create a file input and trigger it
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.xlsx,.xls';
        input.onchange = async (e: any) => {
          const file = e.target.files[0];
          if (file) {
            setSaving(true);
            try {
              const formData = new FormData();
              formData.append('file', file);
              const response = await api.post('/admin/prices/import', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
              });
              await fetchPrices();
              Alert.alert('Success', response.data.message || 'Prices imported successfully');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to import prices');
            } finally {
              setSaving(false);
            }
          }
        };
        input.click();
      } else {
        Alert.alert('Info', 'Import feature works best on web. Please use the web version to import Excel files.');
      }
    } catch (error: any) {
      Alert.alert('Error', 'Failed to open file picker');
    }
  };

  const handleResetPrices = async () => {
    console.log('Reset button pressed!');
    Alert.alert(
      'Reset Prices',
      'Are you sure you want to reset all prices to default values?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            console.log('User confirmed reset');
            try {
              setSaving(true);
              // Cancel any active editing
              setEditingKey(null);
              setEditValue('');
              // Clear current prices first to show loading state
              setPrices(null);
              
              console.log('Calling reset API...');
              const resetResponse = await api.post('/admin/prices/reset');
              console.log('Reset response:', resetResponse.data);
              
              // Fetch fresh prices from server
              console.log('Fetching fresh prices...');
              const response = await api.get('/admin/prices');
              console.log('Fresh prices received:', JSON.stringify(response.data.basic_rates));
              
              setPrices(response.data);
              // Force re-render by updating key
              setRefreshKey(prev => prev + 1);
              
              Alert.alert('Success', `Prices reset to defaults!\nPipe cost: ₹${response.data.basic_rates.pipe_cost_per_kg}\nShaft cost: ₹${response.data.basic_rates.shaft_cost_per_kg}`);
            } catch (error: any) {
              console.error('Reset error:', error);
              Alert.alert('Error', error.response?.data?.detail || 'Failed to reset prices');
              // Try to refetch even on error
              fetchPrices();
            } finally {
              setSaving(false);
            }
          },
        },
      ]
    );
  };

  const startEdit = (key: string, value: number) => {
    setEditingKey(key);
    setEditValue(value.toString());
  };

  const saveEdit = (category: string, key: string, subKey: string | null = null) => {
    const value = parseFloat(editValue);
    if (isNaN(value) || value < 0) {
      Alert.alert('Invalid Value', 'Please enter a valid positive number');
      return;
    }
    handleUpdatePrice(category, key, subKey, value);
  };

  // ============= SET AS DEFAULT FUNCTIONS =============
  const handleSetAsDefault = () => {
    // Directly open the modal without extra confirmation
    console.log('Set as Default clicked, opening modal...');
    setShowSetDefaultModal(true);
    console.log('showSetDefaultModal set to true');
  };

  const sendSetDefaultOtp = async () => {
    try {
      setSendingOtp(true);
      const response = await api.post('/admin/prices/set-default/send-otp');
      setOtpEmail(response.data.email);
      setOtpSent(true);
      Alert.alert('OTP Sent', `Verification code sent to ${response.data.email}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setSendingOtp(false);
    }
  };

  const verifyAndSetDefault = async () => {
    if (otpValue.length !== 4) {
      Alert.alert('Invalid OTP', 'Please enter the 4-digit verification code');
      return;
    }

    try {
      setVerifyingOtp(true);
      const response = await api.post('/admin/prices/set-default/verify', { otp: otpValue });
      Alert.alert('Success', response.data.message);
      setShowSetDefaultModal(false);
      setOtpSent(false);
      setOtpValue('');
      fetchPrices(); // Refresh prices
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to verify OTP');
    } finally {
      setVerifyingOtp(false);
    }
  };

  const closeSetDefaultModal = () => {
    setShowSetDefaultModal(false);
    setOtpSent(false);
    setOtpValue('');
  };

  // ============= STANDARDS FUNCTIONS =============
  const fetchStandardsSummary = async () => {
    try {
      setLoadingStandards(true);
      const response = await api.get('/admin/standards-summary');
      setStandardsSummary(response.data.summary);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch standards');
    } finally {
      setLoadingStandards(false);
    }
  };

  const fetchCollectionData = async (collection: string) => {
    try {
      setLoadingStandards(true);
      setSelectedCollection(collection);
      const response = await api.get(`/admin/standards/${collection}`);
      setCollectionData(response.data.data);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to fetch data');
    } finally {
      setLoadingStandards(false);
    }
  };

  const viewItemDetails = (item: StandardItem) => {
    setSelectedItem(item);
    setDetailModalVisible(true);
  };

  // Get unique key fields for a collection item
  const getItemKeyFields = (item: StandardItem): Record<string, any> => {
    if (item.number) return { number: item.number }; // bearings
    if (item.actual_od) return { actual_od: item.actual_od }; // pipe_diameters
    if (item.diameter) return { diameter: item.diameter }; // shaft_diameters
    if (item.type && item.extension_mm) return { type: item.type }; // shaft_end_types
    if (item.pipe_dia && item.type_a) return { pipe_dia: item.pipe_dia }; // pipe_weights
    if (item.housing_dia && item.bearing_bore) return { housing_dia: item.housing_dia, bearing_bore: item.bearing_bore }; // housings
    if (item.belt_width && item.roller_type) return { belt_width: item.belt_width, roller_type: item.roller_type }; // roller_lengths
    if (item.shaft_dia && item.cost_per_piece !== undefined) return { shaft_dia: item.shaft_dia }; // circlips
    if (item.pipe_code && item.rubber_dia) return { pipe_code: item.pipe_code, rubber_dia: item.rubber_dia }; // rubber_rings
    if (item.pipe_code && item.cost) return { pipe_code: item.pipe_code }; // locking_rings
    if (item.pipe_code && item.rubber_options) return { pipe_code: item.pipe_code }; // rubber_lagging
    if (item.min_value !== undefined) return { min_value: item.min_value }; // discount_slabs
    if (item.min_km !== undefined) return { min_km: item.min_km }; // freight_rates
    if (item.type && item.percent !== undefined) return { type: item.type }; // packing_options
    if (item.key) return { key: item.key }; // gst_config
    if (item.material) return { material: item.material }; // raw_material_costs
    return {};
  };

  // Get editable fields for a collection item
  const getEditableFields = (item: StandardItem): string[] => {
    const excludeFields = ['_id', 'created_at', 'updated_at', 'migrated_from', 'created_by', 'updated_by'];
    return Object.keys(item).filter(key => !excludeFields.includes(key));
  };

  const openEditModal = (item: StandardItem) => {
    setEditingItem(item);
    const formData: Record<string, string> = {};
    getEditableFields(item).forEach(key => {
      const value = item[key];
      formData[key] = typeof value === 'object' ? JSON.stringify(value) : String(value);
    });
    setEditFormData(formData);
    setEditModalVisible(true);
  };

  const handleUpdateStandard = async () => {
    if (!selectedCollection || !editingItem) return;
    
    try {
      setSavingStandard(true);
      
      // Parse form data back to proper types
      const updateData: Record<string, any> = {};
      Object.entries(editFormData).forEach(([key, value]) => {
        // Try to parse as JSON first (for objects/arrays)
        try {
          updateData[key] = JSON.parse(value);
        } catch {
          // Try to parse as number
          const num = parseFloat(value);
          updateData[key] = isNaN(num) ? value : num;
        }
      });
      
      const query = getItemKeyFields(editingItem);
      
      await api.put(`/admin/standards/${selectedCollection}`, {
        query,
        update_data: updateData
      });
      
      setEditModalVisible(false);
      setEditingItem(null);
      fetchCollectionData(selectedCollection);
      Alert.alert('Success', 'Item updated successfully');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to update item');
    } finally {
      setSavingStandard(false);
    }
  };

  const handleDeleteStandard = (item: StandardItem) => {
    Alert.alert(
      'Delete Item',
      'Are you sure you want to delete this item? This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (!selectedCollection) return;
            
            try {
              setSavingStandard(true);
              const query = getItemKeyFields(item);
              
              await api.delete(`/admin/standards/${selectedCollection}`, {
                data: { query }
              });
              
              fetchCollectionData(selectedCollection);
              fetchStandardsSummary();
              Alert.alert('Success', 'Item deleted successfully');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to delete item');
            } finally {
              setSavingStandard(false);
            }
          }
        }
      ]
    );
  };

  // ============= ACCESS CHECK =============
  if (user?.role !== 'admin') {
    return (
      <View style={styles.container}>
        <View style={styles.accessDenied}>
          <Ionicons name="lock-closed" size={64} color="#ccc" />
          <Text style={styles.accessDeniedText}>Admin Access Required</Text>
          <Text style={styles.accessDeniedSubtext}>
            Contact administrator to get access
          </Text>
        </View>
      </View>
    );
  }

  // ============= PRICES RENDER FUNCTIONS =============
  const renderEditableRow = (
    label: string,
    value: number,
    editKey: string,
    category: string,
    key: string,
    subKey: string | null = null
  ) => (
    <View style={styles.priceRow} key={editKey}>
      <Text style={styles.priceLabel}>{label}</Text>
      {editingKey === editKey ? (
        <View style={styles.editContainer}>
          <TextInput
            style={styles.editInput}
            value={editValue}
            onChangeText={setEditValue}
            keyboardType="numeric"
            autoFocus
          />
          <TouchableOpacity
            style={styles.saveBtn}
            onPress={() => saveEdit(category, key, subKey)}
            disabled={saving}
          >
            <Ionicons name="checkmark" size={20} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.cancelBtn}
            onPress={() => setEditingKey(null)}
          >
            <Ionicons name="close" size={20} color="#666" />
          </TouchableOpacity>
        </View>
      ) : (
        <TouchableOpacity
          style={styles.valueContainer}
          onPress={() => startEdit(editKey, value)}
        >
          <Text style={styles.priceValue}>₹{value.toFixed(2)}</Text>
          <Ionicons name="pencil" size={16} color="#960018" />
        </TouchableOpacity>
      )}
    </View>
  );

  // Editable row for pulley prices - uses path array to update nested MongoDB data
  const renderPulleyEditableRow = (
    label: string,
    value: number,
    editKey: string,
    path: string[]
  ) => {
    // Bulk edit mode: render a persistent TextInput bound to pulleyBulkDraft
    if (pulleyBulkMode) {
      // Read current value from draft along path
      let draftVal: any = pulleyBulkDraft;
      for (const seg of path) draftVal = draftVal?.[seg];
      const shown = draftVal === undefined || draftVal === null ? String(value) : String(draftVal);
      return (
        <View style={styles.priceRow} key={editKey}>
          <Text style={styles.priceLabel}>{label}</Text>
          <View style={styles.editContainer}>
            <Text style={{ fontSize: 13, color: '#94A3B8', marginRight: 4 }}>₹</Text>
            <TextInput
              style={[styles.editInput, { minWidth: 80 }]}
              value={shown}
              onChangeText={(t) => updateBulkValue(path, t)}
              keyboardType="numeric"
              testID={`pulley-bulk-${editKey}`}
            />
          </View>
        </View>
      );
    }
    return (
      <View style={styles.priceRow} key={editKey}>
        <Text style={styles.priceLabel}>{label}</Text>
        {pulleyEditKey === editKey ? (
          <View style={styles.editContainer}>
            <TextInput
              style={styles.editInput}
              value={pulleyEditValue}
              onChangeText={setPulleyEditValue}
              keyboardType="numeric"
              autoFocus
              testID={`pulley-input-${editKey}`}
            />
            <TouchableOpacity
              style={styles.saveBtn}
              onPress={() => savePulleyEdit(path)}
              disabled={pulleySaving}
              testID={`pulley-save-${editKey}`}
            >
              <Ionicons name="checkmark" size={20} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.cancelBtn}
              onPress={cancelPulleyEdit}
              testID={`pulley-cancel-${editKey}`}
            >
              <Ionicons name="close" size={20} color="#666" />
            </TouchableOpacity>
          </View>
        ) : (
          <TouchableOpacity
            style={styles.valueContainer}
            onPress={() => startPulleyEdit(editKey, value)}
            testID={`pulley-edit-${editKey}`}
          >
            <Text style={styles.priceValue}>₹{Number(value).toFixed(2)}</Text>
            <Ionicons name="pencil" size={16} color="#960018" />
          </TouchableOpacity>
        )}
      </View>
    );
  };

  const renderBasicRates = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Basic Material Rates</Text>
      {renderEditableRow(
        'Pipe Cost (per kg)',
        prices?.basic_rates.pipe_cost_per_kg || 0,
        'pipe_cost',
        'pipe_cost',
        'pipe_cost_per_kg'
      )}
      {renderEditableRow(
        'Shaft Cost (per kg)',
        prices?.basic_rates.shaft_cost_per_kg || 0,
        'shaft_cost',
        'shaft_cost',
        'shaft_cost_per_kg'
      )}
    </View>
  );

  const renderBearingCosts = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Bearing Costs (per piece)</Text>
      {prices?.bearing_costs && Object.entries(prices.bearing_costs).map(([bearing, makes]) => (
        <View key={bearing} style={styles.bearingGroup}>
          <Text style={styles.bearingTitle}>{bearing}</Text>
          {Object.entries(makes).map(([make, cost]) => (
            renderEditableRow(
              make.toUpperCase(),
              cost,
              `bearing_${bearing}_${make}`,
              'bearing',
              bearing,
              make
            )
          ))}
        </View>
      ))}
    </View>
  );

  const renderSealCosts = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Seal Costs (per set)</Text>
      {prices?.seal_costs && Object.entries(prices.seal_costs).map(([bearing, cost]) => (
        renderEditableRow(
          `Bearing ${bearing}`,
          cost,
          `seal_${bearing}`,
          'seal',
          bearing
        )
      ))}
    </View>
  );

  const renderHousingCosts = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Housing Costs (per piece)</Text>
      <Text style={styles.sectionSubtitle}>Format: Housing OD / Bearing OD (mm)</Text>
      {prices?.housing_costs && Object.entries(prices.housing_costs).map(([config, cost]) => (
        renderEditableRow(
          config,
          cost,
          `housing_${config}`,
          'housing',
          config
        )
      ))}
    </View>
  );

  const renderCirclipCosts = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Circlip Costs (per piece)</Text>
      {prices?.circlip_costs && Object.entries(prices.circlip_costs).map(([shaft, cost]) => (
        renderEditableRow(
          `${shaft}mm Shaft`,
          cost,
          `circlip_${shaft}`,
          'circlip',
          shaft
        )
      ))}
    </View>
  );

  const renderRubberRingCosts = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Rubber Ring Costs (per ring)</Text>
      {prices?.rubber_ring_costs && Object.entries(prices.rubber_ring_costs).map(([config, cost]) => (
        renderEditableRow(
          `Pipe/Rubber: ${config}`,
          cost,
          `rubber_${config}`,
          'rubber_ring',
          config
        )
      ))}
    </View>
  );

  const renderLockingRingCosts = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Locking Ring Costs (per roller)</Text>
      {prices?.locking_ring_costs && Object.entries(prices.locking_ring_costs).map(([pipe, cost]) => (
        renderEditableRow(
          `${pipe}mm Pipe`,
          cost,
          `locking_${pipe}`,
          'locking_ring',
          pipe
        )
      ))}
    </View>
  );

  // ============= STANDARDS RENDER FUNCTIONS =============
  const renderStandardsSummary = () => (
    <View style={styles.standardsGrid}>
      {standardsSummary.map((item) => (
        <TouchableOpacity
          key={item.collection}
          style={[
            styles.collectionCard,
            selectedCollection === item.collection && styles.collectionCardActive
          ]}
          onPress={() => fetchCollectionData(item.collection)}
        >
          <Ionicons 
            name="folder-outline" 
            size={24} 
            color={selectedCollection === item.collection ? '#fff' : '#960018'} 
          />
          <Text style={[
            styles.collectionName,
            selectedCollection === item.collection && styles.collectionNameActive
          ]}>
            {COLLECTION_LABELS[item.collection] || item.collection}
          </Text>
          <Text style={[
            styles.collectionCount,
            selectedCollection === item.collection && styles.collectionCountActive
          ]}>
            {item.count} items
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  const renderCollectionData = () => {
    if (!selectedCollection) return null;

    const getItemLabel = (item: StandardItem): string => {
      if (item.number) return item.number; // bearings
      if (item.actual_od) return `${item.display_code}mm (${item.actual_od}mm)`; // pipe_diameters
      if (item.diameter) return `${item.diameter}mm`; // shaft_diameters
      if (item.type) return item.description || item.type; // shaft_end_types, packing
      if (item.pipe_dia) return `${item.pipe_dia}mm pipe`; // pipe_weights
      if (item.housing_dia) return `Housing ${item.housing_dia} / Bore ${item.bearing_bore}`; // housings
      if (item.belt_width) return `Belt ${item.belt_width}mm`; // roller_lengths
      if (item.shaft_dia) return `Shaft ${item.shaft_dia}mm`; // circlips
      if (item.pipe_code && item.rubber_dia) return `Pipe ${item.pipe_code} / Rubber ${item.rubber_dia}`; // rubber_rings
      if (item.pipe_code) return `Pipe ${item.pipe_code}mm`; // locking_rings, rubber_lagging
      if (item.min_value !== undefined) return `₹${item.min_value.toLocaleString()} - ₹${item.max_value.toLocaleString()}`; // discount_slabs
      if (item.min_km !== undefined) return `${item.min_km} - ${item.max_km} km`; // freight_rates
      if (item.key) return item.key; // gst_config
      if (item.material) return item.material; // raw_material_costs
      return JSON.stringify(item).substring(0, 40);
    };

    const getItemSubtitle = (item: StandardItem): string => {
      if (item.costs) return `SKF: ₹${item.costs.skf || '-'}, FAG: ₹${item.costs.fag || '-'}`;
      if (item.type_a) return `A: ${item.type_a}, B: ${item.type_b}, C: ${item.type_c} kg/m`;
      if (item.weight_per_meter) return `${item.weight_per_meter} kg/m`;
      if (item.cost) return `₹${item.cost}`;
      if (item.cost_per_piece) return `₹${item.cost_per_piece}/pc`;
      if (item.cost_per_ring) return `₹${item.cost_per_ring}/ring`;
      if (item.discount_percent) return `${item.discount_percent}% discount`;
      if (item.rate_per_kg) return `₹${item.rate_per_kg}/kg`;
      if (item.percent !== undefined) return `${item.percent}%`;
      if (item.value !== undefined) return `${item.value}`;
      if (item.extension_mm) return `+${item.extension_mm}mm`;
      if (item.rubber_options) return `Options: ${item.rubber_options.join(', ')}mm`;
      if (item.lengths) return `Lengths: ${item.lengths.join(', ')}mm`;
      return '';
    };

    return (
      <View style={styles.collectionDataContainer}>
        <View style={styles.collectionHeader}>
          <TouchableOpacity 
            style={styles.backButton}
            onPress={() => setSelectedCollection(null)}
          >
            <Ionicons name="arrow-back" size={24} color="#960018" />
          </TouchableOpacity>
          <Text style={styles.collectionTitle}>
            {COLLECTION_LABELS[selectedCollection] || selectedCollection}
          </Text>
          <Text style={styles.collectionItemCount}>
            {collectionData.length} items
          </Text>
        </View>
        
        {/* Read-only notice */}
        <View style={styles.readOnlyNotice}>
          <Ionicons name="information-circle" size={16} color="#666" />
          <Text style={styles.readOnlyText}>View only. To change prices, use the Prices tab.</Text>
        </View>
        
        <FlatList
          data={collectionData}
          keyExtractor={(item, index) => index.toString()}
          renderItem={({ item }) => (
            <TouchableOpacity 
              style={styles.dataRow}
              onPress={() => viewItemDetails(item)}
            >
              <View style={styles.dataRowContent}>
                <Text style={styles.dataRowLabel}>{getItemLabel(item)}</Text>
                <Text style={styles.dataRowValue}>{getItemSubtitle(item)}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#ccc" />
            </TouchableOpacity>
          )}
          contentContainerStyle={styles.dataList}
        />
      </View>
    );
  };

  const renderDetailModal = () => (
    <Modal
      visible={detailModalVisible}
      animationType="slide"
      transparent={true}
      onRequestClose={() => setDetailModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Item Details</Text>
            <TouchableOpacity onPress={() => setDetailModalVisible(false)}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
          <ScrollView style={styles.modalBody}>
            {selectedItem && Object.entries(selectedItem)
              .filter(([key]) => !key.startsWith('_') && key !== 'created_at' && key !== 'migrated_from')
              .map(([key, value]) => (
                <View key={key} style={styles.detailRow}>
                  <Text style={styles.detailKey}>{key.replace(/_/g, ' ')}</Text>
                  <Text style={styles.detailValue}>
                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                  </Text>
                </View>
              ))}
          </ScrollView>
          <View style={styles.modalFooter}>
            <TouchableOpacity 
              style={styles.modalEditBtn}
              onPress={() => {
                setDetailModalVisible(false);
                if (selectedItem) openEditModal(selectedItem);
              }}
            >
              <Ionicons name="pencil" size={18} color="#fff" />
              <Text style={styles.modalEditBtnText}>Edit</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.modalDeleteBtn}
              onPress={() => {
                setDetailModalVisible(false);
                if (selectedItem) handleDeleteStandard(selectedItem);
              }}
            >
              <Ionicons name="trash" size={18} color="#C41E3A" />
              <Text style={styles.modalDeleteBtnText}>Delete</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  const renderEditModal = () => (
    <Modal
      visible={editModalVisible}
      animationType="slide"
      transparent={true}
      onRequestClose={() => setEditModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Edit Item</Text>
            <TouchableOpacity onPress={() => setEditModalVisible(false)}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
          <ScrollView style={styles.modalBody}>
            {editingItem && getEditableFields(editingItem).map(key => (
              <View key={key} style={styles.editFieldContainer}>
                <Text style={styles.editFieldLabel}>{key.replace(/_/g, ' ')}</Text>
                <TextInput
                  style={styles.editFieldInput}
                  value={editFormData[key] || ''}
                  onChangeText={(text) => setEditFormData({...editFormData, [key]: text})}
                  placeholder={`Enter ${key}`}
                  multiline={typeof editingItem[key] === 'object'}
                />
              </View>
            ))}
          </ScrollView>
          <View style={styles.modalFooter}>
            <TouchableOpacity 
              style={styles.cancelButton}
              onPress={() => setEditModalVisible(false)}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.saveButton}
              onPress={handleUpdateStandard}
              disabled={savingStandard}
            >
              {savingStandard ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="checkmark" size={18} color="#fff" />
                  <Text style={styles.saveButtonText}>Save</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  // ============= MAIN RENDER =============
  const categories: { key: PriceCategory; label: string; icon: string }[] = [
    { key: 'basic', label: 'Basic', icon: 'cash-outline' },
    { key: 'bearing', label: 'Bearing', icon: 'ellipse-outline' },
    { key: 'housing', label: 'Housing', icon: 'home-outline' },
    { key: 'seal', label: 'Seal', icon: 'disc-outline' },
    { key: 'circlip', label: 'Circlip', icon: 'radio-button-on-outline' },
    { key: 'rubber', label: 'Rubber', icon: 'albums-outline' },
    { key: 'locking', label: 'Locking', icon: 'lock-closed-outline' },
  ];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Admin Panel</Text>
        <View style={styles.mainTabs}>
          <TouchableOpacity
            style={[styles.mainTab, mainTab === 'prices' && styles.mainTabActive]}
            onPress={() => setMainTab('prices')}
          >
            <Ionicons 
              name="pricetag-outline" 
              size={18} 
              color={mainTab === 'prices' ? '#960018' : '#fff'} 
            />
            <Text style={[styles.mainTabText, mainTab === 'prices' && styles.mainTabTextActive]}>
              Prices
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.mainTab, mainTab === 'standards' && styles.mainTabActive]}
            onPress={() => setMainTab('standards')}
          >
            <Ionicons 
              name="server-outline" 
              size={18} 
              color={mainTab === 'standards' ? '#960018' : '#fff'} 
            />
            <Text style={[styles.mainTabText, mainTab === 'standards' && styles.mainTabTextActive]}>
              Standards
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.mainTab, mainTab === 'history' && styles.mainTabActive]}
            onPress={() => setMainTab('history')}
            testID="history-tab"
          >
            <Ionicons
              name="time-outline"
              size={18}
              color={mainTab === 'history' ? '#960018' : '#fff'}
            />
            <Text style={[styles.mainTabText, mainTab === 'history' && styles.mainTabTextActive]}>
              History
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.mainTab, mainTab === 'users' && styles.mainTabActive]}
            onPress={() => setMainTab('users')}
            testID="users-tab"
          >
            <Ionicons
              name="people-circle-outline"
              size={18}
              color={mainTab === 'users' ? '#960018' : '#fff'}
            />
            <Text style={[styles.mainTabText, mainTab === 'users' && styles.mainTabTextActive]}>
              Users
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {mainTab === 'prices' ? (
        <View style={{flex: 1}}>
          {/* Roller / Pulley Toggle */}
          <View style={{ flexDirection: 'row', marginHorizontal: 16, marginTop: 12, backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: 10, padding: 3 }}>
            <TouchableOpacity style={[{ flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 10, borderRadius: 8, gap: 6 }, productType === 'roller' && { backgroundColor: '#fff', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 }]} onPress={() => setProductType('roller')}>
              <Ionicons name="disc-outline" size={14} color={productType === 'roller' ? '#C5964A' : '#94A3B8'} />
              <Text style={{ fontSize: 14, fontWeight: productType === 'roller' ? '700' : '500', color: productType === 'roller' ? '#C5964A' : '#94A3B8' }}>Roller</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[{ flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 10, borderRadius: 8, gap: 6 }, productType === 'pulley' && { backgroundColor: '#fff', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 }]} onPress={() => { setProductType('pulley'); if (!pulleyStandards) fetchPulleyPricing(); }}>
              <Ionicons name="cog-outline" size={14} color={productType === 'pulley' ? '#C5964A' : '#94A3B8'} />
              <Text style={{ fontSize: 14, fontWeight: productType === 'pulley' ? '700' : '500', color: productType === 'pulley' ? '#C5964A' : '#94A3B8' }}>Pulley</Text>
            </TouchableOpacity>
          </View>

          {productType === 'pulley' ? (
            <ScrollView
              style={{ flex: 1, padding: 16 }}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  tintColor="#C5964A"
                  colors={['#C5964A']}
                />
              }
            >
              {!pulleyStandards ? (
                <ActivityIndicator size="large" color="#C5964A" style={{ paddingVertical: 40 }} />
              ) : (
                <>
                  {/* Bulk edit toolbar */}
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: 10, padding: 10 }}>
                    {pulleyBulkMode ? (
                      <>
                        <Text style={{ fontSize: 13, fontWeight: '700', color: '#C5964A' }}>
                          Bulk edit active — change any value, then Save All
                        </Text>
                        <View style={{ flexDirection: 'row', gap: 8 }}>
                          <TouchableOpacity
                            onPress={cancelBulkEdit}
                            disabled={pulleySaving}
                            testID="pulley-bulk-cancel"
                            style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8, backgroundColor: '#E5E7EB', flexDirection: 'row', alignItems: 'center', gap: 4 }}
                          >
                            <Ionicons name="close" size={14} color="#475569" />
                            <Text style={{ fontSize: 13, fontWeight: '600', color: '#475569' }}>Cancel</Text>
                          </TouchableOpacity>
                          <TouchableOpacity
                            onPress={saveBulkEdit}
                            disabled={pulleySaving}
                            testID="pulley-bulk-save"
                            style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8, backgroundColor: '#217346', flexDirection: 'row', alignItems: 'center', gap: 4 }}
                          >
                            <Ionicons name="checkmark-done" size={14} color="#fff" />
                            <Text style={{ fontSize: 13, fontWeight: '700', color: '#fff' }}>{pulleySaving ? 'Saving...' : 'Save All'}</Text>
                          </TouchableOpacity>
                        </View>
                      </>
                    ) : (
                      <>
                        <Text style={{ fontSize: 13, color: '#64748B' }}>
                          Tap any ₹ value to edit one — or switch to bulk edit to change many at once.
                        </Text>
                        <TouchableOpacity
                          onPress={enterBulkEdit}
                          testID="pulley-bulk-enter"
                          style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8, backgroundColor: '#C5964A', flexDirection: 'row', alignItems: 'center', gap: 4 }}
                        >
                          <Ionicons name="create-outline" size={14} color="#fff" />
                          <Text style={{ fontSize: 13, fontWeight: '700', color: '#fff' }}>Bulk Edit</Text>
                        </TouchableOpacity>
                      </>
                    )}
                  </View>

                  {/* Pipe Rates - nested: dia -> thk -> rate */}
                  <View style={styles.priceCard}>
                    <Text style={styles.priceSectionTitle}>Pipe Rates (Rs./kg)</Text>
                    {Object.entries(pulleyStandards.pipe_rates || {}).map(([dia, rates]: [string, any]) => (
                      <View key={dia} style={{ marginBottom: 10 }}>
                        <Text style={{ fontSize: 13, fontWeight: '700', color: '#960018', marginBottom: 6 }}>{dia}mm Pipe</Text>
                        {Object.entries(rates).map(([thk, rate]: [string, any]) => {
                          const ek = `pipe_${dia}_${thk}`;
                          return renderPulleyEditableRow(`${thk}mm thickness`, Number(rate), ek, ['pipe_rates', dia, thk]);
                        })}
                      </View>
                    ))}
                  </View>

                  {/* Shaft Rates - nested: dia -> material -> rate */}
                  <View style={styles.priceCard}>
                    <Text style={styles.priceSectionTitle}>Shaft Rates (Rs./kg)</Text>
                    {Object.entries(pulleyStandards.shaft_rates || {}).map(([dia, rates]: [string, any]) => (
                      <View key={dia} style={{ marginBottom: 10 }}>
                        <Text style={{ fontSize: 13, fontWeight: '700', color: '#960018', marginBottom: 6 }}>{dia}mm Shaft</Text>
                        {Object.entries(rates).map(([mat, rate]: [string, any]) => {
                          const ek = `shaft_${dia}_${mat}`;
                          return renderPulleyEditableRow(mat, Number(rate), ek, ['shaft_rates', dia, mat]);
                        })}
                      </View>
                    ))}
                  </View>

                  {/* End Plate Rates */}
                  <View style={styles.priceCard}>
                    <Text style={styles.priceSectionTitle}>End Plate Rates (Rs./kg)</Text>
                    {Object.entries(pulleyStandards.end_plate_rates || {}).map(([thk, rate]: [string, any]) => {
                      const ek = `endplate_${thk}`;
                      return renderPulleyEditableRow(`${thk}mm`, Number(rate), ek, ['end_plate_rates', thk]);
                    })}
                  </View>

                  {/* Hub Rates */}
                  <View style={styles.priceCard}>
                    <Text style={styles.priceSectionTitle}>Hub Rates (Rs./kg)</Text>
                    {Object.entries(pulleyStandards.hub_rates || {}).map(([dia, rate]: [string, any]) => {
                      const ek = `hub_${dia}`;
                      return renderPulleyEditableRow(`${dia}mm`, Number(rate), ek, ['hub_rates', dia]);
                    })}
                  </View>

                  {/* Rubber Lagging - Plain/Diamond */}
                  <View style={styles.priceCard}>
                    <Text style={styles.priceSectionTitle}>Rubber Lagging - Plain/Diamond (Rs./sqm)</Text>
                    {Object.entries(pulleyStandards.rubber_plain_rates || {}).map(([thk, rate]: [string, any]) => {
                      const ek = `rplain_${thk}`;
                      return renderPulleyEditableRow(`${thk}mm`, Number(rate), ek, ['rubber_plain_rates', thk]);
                    })}
                  </View>

                  {/* Rubber Lagging - Ceramic */}
                  <View style={styles.priceCard}>
                    <Text style={styles.priceSectionTitle}>Rubber Lagging - Ceramic (Rs./sqm)</Text>
                    {Object.entries(pulleyStandards.rubber_ceramic_rates || {}).map(([thk, rate]: [string, any]) => {
                      const ek = `rcer_${thk}`;
                      return renderPulleyEditableRow(`${thk}mm`, Number(rate), ek, ['rubber_ceramic_rates', thk]);
                    })}
                  </View>

                  {/* Action buttons */}
                  <TouchableOpacity
                    style={[styles.resetButton, { backgroundColor: '#C41E3A' }]}
                    onPress={handleResetPulleyPrices}
                    disabled={pulleySaving}
                    testID="pulley-reset-btn"
                  >
                    <Ionicons name="refresh" size={20} color="#fff" />
                    <Text style={[styles.resetButtonText, { color: '#fff' }]}>Reset Pulley to Default</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[styles.resetButton, { backgroundColor: '#217346', marginTop: 12 }]}
                    onPress={handleSetDefaultPulleyPrices}
                    disabled={pulleySaving}
                    testID="pulley-set-default-btn"
                  >
                    <Ionicons name="checkmark-done" size={20} color="#fff" />
                    <Text style={[styles.resetButtonText, { color: '#fff' }]}>Save Current as Default</Text>
                  </TouchableOpacity>

                  <View style={{ height: 100 }} />
                </>
              )}
            </ScrollView>
          ) : (
          <>
          <View style={styles.categoryTabs}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {categories.map((cat) => (
                <TouchableOpacity
                  key={cat.key}
                  style={[
                    styles.categoryTab,
                    activeCategory === cat.key && styles.categoryTabActive,
                  ]}
                  onPress={() => setActiveCategory(cat.key)}
                >
                  <Ionicons
                    name={cat.icon as any}
                    size={18}
                    color={activeCategory === cat.key ? '#fff' : '#666'}
                  />
                  <Text
                    style={[
                      styles.categoryTabText,
                      activeCategory === cat.key && styles.categoryTabTextActive,
                    ]}
                  >
                    {cat.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#960018" />
              <Text style={styles.loadingText}>Loading prices...</Text>
            </View>
          ) : (
            <ScrollView 
              style={styles.content} 
              showsVerticalScrollIndicator={false}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  tintColor="#960018"
                  colors={['#960018']}
                />
              }
            >
              {activeCategory === 'basic' && renderBasicRates()}
              {activeCategory === 'bearing' && renderBearingCosts()}
              {activeCategory === 'housing' && renderHousingCosts()}
              {activeCategory === 'seal' && renderSealCosts()}
              {activeCategory === 'circlip' && renderCirclipCosts()}
              {activeCategory === 'rubber' && renderRubberRingCosts()}
              {activeCategory === 'locking' && renderLockingRingCosts()}

              {/* Import/Export Buttons */}
              <View style={styles.importExportContainer}>
                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: '#217346' }]}
                  onPress={() => handleExportPrices('excel')}
                  disabled={saving}
                >
                  <Ionicons name="grid-outline" size={20} color="#fff" />
                  <Text style={styles.actionButtonText}>Excel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: '#960018' }]}
                  onPress={() => handleExportPrices('pdf')}
                  disabled={saving}
                >
                  <Ionicons name="document-outline" size={20} color="#fff" />
                  <Text style={styles.actionButtonText}>PDF</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: '#4CAF50' }]}
                  onPress={handleImportPrices}
                  disabled={saving}
                >
                  <Ionicons name="cloud-upload-outline" size={20} color="#fff" />
                  <Text style={styles.actionButtonText}>Import</Text>
                </TouchableOpacity>
              </View>

              <TouchableOpacity
                style={[styles.resetButton, { backgroundColor: '#C41E3A' }]}
                onPress={async () => {
                  try {
                    setSaving(true);
                    setEditingKey(null);
                    setEditValue('');
                    
                    // Call reset API directly without confirmation
                    await api.post('/admin/prices/reset');
                    
                    // Fetch fresh prices
                    const response = await api.get('/admin/prices');
                    setPrices(response.data);
                    
                    Alert.alert('Done', 'Prices reset to defaults');
                  } catch (error: any) {
                    Alert.alert('Error', String(error));
                  } finally {
                    setSaving(false);
                  }
                }}
                disabled={saving}
              >
                <Ionicons name="refresh" size={20} color="#fff" />
                <Text style={[styles.resetButtonText, { color: '#fff' }]}>Reset All to Default</Text>
              </TouchableOpacity>

              {/* Set as Default Button */}
              <TouchableOpacity
                style={[styles.resetButton, { backgroundColor: '#217346', marginTop: 12 }]}
                onPress={() => {
                  console.log('Set as Default button pressed');
                  setShowSetDefaultModal(true);
                }}
                disabled={saving}
                activeOpacity={0.7}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, pointerEvents: 'none' }}>
                  <Ionicons name="checkmark-circle" size={20} color="#fff" />
                  <Text style={[styles.resetButtonText, { color: '#fff' }]}>Set as Default (OTP)</Text>
                </View>
              </TouchableOpacity>

              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}
        </>
        )}
        </View>
      ) : mainTab === 'standards' ? (
        <>
          {loadingStandards ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#960018" />
              <Text style={styles.loadingText}>Loading standards...</Text>
            </View>
          ) : selectedCollection ? (
            renderCollectionData()
          ) : (
            <ScrollView 
              style={styles.content} 
              showsVerticalScrollIndicator={false}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  tintColor="#960018"
                  colors={['#960018']}
                />
              }
            >
              <Text style={styles.standardsTitle}>Product Standards Data</Text>
              <Text style={styles.standardsSubtitle}>
                View-only reference data. To change prices, use the Prices tab.
              </Text>
              {renderStandardsSummary()}
              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}
        </>
      ) : mainTab === 'history' ? (
        // History tab
        <View style={{ flex: 1 }}>
          {/* Filter chips */}
          <View style={{ flexDirection: 'row', gap: 8, paddingHorizontal: 16, paddingTop: 12 }}>
            {(['all','roller','pulley'] as const).map((f) => (
              <TouchableOpacity
                key={f}
                onPress={() => setHistoryFilter(f)}
                testID={`history-filter-${f}`}
                style={{
                  paddingHorizontal: 14,
                  paddingVertical: 8,
                  borderRadius: 20,
                  backgroundColor: historyFilter === f ? '#960018' : 'rgba(255,255,255,0.6)',
                  borderWidth: 1,
                  borderColor: historyFilter === f ? '#960018' : '#E5E7EB',
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: '600', color: historyFilter === f ? '#fff' : '#475569', textTransform: 'capitalize' }}>{f}</Text>
              </TouchableOpacity>
            ))}
            <View style={{ flex: 1 }} />
            <TouchableOpacity
              onPress={fetchPriceHistory}
              testID="history-refresh"
              style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.6)', borderWidth: 1, borderColor: '#E5E7EB', flexDirection: 'row', alignItems: 'center', gap: 4 }}
            >
              <Ionicons name="refresh" size={14} color="#475569" />
              <Text style={{ fontSize: 13, fontWeight: '600', color: '#475569' }}>Refresh</Text>
            </TouchableOpacity>
          </View>

          {historyLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#960018" />
              <Text style={styles.loadingText}>Loading history...</Text>
            </View>
          ) : historyItems.length === 0 ? (
            <View style={{ paddingTop: 60, alignItems: 'center' }}>
              <Ionicons name="time-outline" size={56} color="#CBD5E1" />
              <Text style={{ marginTop: 12, fontSize: 15, color: '#94A3B8' }}>No price changes logged yet</Text>
            </View>
          ) : (
            <ScrollView style={{ flex: 1, padding: 16 }}>
              {historyItems.map((h: any) => {
                const when = new Date(h.timestamp);
                const dd = String(when.getDate()).padStart(2,'0');
                const mm = String(when.getMonth()+1).padStart(2,'0');
                const yy = when.getFullYear();
                const hh = String(when.getHours()).padStart(2,'0');
                const mi = String(when.getMinutes()).padStart(2,'0');
                const pretty = `${dd}-${mm}-${yy} ${hh}:${mi}`;
                const pathStr = [h.category, h.key, h.sub_key].filter(Boolean).join(' → ');
                const direction = (h.old_value ?? 0) < h.new_value ? 'up' : 'down';
                const delta = h.old_value != null ? (h.new_value - h.old_value) : null;
                return (
                  <View key={h.id} style={{ backgroundColor: '#fff', borderRadius: 10, padding: 12, marginBottom: 8, borderLeftWidth: 4, borderLeftColor: h.product_type === 'pulley' ? '#C5964A' : '#960018' }} testID={`history-row-${h.id}`}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: 11, fontWeight: '700', color: h.product_type === 'pulley' ? '#C5964A' : '#960018', textTransform: 'uppercase', letterSpacing: 0.5 }}>{h.product_type}</Text>
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '#1F2937', marginTop: 2 }}>{pathStr}</Text>
                        <Text style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>
                          {h.old_value != null ? `₹${Number(h.old_value).toFixed(2)}` : '—'}
                          <Text style={{ color: '#9CA3AF' }}>  →  </Text>
                          <Text style={{ fontWeight: '700', color: '#1F2937' }}>₹{Number(h.new_value).toFixed(2)}</Text>
                          {delta != null && (
                            <Text style={{ color: direction === 'up' ? '#DC2626' : '#059669', fontWeight: '600' }}>
                              {'  '}({direction === 'up' ? '+' : ''}{delta.toFixed(2)})
                            </Text>
                          )}
                        </Text>
                      </View>
                      <View style={{ alignItems: 'flex-end' }}>
                        <Text style={{ fontSize: 11, color: '#9CA3AF' }}>{pretty}</Text>
                        <Text style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{h.user_email}</Text>
                      </View>
                    </View>
                  </View>
                );
              })}
              <View style={{ height: 100 }} />
            </ScrollView>
          )}
        </View>
      ) : (
        // Users tab
        <View style={{ flex: 1 }}>
          <View style={{ flexDirection: 'row', paddingHorizontal: 16, paddingTop: 12, alignItems: 'center', gap: 8 }}>
            <Text style={{ flex: 1, fontSize: 13, color: '#64748B' }}>
              Manage roles for all registered users. Click a role pill to change it.
            </Text>
            <TouchableOpacity
              onPress={() => setShowCreateUser(true)}
              testID="create-user-btn"
              style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: '#960018', flexDirection: 'row', alignItems: 'center', gap: 4 }}
            >
              <Ionicons name="person-add" size={14} color="#fff" />
              <Text style={{ fontSize: 13, fontWeight: '700', color: '#fff' }}>New User</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={fetchUsers}
              testID="users-refresh"
              style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.6)', borderWidth: 1, borderColor: '#E5E7EB', flexDirection: 'row', alignItems: 'center', gap: 4 }}
            >
              <Ionicons name="refresh" size={14} color="#475569" />
              <Text style={{ fontSize: 13, fontWeight: '600', color: '#475569' }}>Refresh</Text>
            </TouchableOpacity>
          </View>
          {usersLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#960018" />
              <Text style={styles.loadingText}>Loading users...</Text>
            </View>
          ) : (
            <ScrollView style={{ flex: 1, padding: 16 }}>
              {users.map((u: any) => {
                const roleColor: Record<string, string> = {
                  admin: '#DC2626',
                  sales_manager: '#C5964A',
                  production_head: '#0891B2',
                  accounts: '#7C3AED',
                  dispatch: '#059669',
                  customer: '#64748B',
                };
                const color = roleColor[u.role] || '#64748B';
                const isPickerOpen = rolePickerEmail === u.email;
                return (
                  <View key={u.email} style={{ backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 8, borderLeftWidth: 4, borderLeftColor: color }} testID={`user-row-${u.email}`}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: 15, fontWeight: '600', color: '#1F2937' }}>{u.name || u.email}</Text>
                        <Text style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>{u.email}</Text>
                      </View>
                      <TouchableOpacity
                        onPress={() => setRolePickerEmail(isPickerOpen ? null : u.email)}
                        testID={`role-pill-${u.email}`}
                        style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 14, backgroundColor: color, flexDirection: 'row', alignItems: 'center', gap: 4 }}
                      >
                        <Text style={{ fontSize: 12, fontWeight: '700', color: '#fff', textTransform: 'capitalize' }}>{(u.role || 'customer').replace('_',' ')}</Text>
                        <Ionicons name={isPickerOpen ? 'chevron-up' : 'chevron-down'} size={12} color="#fff" />
                      </TouchableOpacity>
                    </View>
                    {isPickerOpen && (
                      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#F1F5F9' }}>
                        {assignableRoles.map((r) => (
                          <TouchableOpacity
                            key={r}
                            onPress={() => updateUserRole(u.email, r)}
                            testID={`role-option-${u.email}-${r}`}
                            disabled={r === u.role}
                            style={{
                              paddingHorizontal: 10,
                              paddingVertical: 6,
                              borderRadius: 12,
                              backgroundColor: r === u.role ? '#E5E7EB' : (roleColor[r] || '#64748B'),
                              opacity: r === u.role ? 0.5 : 1,
                            }}
                          >
                            <Text style={{ fontSize: 11, fontWeight: '600', color: r === u.role ? '#64748B' : '#fff', textTransform: 'capitalize' }}>
                              {r.replace('_', ' ')}
                            </Text>
                          </TouchableOpacity>
                        ))}
                      </View>
                    )}
                  </View>
                );
              })}
              <View style={{ height: 100 }} />
            </ScrollView>
          )}
        </View>
      )}

      {renderDetailModal()}

      {(saving || savingStandard) && (
        <View style={styles.savingOverlay}>
          <ActivityIndicator size="large" color="#960018" />
          <Text style={styles.savingText}>Saving...</Text>
        </View>
      )}

      {/* Set as Default OTP Modal */}
      <Modal
        visible={showSetDefaultModal}
        transparent
        animationType="fade"
        onRequestClose={closeSetDefaultModal}
      >
        <View style={styles.centeredModalOverlay}>
          <View style={styles.setDefaultModal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Set as Default</Text>
              <TouchableOpacity onPress={closeSetDefaultModal}>
                <Ionicons name="close" size={24} color="#64748B" />
              </TouchableOpacity>
            </View>

            {!otpSent ? (
              <>
                <View style={styles.warningBox}>
                  <Ionicons name="warning-outline" size={24} color="#F59E0B" />
                  <Text style={styles.warningText}>
                    This action will update the default prices in the system. All future calculations will use these new rates.
                  </Text>
                </View>
                <Text style={styles.otpDescription}>
                  Click the button below to receive a verification code on your email.
                </Text>
                <TouchableOpacity
                  style={[styles.otpButton, sendingOtp && styles.otpButtonDisabled]}
                  onPress={() => {
                    console.log('Send Verification Code clicked');
                    sendSetDefaultOtp();
                  }}
                  disabled={sendingOtp}
                  activeOpacity={0.7}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, pointerEvents: 'none' }}>
                    {sendingOtp ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="mail-outline" size={20} color="#fff" />
                        <Text style={styles.otpButtonText}>Send Verification Code</Text>
                      </>
                    )}
                  </View>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={styles.otpSentText}>
                  Verification code sent to {otpEmail}
                </Text>
                <TextInput
                  style={styles.otpInput}
                  placeholder="Enter 4-digit code"
                  value={otpValue}
                  onChangeText={setOtpValue}
                  keyboardType="number-pad"
                  maxLength={4}
                  autoFocus
                />
                <TouchableOpacity
                  style={[styles.otpButton, styles.verifyButton, verifyingOtp && styles.otpButtonDisabled]}
                  onPress={() => {
                    console.log('Verify button pressed');
                    verifyAndSetDefault();
                  }}
                  disabled={verifyingOtp}
                  activeOpacity={0.7}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, pointerEvents: 'none' }}>
                    {verifyingOtp ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="checkmark-circle-outline" size={20} color="#fff" />
                        <Text style={styles.otpButtonText}>Verify & Set as Default</Text>
                      </>
                    )}
                  </View>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.resendButton}
                  onPress={() => {
                    console.log('Resend clicked');
                    setOtpSent(false);
                    setOtpValue('');
                  }}
                  activeOpacity={0.7}
                >
                  <Text style={styles.resendButtonText}>Resend Code</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>

      {/* Create User Modal */}
      <Modal visible={showCreateUser} animationType="slide" transparent>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
          <View style={{ backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '85%' }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <Text style={{ fontSize: 18, fontWeight: '800', color: '#0F172A' }}>Create New User</Text>
              <TouchableOpacity onPress={() => setShowCreateUser(false)} testID="create-user-close">
                <Ionicons name="close" size={24} color="#64748B" />
              </TouchableOpacity>
            </View>
            <ScrollView style={{ maxHeight: 520 }} showsVerticalScrollIndicator={false}>
              <Text style={{ fontSize: 12, color: '#960018', fontWeight: '700', marginTop: 4, marginBottom: 4 }}>Email *</Text>
              <TextInput
                style={{ borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8, padding: 10, fontSize: 14, backgroundColor: '#F8FAFC' }}
                value={newUserEmail} onChangeText={setNewUserEmail}
                placeholder="user@company.com" keyboardType="email-address" autoCapitalize="none"
                testID="cu-email"
              />
              <Text style={{ fontSize: 12, color: '#960018', fontWeight: '700', marginTop: 10, marginBottom: 4 }}>Full Name *</Text>
              <TextInput
                style={{ borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8, padding: 10, fontSize: 14, backgroundColor: '#F8FAFC' }}
                value={newUserName} onChangeText={setNewUserName}
                placeholder="e.g. Ramesh Patel"
                testID="cu-name"
              />
              <Text style={{ fontSize: 12, color: '#960018', fontWeight: '700', marginTop: 10, marginBottom: 4 }}>Password * (min 6 chars)</Text>
              <TextInput
                style={{ borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8, padding: 10, fontSize: 14, backgroundColor: '#F8FAFC' }}
                value={newUserPassword} onChangeText={setNewUserPassword}
                placeholder="Temporary password" secureTextEntry
                testID="cu-password"
              />
              <Text style={{ fontSize: 12, color: '#960018', fontWeight: '700', marginTop: 10, marginBottom: 4 }}>Company (optional)</Text>
              <TextInput
                style={{ borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8, padding: 10, fontSize: 14, backgroundColor: '#F8FAFC' }}
                value={newUserCompany} onChangeText={setNewUserCompany}
                placeholder="e.g. Convero Solutions"
                testID="cu-company"
              />
              <Text style={{ fontSize: 12, color: '#960018', fontWeight: '700', marginTop: 12, marginBottom: 6 }}>Role *</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                {['admin','sales_manager','production_head','accounts','dispatch','customer'].map((r) => {
                  const roleColor: Record<string,string> = {
                    admin:'#DC2626', sales_manager:'#C5964A', production_head:'#0891B2',
                    accounts:'#7C3AED', dispatch:'#059669', customer:'#64748B',
                  };
                  const active = newUserRole === r;
                  return (
                    <TouchableOpacity
                      key={r} onPress={() => setNewUserRole(r)}
                      testID={`cu-role-${r}`}
                      style={{
                        paddingHorizontal: 12, paddingVertical: 8, borderRadius: 16,
                        backgroundColor: active ? roleColor[r] : '#F1F5F9',
                        borderWidth: active ? 0 : 1, borderColor: '#E5E7EB',
                      }}
                    >
                      <Text style={{ fontSize: 12, fontWeight: '700', color: active ? '#fff' : '#475569', textTransform: 'capitalize' }}>
                        {r.replace('_', ' ')}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
              <TouchableOpacity
                onPress={createUser}
                disabled={creatingUser}
                testID="cu-submit"
                style={{ marginTop: 20, backgroundColor: '#960018', paddingVertical: 14, borderRadius: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }}
              >
                {creatingUser ? <ActivityIndicator color="#fff" /> : (
                  <>
                    <Ionicons name="person-add" size={18} color="#fff" />
                    <Text style={{ fontSize: 15, fontWeight: '700', color: '#fff' }}>Create User</Text>
                  </>
                )}
              </TouchableOpacity>
              <View style={{ height: 20 }} />
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
    backgroundColor: '#F0F4F8',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F0F4F8',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#64748B',
  },
  accessDenied: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  accessDeniedText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#0F172A',
    marginTop: 16,
  },
  accessDeniedSubtext: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 8,
  },
  header: {
    backgroundColor: '#0F172A',
    paddingTop: 56,
    paddingBottom: 16,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: -0.3,
    marginBottom: 12,
  },
  mainTabs: {
    flexDirection: 'row',
    gap: 12,
  },
  mainTab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.15)',
    gap: 6,
  },
  mainTabActive: {
    backgroundColor: '#fff',
  },
  mainTabText: {
    fontSize: 14,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.9)',
  },
  mainTabTextActive: {
    color: '#960018',
  },
  categoryTabs: {
    backgroundColor: '#fff',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  categoryTab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginHorizontal: 4,
    borderRadius: 20,
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 6,
  },
  categoryTabActive: {
    backgroundColor: '#960018',
    borderColor: '#960018',
  },
  categoryTabText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#666',
  },
  categoryTabTextActive: {
    color: '#fff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  bearingGroup: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  bearingTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
    marginBottom: 8,
  },
  priceCard: {
    backgroundColor: 'rgba(255,255,255,0.78)',
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.35)',
  },
  priceSectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#C5964A',
    marginBottom: 10,
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f5f5f5',
  },
  priceLabel: {
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  valueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  priceValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  editContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  editInput: {
    width: 100,
    height: 36,
    borderWidth: 1,
    borderColor: '#960018',
    borderRadius: 6,
    paddingHorizontal: 10,
    fontSize: 14,
    backgroundColor: '#fff',
  },
  saveBtn: {
    width: 36,
    height: 36,
    borderRadius: 6,
    backgroundColor: '#34C759',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelBtn: {
    width: 36,
    height: 36,
    borderRadius: 6,
    backgroundColor: '#f0f0f0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  resetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#C41E3A',
    marginTop: 8,
  },
  resetButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#C41E3A',
  },
  bottomSpacer: {
    height: 40,
  },
  savingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255,255,255,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  savingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#333',
  },
  // Standards styles
  standardsTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  standardsSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
  },
  standardsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  collectionCard: {
    width: '47%',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  collectionCardActive: {
    backgroundColor: '#960018',
    borderColor: '#960018',
  },
  collectionName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
    marginTop: 8,
    textAlign: 'center',
  },
  collectionNameActive: {
    color: '#fff',
  },
  collectionCount: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  collectionCountActive: {
    color: 'rgba(255,255,255,0.8)',
  },
  collectionDataContainer: {
    flex: 1,
  },
  collectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  backButton: {
    marginRight: 12,
  },
  collectionTitle: {
    flex: 1,
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  collectionItemCount: {
    fontSize: 14,
    color: '#666',
  },
  dataList: {
    padding: 16,
  },
  dataRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 10,
    marginBottom: 8,
  },
  dataRowContent: {
    flex: 1,
  },
  dataRowLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
  },
  dataRowValue: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  readOnlyNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF9E6',
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  readOnlyText: {
    fontSize: 13,
    color: '#666',
    flex: 1,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  centeredModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
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
  detailRow: {
    marginBottom: 16,
  },
  detailKey: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 15,
    color: '#333',
  },
  // Data row action buttons
  dataRowActions: {
    flexDirection: 'row',
    gap: 8,
  },
  editBtn: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#FFF0F0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteBtn: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#FFF0F0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  // Modal footer
  modalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E5E5EA',
    gap: 12,
  },
  modalEditBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 6,
  },
  modalEditBtnText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
  },
  modalDeleteBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF0F0',
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#C41E3A',
    gap: 6,
  },
  modalDeleteBtnText: {
    color: '#C41E3A',
    fontWeight: '600',
    fontSize: 15,
  },
  // Edit modal styles
  editFieldContainer: {
    marginBottom: 16,
  },
  editFieldLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    marginBottom: 6,
  },
  editFieldInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    backgroundColor: '#f9f9f9',
    minHeight: 44,
  },
  cancelButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  cancelButtonText: {
    color: '#666',
    fontWeight: '600',
    fontSize: 15,
  },
  saveButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#34C759',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 6,
  },
  saveButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
  },
  // Import/Export styles
  importExportContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 20,
    marginBottom: 10,
    gap: 12,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 10,
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  // Set as Default Modal Styles
  setDefaultModal: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '90%',
    maxWidth: 400,
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#FEF3C7',
    padding: 16,
    borderRadius: 12,
    marginBottom: 20,
    gap: 12,
    alignItems: 'flex-start',
  },
  warningText: {
    flex: 1,
    fontSize: 14,
    color: '#92400E',
    lineHeight: 20,
  },
  otpDescription: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    marginBottom: 20,
  },
  otpButton: {
    flexDirection: 'row',
    backgroundColor: '#960018',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  otpButtonDisabled: {
    opacity: 0.6,
  },
  otpButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  verifyButton: {
    backgroundColor: '#217346',
  },
  otpSentText: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    marginBottom: 16,
  },
  otpInput: {
    borderWidth: 2,
    borderColor: '#E2E8F0',
    borderRadius: 12,
    padding: 16,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: 8,
    marginBottom: 20,
    color: '#0F172A',
  },
  resendButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  resendButtonText: {
    color: '#960018',
    fontSize: 14,
    fontWeight: '600',
  },
});
