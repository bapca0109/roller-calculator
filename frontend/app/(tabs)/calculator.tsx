import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';

// Attachment interface
interface Attachment {
  uri: string;
  name: string;
  type: string;
  base64?: string;
}

interface RollerStandards {
  pipe_diameters: number[];
  shaft_diameters: number[];
  bearing_options: { [key: string]: string[] };
  roller_lengths_by_belt_width: { [key: string]: number[] };
}

interface CostResult {
  configuration: {
    product_code: string;
    roller_type: string;
    pipe_diameter_mm: number;
    pipe_length_mm: number;
    pipe_type: string;
    shaft_diameter_mm: number;
    shaft_length_mm: number;
    bearing: string;
    bearing_make: string;
    housing: string;
    rubber_diameter_mm?: number;
    quantity: number;
  };
  cost_breakdown: {
    pipe_cost: number;
    shaft_cost: number;
    bearing_cost: number;
    housing_cost: number;
    seal_cost: number;
    circlip_cost: number;
    rubber_cost?: number;
    locking_ring_cost?: number;
    total_raw_material: number;
  };
  pricing: {
    raw_material_cost: number;
    layout_cost: number;
    profit: number;
    unit_price: number;
    quantity: number;
    order_value: number;
    discount_percent: number;
    discount_amount: number;
    price_after_discount: number;
    packing_type: string;
    packing_percent: number;
    packing_charges: number;
    final_price: number;
  };
  freight?: {
    destination_pincode: string;
    dispatch_pincode: string;
    distance_km: number;
    single_roller_weight_kg: number;
    total_weight_kg: number;
    freight_rate_per_kg: number;
    freight_charges: number;
  };
  gst?: {
    taxable_amount: number;
    gst_type: string;
    cgst_rate: number;
    cgst_amount: number;
    sgst_rate: number;
    sgst_amount: number;
    igst_rate: number;
    igst_amount: number;
    total_gst: number;
    destination_state: string;
    is_same_state: boolean;
  };
  grand_total: number;
}

const PIPE_TYPES = [
  { label: 'Type A (Light)', value: 'A' },
  { label: 'Type B (Medium)', value: 'B' },
  { label: 'Type C (Heavy)', value: 'C' },
];

const BEARING_MAKES = [
  { label: 'China', value: 'china' },
  { label: 'SKF', value: 'skf' },
  { label: 'FAG', value: 'fag' },
  { label: 'Timken', value: 'timken' },
];

const PACKING_TYPES = [
  { label: 'No Packing', value: 'none' },
  { label: 'Standard (1%)', value: 'standard' },
  { label: 'Pallet (4%)', value: 'pallet' },
  { label: 'Wooden Box (8%)', value: 'wooden_box' },
];

const RUBBER_DIAMETERS: { [key: number]: number[] } = {
  60.8: [90, 114],
  76.1: [114, 127, 140],
  88.9: [127, 140, 152],
  114.3: [139, 152, 165, 190],
  127.0: [165, 190],
  139.7: [165, 190],
  152.4: [190],
};

export default function CalculatorScreen() {
  const { user, loading: authLoading } = useAuth();
  const isCustomer = user?.role === 'customer';
  const [standards, setStandards] = useState<RollerStandards | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Debug: Log user state on every render
  console.log('CalculatorScreen render - user:', user, 'role:', user?.role, 'isCustomer:', isCustomer);
  
  // RFQ popup state for customers
  const [showRfqPopup, setShowRfqPopup] = useState(false);
  const [showRfqSuccessPopup, setShowRfqSuccessPopup] = useState(false);
  const [submittedRfqNumber, setSubmittedRfqNumber] = useState('');
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState<CostResult | null>(null);
  const [savingQuote, setSavingQuote] = useState(false);
  const [quoteItems, setQuoteItems] = useState<CostResult[]>([]);
  const [showQuoteBuilder, setShowQuoteBuilder] = useState(false);
  
  // Customer attachment state
  const [currentAttachments, setCurrentAttachments] = useState<Attachment[]>([]);
  const [itemAttachments, setItemAttachments] = useState<{[key: number]: Attachment[]}>({});
  
  // Customer selection state
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [showCustomerPicker, setShowCustomerPicker] = useState(false);
  
  // GST Lookup state (for calculator)
  const [showGstLookup, setShowGstLookup] = useState(false);
  const [gstinInput, setGstinInput] = useState('');
  const [captchaData, setCaptchaData] = useState<any>(null);
  const [captchaInput, setCaptchaInput] = useState('');
  const [gstLoading, setGstLoading] = useState(false);
  const [gstVerifying, setGstVerifying] = useState(false);

  // Form state
  const [rollerType, setRollerType] = useState<'carrying' | 'impact' | 'return'>('carrying');
  const [pipeDiameter, setPipeDiameter] = useState<number>(88.9);
  const [pipeLength, setPipeLength] = useState<string>('1000');
  const [pipeType, setPipeType] = useState<string>('B');
  const [shaftDiameter, setShaftDiameter] = useState<number>(25);
  const [bearingNumber, setBearingNumber] = useState<string>('');
  const [bearingMake, setBearingMake] = useState<string>('china');
  const [rubberDiameter, setRubberDiameter] = useState<number | null>(null);
  const [quantity, setQuantity] = useState<string>('1');
  const [packingType, setPackingType] = useState<string>('none');
  const [freightPincode, setFreightPincode] = useState<string>('');
  
  // Shaft end type state
  const [shaftEndType, setShaftEndType] = useState<string>('B');
  const [customShaftExtension, setCustomShaftExtension] = useState<string>('');
  
  // Custom discount state
  const [customDiscount, setCustomDiscount] = useState<string>('');
  const [useCustomDiscount, setUseCustomDiscount] = useState(false);
  
  // Drawing generation state
  const [generatingDrawing, setGeneratingDrawing] = useState(false);

  // Error state
  const [errors, setErrors] = useState<{
    pipeLength?: string;
    quantity?: string;
    freightPincode?: string;
    customShaftExtension?: string;
  }>({});

  useEffect(() => {
    fetchStandards();
    fetchCustomers();
  }, []);
  
  const fetchCustomers = async () => {
    try {
      const response = await api.get('/customers');
      setCustomers(response.data.customers || []);
    } catch (error) {
      console.log('Failed to fetch customers');
    }
  };

  // GST Lookup functions for calculator
  const fetchGstCaptcha = async () => {
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

  const openGstLookupFromCalculator = () => {
    setGstinInput('');
    setCaptchaData(null);
    setCaptchaInput('');
    setExistingGstCustomer(null);
    setShowCustomerPicker(false);
    setShowGstLookup(true);
  };

  // State for existing customer found by GSTIN
  const [existingGstCustomer, setExistingGstCustomer] = useState<any>(null);
  const [searchingGstin, setSearchingGstin] = useState(false);

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

  // Handle GSTIN input change with debounced search
  const handleGstinInputChange = (text: string) => {
    const upperText = text.toUpperCase();
    setGstinInput(upperText);
    if (upperText.length === 15) {
      searchGstinInDatabase(upperText);
    } else {
      setExistingGstCustomer(null);
    }
  };

  // Select existing customer from GSTIN search
  const selectExistingGstCustomer = () => {
    if (existingGstCustomer) {
      setSelectedCustomer(existingGstCustomer);
      setShowGstLookup(false);
      Alert.alert('Customer Selected', `"${existingGstCustomer.name}" has been selected.`);
    }
  };

  const verifyGstinFromCalculator = async () => {
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
        // Create customer from GST data and save
        const customerResponse = await api.post('/customers/from-gst', response.data);
        
        if (customerResponse.data.customer) {
          // Refresh customers list and select the new customer
          await fetchCustomers();
          setSelectedCustomer(customerResponse.data.customer);
          setShowGstLookup(false);
          Alert.alert('Success', `Customer "${gstData.trade_name || gstData.legal_name}" created and selected!`);
        }
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Verification failed';
      if (errorMsg.includes('already exists')) {
        Alert.alert('Customer Exists', errorMsg);
      } else {
        Alert.alert('Verification Failed', errorMsg);
      }
      // Refresh captcha on failure
      fetchGstCaptcha();
      setCaptchaInput('');
    } finally {
      setGstVerifying(false);
    }
  };

  useEffect(() => {
    // Auto-select first bearing when shaft diameter changes
    if (standards && shaftDiameter) {
      const bearings = standards.bearing_options[shaftDiameter.toString()];
      if (bearings && bearings.length > 0) {
        setBearingNumber(bearings[0]);
      }
    }
  }, [shaftDiameter, standards]);

  useEffect(() => {
    // Auto-select rubber diameter for impact rollers
    if (rollerType === 'impact' && pipeDiameter) {
      const rubberOptions = RUBBER_DIAMETERS[pipeDiameter];
      if (rubberOptions && rubberOptions.length > 0) {
        setRubberDiameter(rubberOptions[0]);
      } else {
        setRubberDiameter(null);
      }
    } else {
      setRubberDiameter(null);
    }
  }, [rollerType, pipeDiameter]);

  const fetchStandards = async () => {
    try {
      const response = await api.get('/roller-standards');
      setStandards(response.data);
      // Set default bearing
      if (response.data.bearing_options['25']) {
        setBearingNumber(response.data.bearing_options['25'][0]);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to load roller standards');
    } finally {
      setLoading(false);
    }
  };

  // Validation functions
  const validatePipeLength = (value: string) => {
    if (!value || value.trim() === '') {
      return 'Pipe length is required';
    }
    const num = parseInt(value);
    if (isNaN(num) || num <= 0) {
      return 'Enter a valid length (greater than 0)';
    }
    if (num < 100) {
      return 'Minimum length is 100mm';
    }
    if (num > 3000) {
      return 'Maximum length is 3000mm';
    }
    return '';
  };

  const validateQuantity = (value: string) => {
    if (!value || value.trim() === '') {
      return 'Quantity is required';
    }
    const num = parseInt(value);
    if (isNaN(num) || num <= 0) {
      return 'Enter a valid quantity (greater than 0)';
    }
    if (num > 100000) {
      return 'Maximum quantity is 100,000';
    }
    return '';
  };

  const validatePincode = (value: string) => {
    if (!value || value.trim() === '') {
      return ''; // Pincode is optional
    }
    if (!/^\d{6}$/.test(value)) {
      return 'Enter valid 6-digit pincode';
    }
    return '';
  };

  const handlePipeLengthChange = (value: string) => {
    setPipeLength(value);
    const error = validatePipeLength(value);
    setErrors(prev => ({ ...prev, pipeLength: error }));
  };

  const handleQuantityChange = (value: string) => {
    setQuantity(value);
    const error = validateQuantity(value);
    setErrors(prev => ({ ...prev, quantity: error }));
  };

  const handlePincodeChange = (value: string) => {
    setFreightPincode(value);
    const error = validatePincode(value);
    setErrors(prev => ({ ...prev, freightPincode: error }));
  };

  // ========== ATTACHMENT FUNCTIONS ==========
  
  // Pick image from camera or gallery
  const pickImage = async () => {
    try {
      // Request permissions
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Please allow access to photos to attach images.');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.7,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        let base64Data = asset.base64;
        
        // If base64 is not available (web), try to fetch and convert
        if (!base64Data && asset.uri) {
          try {
            // For web, fetch the blob and convert to base64
            if (Platform.OS === 'web') {
              const response = await fetch(asset.uri);
              const blob = await response.blob();
              base64Data = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                  const dataUrl = reader.result as string;
                  // Remove the data:image/xxx;base64, prefix
                  resolve(dataUrl.split(',')[1]);
                };
                reader.readAsDataURL(blob);
              });
            } else {
              // For native, use FileSystem
              const fileInfo = await FileSystem.readAsStringAsync(asset.uri, {
                encoding: FileSystem.EncodingType.Base64,
              });
              base64Data = fileInfo;
            }
          } catch (e) {
            console.log('Failed to convert to base64:', e);
          }
        }
        
        const newAttachment: Attachment = {
          uri: asset.uri,
          name: asset.fileName || `image_${Date.now()}.jpg`,
          type: 'image',
          base64: base64Data,
        };
        setCurrentAttachments([...currentAttachments, newAttachment]);
        
        console.log('Attachment added:', newAttachment.name, 'has base64:', !!base64Data);
      }
    } catch (error) {
      console.log('Image picker error:', error);
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  // Take photo with camera
  const takePhoto = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Please allow camera access to take photos.');
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: false,
        quality: 0.7,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        let base64Data = asset.base64;
        
        // If base64 is not available (web), try to fetch and convert
        if (!base64Data && asset.uri) {
          try {
            if (Platform.OS === 'web') {
              const response = await fetch(asset.uri);
              const blob = await response.blob();
              base64Data = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                  const dataUrl = reader.result as string;
                  resolve(dataUrl.split(',')[1]);
                };
                reader.readAsDataURL(blob);
              });
            } else {
              const fileInfo = await FileSystem.readAsStringAsync(asset.uri, {
                encoding: FileSystem.EncodingType.Base64,
              });
              base64Data = fileInfo;
            }
          } catch (e) {
            console.log('Failed to convert to base64:', e);
          }
        }
        
        const newAttachment: Attachment = {
          uri: asset.uri,
          name: `photo_${Date.now()}.jpg`,
          type: 'image',
          base64: base64Data,
        };
        setCurrentAttachments([...currentAttachments, newAttachment]);
        console.log('Photo added:', newAttachment.name, 'has base64:', !!base64Data);
      }
    } catch (error) {
      console.log('Camera error:', error);
      Alert.alert('Error', 'Failed to take photo');
    }
  };

  // Pick document/file
  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/*', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        const newAttachment: Attachment = {
          uri: asset.uri,
          name: asset.name,
          type: 'document',
        };
        setCurrentAttachments([...currentAttachments, newAttachment]);
      }
    } catch (error) {
      console.log('Document picker error:', error);
      Alert.alert('Error', 'Failed to pick document');
    }
  };

  // Remove attachment
  const removeAttachment = (index: number) => {
    const updated = [...currentAttachments];
    updated.splice(index, 1);
    setCurrentAttachments(updated);
  };

  // Show attachment picker options
  const showAttachmentOptions = () => {
    Alert.alert(
      'Attach File',
      'Choose an option',
      [
        { text: 'Take Photo', onPress: takePhoto },
        { text: 'Choose from Gallery', onPress: pickImage },
        { text: 'Choose Document', onPress: pickDocument },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const calculateCost = async () => {
    // Validate all fields
    const pipeLengthError = validatePipeLength(pipeLength);
    const quantityError = validateQuantity(quantity);
    const pincodeError = validatePincode(freightPincode);

    setErrors({
      pipeLength: pipeLengthError,
      quantity: quantityError,
      freightPincode: pincodeError,
    });

    // If any errors, don't proceed
    if (pipeLengthError || quantityError || pincodeError) {
      return null;
    }

    setCalculating(true);
    setResult(null);

    try {
      const payload: any = {
        roller_type: rollerType,
        pipe_diameter: pipeDiameter,
        pipe_length: parseInt(pipeLength),
        shaft_diameter: shaftDiameter,
        bearing_number: bearingNumber,
        bearing_make: bearingMake,
        pipe_type: pipeType,
        quantity: parseInt(quantity),
        packing_type: packingType,
        shaft_end_type: shaftEndType,
      };

      // Add custom shaft length if custom type selected (user enters total shaft length)
      if (shaftEndType === 'custom' && customShaftExtension) {
        payload.custom_shaft_length = parseInt(customShaftExtension);
      }

      if (rollerType === 'impact' && rubberDiameter) {
        payload.rubber_diameter = rubberDiameter;
      }

      if (freightPincode && freightPincode.length === 6) {
        payload.freight_pincode = freightPincode;
      }

      const response = await api.post('/calculate-detailed-cost', payload);
      setResult(response.data);
      return response.data; // Return the result for direct use
    } catch (error: any) {
      Alert.alert('Calculation Error', error.response?.data?.detail || 'Failed to calculate cost');
      return null;
    } finally {
      setCalculating(false);
    }
  };

  const saveQuote = async () => {
    if (!result) return;

    setSavingQuote(true);
    try {
      const customerDetails = selectedCustomer ? {
        name: selectedCustomer.name,
        company: selectedCustomer.company,
        email: selectedCustomer.email,
        phone: selectedCustomer.phone,
        address: selectedCustomer.address,
        city: selectedCustomer.city,
        state: selectedCustomer.state,
        pincode: selectedCustomer.pincode,
        gst_number: selectedCustomer.gst_number,
      } : null;

      const response = await api.post('/quotes/roller', {
        customer_name: selectedCustomer?.name || user?.name || 'Customer',
        customer_id: selectedCustomer?.id || null,
        customer_details: customerDetails,
        configuration: result.configuration,
        cost_breakdown: result.cost_breakdown,
        pricing: result.pricing,
        freight: result.freight,
        grand_total: result.grand_total,
        notes: `Roller: ${result.configuration.product_code}`
      });
      
      Alert.alert(
        'Quote Saved!', 
        `Quote Number: ${response.data.quote_number}\nCustomer: ${selectedCustomer?.name || 'N/A'}\nTotal: Rs. ${response.data.total_price.toFixed(2)}`,
        [{ text: 'OK' }]
      );
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save quote');
    } finally {
      setSavingQuote(false);
    }
  };

  // Download Drawing function
  const downloadDrawing = async () => {
    if (!result) return;
    
    setGeneratingDrawing(true);
    try {
      const config = result.configuration;
      
      // Step 1: Get token
      const token = await AsyncStorage.getItem('token');
      if (!token) {
        Alert.alert('Error', 'Not authenticated. Please login again.');
        return;
      }
      
      const requestBody = {
        product_code: config.product_code,
        roller_type: rollerType,
        pipe_diameter: config.pipe_diameter,
        pipe_length: config.pipe_length,
        pipe_type: config.pipe_type,
        shaft_diameter: config.shaft_diameter,
        bearing: config.bearing_number,
        bearing_make: config.bearing_make,
        housing: config.housing,
        weight_kg: result.cost_breakdown.total_weight || 0,
        unit_price: result.pricing.unit_price,
        rubber_diameter: config.rubber_diameter || null,
        belt_widths: [],
        quantity: config.quantity
      };

      // Step 2: Fetch PDF as base64
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
      const response = await fetch(`${backendUrl}/api/generate-drawing-base64`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        Alert.alert('Error', `Server error: ${response.status}`);
        return;
      }

      // Step 3: Parse JSON
      const data = await response.json();
      if (!data.base64) {
        Alert.alert('Error', 'No PDF data received');
        return;
      }

      // Step 4: Write file
      const filename = `Drawing_${config.product_code.replace(/ /g, '_').replace(/\//g, '-')}.pdf`;
      const fileUri = FileSystem.documentDirectory + filename;

      await FileSystem.writeAsStringAsync(fileUri, data.base64, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Step 5: Check file exists
      const fileInfo = await FileSystem.getInfoAsync(fileUri);
      if (!fileInfo.exists) {
        Alert.alert('Error', 'Failed to save file');
        return;
      }

      // Step 6: Share file
      const sharingAvailable = await Sharing.isAvailableAsync();
      if (sharingAvailable) {
        await Sharing.shareAsync(fileUri, {
          mimeType: 'application/pdf',
          dialogTitle: `Drawing: ${config.product_code}`,
          UTI: 'com.adobe.pdf'
        });
      } else {
        Alert.alert('Success', `Drawing saved to: ${filename}`);
      }
    } catch (error: any) {
      console.error('Drawing error:', error);
      Alert.alert('Error', `Failed: ${error.message || String(error)}`);
    } finally {
      setGeneratingDrawing(false);
    }
  };

  const addToQuote = () => {
    if (!result) return;
    setQuoteItems([...quoteItems, result]);
    Alert.alert('Added!', `${result.configuration.product_code} added to quote.\nItems in quote: ${quoteItems.length + 1}`);
    setResult(null); // Clear current result to configure next item
  };

  const removeFromQuote = (index: number) => {
    const newItems = [...quoteItems];
    newItems.splice(index, 1);
    setQuoteItems(newItems);
  };

  const getQuoteTotal = () => {
    return quoteItems.reduce((sum, item) => sum + item.grand_total, 0);
  };

  const saveMultiProductQuote = async () => {
    if (quoteItems.length === 0) {
      Alert.alert('Error', 'No items in quote');
      return null;
    }

    setSavingQuote(true);
    try {
      const products = quoteItems.map((item, index) => ({
        product_id: item.configuration.product_code,
        product_name: `${item.configuration.roller_type.charAt(0).toUpperCase() + item.configuration.roller_type.slice(1)} Roller - ${item.configuration.product_code}`,
        quantity: item.configuration.quantity,
        unit_price: item.pricing.unit_price,
        specifications: {
          pipe_diameter: item.configuration.pipe_diameter_mm,
          pipe_length: item.configuration.pipe_length_mm,
          pipe_type: item.configuration.pipe_type,
          shaft_diameter: item.configuration.shaft_diameter_mm,
          bearing: item.configuration.bearing,
          bearing_make: item.configuration.bearing_make,
          housing: item.configuration.housing,
          rubber_diameter: item.configuration.rubber_diameter_mm
        },
        calculated_discount: item.pricing.discount_amount,
        custom_premium: 0,
        // Include attachments with base64 data
        attachments: item.attachments?.map((att: Attachment) => ({
          name: att.name,
          type: att.type,
          base64: att.base64 || null,
        })) || []
      }));

      const response = await api.post('/quotes', {
        products,
        delivery_location: quoteItems[0].freight?.destination_pincode || null,
        notes: `Multi-product quote with ${quoteItems.length} items`
      });
      
      // For customers, don't show the default alert - let the caller handle it
      if (!isCustomer) {
        Alert.alert(
          'Quote Saved!', 
          `Quote ID: ${response.data.id}\nTotal Items: ${quoteItems.length}\nTotal: Rs. ${response.data.total_price.toFixed(2)}`,
          [{ text: 'OK', onPress: () => {
            setQuoteItems([]);
            setShowQuoteBuilder(false);
          }}]
        );
      }
      
      return response.data; // Return the response for caller to use
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save quote');
      return null;
    } finally {
      setSavingQuote(false);
    }
  };

  const availableBearings = standards?.bearing_options[shaftDiameter.toString()] || [];
  const availableRubberDiameters = RUBBER_DIAMETERS[pipeDiameter] || [];

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading standards...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoContainer}>
            <Image 
              source={{ uri: 'https://static.wixstatic.com/media/d714c4_0d70a3cab7694564bc644161f285e30a~mv2.png/v1/fill/w_305,h_98,al_c,q_85,enc_auto/VISITING%20CARD%20LOGO.png' }} 
              style={styles.headerLogo}
              resizeMode="contain"
            />
          </View>
          <Text style={styles.headerTitle}>Roller Calculator</Text>
          <Text style={styles.headerSubtitle}>Configure your conveyor roller</Text>
        </View>

        {/* Roller Type Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Roller Type</Text>
          <View style={styles.toggleContainer}>
            <TouchableOpacity
              style={[
                styles.toggleButton,
                rollerType === 'carrying' && styles.toggleButtonActive,
              ]}
              onPress={() => setRollerType('carrying')}
            >
              <Ionicons
                name="disc-outline"
                size={20}
                color={rollerType === 'carrying' ? '#fff' : '#666'}
              />
              <Text
                style={[
                  styles.toggleText,
                  rollerType === 'carrying' && styles.toggleTextActive,
                ]}
              >
                Carrying
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.toggleButton,
                rollerType === 'impact' && styles.toggleButtonActive,
              ]}
              onPress={() => setRollerType('impact')}
            >
              <Ionicons
                name="radio-button-on-outline"
                size={20}
                color={rollerType === 'impact' ? '#fff' : '#666'}
              />
              <Text
                style={[
                  styles.toggleText,
                  rollerType === 'impact' && styles.toggleTextActive,
                ]}
              >
                Impact
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.toggleButton,
                rollerType === 'return' && styles.toggleButtonActive,
              ]}
              onPress={() => setRollerType('return')}
            >
              <Ionicons
                name="sync-outline"
                size={20}
                color={rollerType === 'return' ? '#fff' : '#666'}
              />
              <Text
                style={[
                  styles.toggleText,
                  rollerType === 'return' && styles.toggleTextActive,
                ]}
              >
                Return
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Pipe Configuration */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pipe Configuration</Text>
          
          <Text style={styles.label}>Pipe Diameter (IS-9295)</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={pipeDiameter}
              onValueChange={(value) => setPipeDiameter(value)}
              style={styles.picker}
            >
              {standards?.pipe_diameters.map((dia) => (
                <Picker.Item key={dia} label={`${dia} mm`} value={dia} />
              ))}
            </Picker>
          </View>

          <Text style={styles.label}>Pipe Length (mm)</Text>
          <TextInput
            style={[styles.input, errors.pipeLength ? styles.inputError : null]}
            value={pipeLength}
            onChangeText={handlePipeLengthChange}
            keyboardType="numeric"
            placeholder="Enter pipe length (100-3000mm)"
          />
          {errors.pipeLength ? (
            <Text style={styles.errorText}>{errors.pipeLength}</Text>
          ) : null}

          <Text style={styles.label}>Pipe Thickness (IS-9295)</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={pipeType}
              onValueChange={(value) => setPipeType(value)}
              style={styles.picker}
            >
              {PIPE_TYPES.map((type) => (
                <Picker.Item key={type.value} label={type.label} value={type.value} />
              ))}
            </Picker>
          </View>
        </View>

        {/* Shaft & Bearing */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Shaft & Bearing</Text>

          <Text style={styles.label}>Shaft Diameter</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={shaftDiameter}
              onValueChange={(value) => setShaftDiameter(value)}
              style={styles.picker}
            >
              {standards?.shaft_diameters.map((dia) => (
                <Picker.Item key={dia} label={`${dia} mm`} value={dia} />
              ))}
            </Picker>
          </View>

          <Text style={styles.label}>Shaft End Type</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={shaftEndType}
              onValueChange={(value) => setShaftEndType(value)}
              style={styles.picker}
            >
              <Picker.Item label="Type A (+26mm)" value="A" />
              <Picker.Item label="Type B (+36mm)" value="B" />
              <Picker.Item label="Type C (+56mm)" value="C" />
              <Picker.Item label="Custom" value="custom" />
            </Picker>
          </View>

          {shaftEndType === 'custom' && (
            <View style={styles.inputRow}>
              <Text style={styles.label}>Total Shaft Length (mm)</Text>
              <TextInput
                style={[styles.input, errors.customShaftExtension ? styles.inputError : null]}
                value={customShaftExtension}
                onChangeText={(value) => {
                  setCustomShaftExtension(value);
                  const pipeLengthNum = parseInt(pipeLength) || 200;
                  const shaftLen = parseInt(value);
                  if (value && (isNaN(shaftLen) || shaftLen <= pipeLengthNum || shaftLen > pipeLengthNum + 200)) {
                    setErrors(prev => ({ ...prev, customShaftExtension: `Enter value between ${pipeLengthNum + 10} - ${pipeLengthNum + 200}mm` }));
                  } else {
                    setErrors(prev => ({ ...prev, customShaftExtension: '' }));
                  }
                }}
                placeholder={`e.g. ${(parseInt(pipeLength) || 200) + 50}`}
                keyboardType="numeric"
              />
              {errors.customShaftExtension ? (
                <Text style={styles.errorText}>{errors.customShaftExtension}</Text>
              ) : null}
            </View>
          )}

          <Text style={styles.label}>Bearing Number</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={bearingNumber}
              onValueChange={(value) => setBearingNumber(value)}
              style={styles.picker}
            >
              {availableBearings.map((bearing) => (
                <Picker.Item key={bearing} label={bearing} value={bearing} />
              ))}
            </Picker>
          </View>

          <Text style={styles.label}>Bearing Make</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={bearingMake}
              onValueChange={(value) => setBearingMake(value)}
              style={styles.picker}
            >
              {BEARING_MAKES.map((make) => (
                <Picker.Item key={make.value} label={make.label} value={make.value} />
              ))}
            </Picker>
          </View>
        </View>

        {/* Impact Roller Options - Always show when Impact is selected */}
        {rollerType === 'impact' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Rubber Lagging</Text>
            <Text style={styles.label}>Rubber Diameter</Text>
            {availableRubberDiameters.length > 0 ? (
              <View style={styles.pickerContainer}>
                <Picker
                  selectedValue={rubberDiameter}
                  onValueChange={(value) => setRubberDiameter(value)}
                  style={styles.picker}
                >
                  {availableRubberDiameters.map((dia) => (
                    <Picker.Item key={dia} label={`${dia} mm`} value={dia} />
                  ))}
                </Picker>
              </View>
            ) : (
              <View style={styles.noOptionsContainer}>
                <Text style={styles.noOptionsText}>
                  No rubber options available for {pipeDiameter}mm pipe
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Quantity & Packing */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quantity & Packing</Text>

          <Text style={styles.label}>Quantity</Text>
          <TextInput
            style={[styles.input, errors.quantity ? styles.inputError : null]}
            value={quantity}
            onChangeText={handleQuantityChange}
            keyboardType="numeric"
            placeholder="Number of rollers"
          />
          {errors.quantity ? (
            <Text style={styles.errorText}>{errors.quantity}</Text>
          ) : null}

          <Text style={styles.label}>Packing Type</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={packingType}
              onValueChange={(value) => setPackingType(value)}
              style={styles.picker}
            >
              {PACKING_TYPES.map((type) => (
                <Picker.Item key={type.value} label={type.label} value={type.value} />
              ))}
            </Picker>
          </View>
        </View>

        {/* Freight */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Freight (Optional)</Text>
          <Text style={styles.label}>Destination Pincode</Text>
          <TextInput
            style={[styles.input, errors.freightPincode ? styles.inputError : null]}
            value={freightPincode}
            onChangeText={handlePincodeChange}
            keyboardType="numeric"
            placeholder="Enter 6-digit pincode"
            maxLength={6}
          />
          {errors.freightPincode ? (
            <Text style={styles.errorText}>{errors.freightPincode}</Text>
          ) : (
            <Text style={styles.hint}>Dispatch from: 382433 (Gujarat)</Text>
          )}
        </View>

        {/* Attachment Section - Customer Only */}
        {isCustomer && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Attachments (Optional)</Text>
            <Text style={styles.hint}>Attach drawing, photo, or document for this item</Text>
            
            {/* Attachment Buttons */}
            <View style={styles.attachmentButtons}>
              <TouchableOpacity style={styles.attachmentBtn} onPress={takePhoto}>
                <Ionicons name="camera" size={24} color="#960018" />
                <Text style={styles.attachmentBtnText}>Camera</Text>
              </TouchableOpacity>
              
              <TouchableOpacity style={styles.attachmentBtn} onPress={pickImage}>
                <Ionicons name="image" size={24} color="#960018" />
                <Text style={styles.attachmentBtnText}>Gallery</Text>
              </TouchableOpacity>
              
              <TouchableOpacity style={styles.attachmentBtn} onPress={pickDocument}>
                <Ionicons name="document" size={24} color="#960018" />
                <Text style={styles.attachmentBtnText}>File</Text>
              </TouchableOpacity>
            </View>
            
            {/* Display Attachments */}
            {currentAttachments.length > 0 && (
              <View style={styles.attachmentList}>
                {currentAttachments.map((attachment, index) => (
                  <View key={index} style={styles.attachmentItem}>
                    {attachment.type === 'image' ? (
                      <Image source={{ uri: attachment.uri }} style={styles.attachmentThumbnail} />
                    ) : (
                      <View style={styles.attachmentDocIcon}>
                        <Ionicons name="document-text" size={32} color="#960018" />
                      </View>
                    )}
                    <Text style={styles.attachmentName} numberOfLines={1}>{attachment.name}</Text>
                    <TouchableOpacity 
                      style={styles.removeAttachmentBtn}
                      onPress={() => removeAttachment(index)}
                    >
                      <Ionicons name="close-circle" size={24} color="#E53935" />
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Calculate Button */}
        <TouchableOpacity
          style={[styles.calculateButton, calculating && styles.calculateButtonDisabled]}
          onPress={async () => {
            if (isCustomer) {
              // For customers: calculate, add to cart with attachments, and show popup
              const calcResult = await calculateCost();
              if (calcResult) {
                // Add attachments to the result
                const itemWithAttachments = {
                  ...calcResult,
                  attachments: currentAttachments,
                };
                // Add the calculated item directly to quote items
                setQuoteItems([...quoteItems, itemWithAttachments]);
                // Store attachments by index
                setItemAttachments({
                  ...itemAttachments,
                  [quoteItems.length]: currentAttachments
                });
                // Clear current attachments for next item
                setCurrentAttachments([]);
                setShowRfqPopup(true);
                setResult(null); // Don't show result section
              }
            } else {
              // For admin: just calculate and show results
              await calculateCost();
            }
          }}
          disabled={calculating}
        >
          {calculating ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name={isCustomer ? "document-text" : "calculator"} size={24} color="#fff" />
              <Text style={styles.calculateButtonText}>{isCustomer ? 'Generate RFQ' : 'Calculate Price'}</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Results - Only for Admin */}
        {result && !isCustomer && (
          <View style={styles.resultsContainer}>
            {/* Product Code */}
            <View style={styles.productCodeCard}>
              <Text style={styles.productCodeLabel}>Product Code</Text>
              <Text style={styles.productCode}>{result.configuration.product_code}</Text>
            </View>

            {/* Configuration Summary - Hide for customers */}
            {!isCustomer && (
            <View style={styles.resultCard}>
              <Text style={styles.resultCardTitle}>Configuration</Text>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Type</Text>
                <Text style={styles.resultValue}>
                  {result.configuration.roller_type === 'impact' ? 'Impact Roller' : 
                   result.configuration.roller_type === 'return' ? 'Return Roller' : 'Carrying Roller'}
                </Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Pipe</Text>
                <Text style={styles.resultValue}>
                  {result.configuration.pipe_diameter_mm}mm x {result.configuration.pipe_length_mm}mm (Type {result.configuration.pipe_type})
                </Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Shaft</Text>
                <Text style={styles.resultValue}>
                  {result.configuration.shaft_diameter_mm}mm x {result.configuration.shaft_length_mm}mm
                </Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Bearing</Text>
                <Text style={styles.resultValue}>
                  {result.configuration.bearing} ({result.configuration.bearing_make.toUpperCase()})
                </Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Housing</Text>
                <Text style={styles.resultValue}>{result.configuration.housing}</Text>
              </View>
              {result.configuration.rubber_diameter_mm && (
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Rubber</Text>
                  <Text style={styles.resultValue}>{result.configuration.rubber_diameter_mm}mm</Text>
                </View>
              )}
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Quantity</Text>
                <Text style={styles.resultValue}>{result.configuration.quantity} pcs</Text>
              </View>
            </View>
            )}

            {/* Cost Breakdown - Admin Only */}
            {user?.role === 'admin' && (
            <View style={styles.resultCard}>
              <Text style={styles.resultCardTitle}>Cost Breakdown (Per Roller) - Admin View</Text>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Pipe</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.pipe_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Shaft (1 pc)</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.shaft_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Bearings (2 pcs)</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.bearing_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Housing (2 pcs)</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.housing_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Seals (2 sets)</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.seal_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Circlips (4 pcs)</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.circlip_cost.toFixed(2)}</Text>
              </View>
              {result.cost_breakdown.rubber_cost !== undefined && (
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Rubber Rings</Text>
                  <Text style={styles.resultValue}>Rs. {result.cost_breakdown.rubber_cost.toFixed(2)}</Text>
                </View>
              )}
              {result.cost_breakdown.locking_ring_cost !== undefined && (
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Locking Ring</Text>
                  <Text style={styles.resultValue}>Rs. {result.cost_breakdown.locking_ring_cost.toFixed(2)}</Text>
                </View>
              )}
              <View style={[styles.resultRow, styles.totalRow]}>
                <Text style={styles.totalLabel}>Raw Material Total</Text>
                <Text style={styles.totalValue}>Rs. {result.cost_breakdown.total_raw_material.toFixed(2)}</Text>
              </View>
            </View>
            )}

            {/* Pricing - Hide for customers */}
            {!isCustomer && (
            <View style={styles.resultCard}>
              <Text style={styles.resultCardTitle}>Pricing</Text>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Unit Price (per roller)</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.unit_price.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Quantity</Text>
                <Text style={styles.resultValue}>{result.pricing.quantity} pcs</Text>
              </View>
              <View style={[styles.resultRow, styles.subtotalRow]}>
                <Text style={styles.resultLabel}>Order Value</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.order_value.toFixed(2)}</Text>
              </View>
              {result.pricing.discount_percent > 0 && !useCustomDiscount && (
                <View style={styles.discountRow}>
                  <Text style={styles.discountLabel}>- Discount ({result.pricing.discount_percent}%)</Text>
                  <Text style={styles.discountValue}>- Rs. {result.pricing.discount_amount.toFixed(2)}</Text>
                </View>
              )}
              
              {/* Custom Discount Input */}
              <View style={styles.customDiscountContainer}>
                <View style={styles.customDiscountHeader}>
                  <Text style={styles.customDiscountLabel}>Custom Discount %</Text>
                  <TouchableOpacity 
                    onPress={() => {
                      setUseCustomDiscount(!useCustomDiscount);
                      if (!useCustomDiscount) {
                        setCustomDiscount(result.pricing.discount_percent.toString());
                      }
                    }}
                    style={styles.editDiscountBtn}
                  >
                    <Ionicons 
                      name={useCustomDiscount ? "checkmark-circle" : "pencil"} 
                      size={20} 
                      color={useCustomDiscount ? "#4CAF50" : "#960018"} 
                    />
                  </TouchableOpacity>
                </View>
                {useCustomDiscount && (
                  <View style={styles.customDiscountInputRow}>
                    <TextInput
                      style={styles.customDiscountInput}
                      value={customDiscount}
                      onChangeText={setCustomDiscount}
                      keyboardType="numeric"
                      placeholder="Enter %"
                      placeholderTextColor="#999"
                    />
                    <Text style={styles.customDiscountPercent}>%</Text>
                    <Text style={styles.customDiscountAmount}>
                      = Rs. {((result.pricing.order_value * (parseFloat(customDiscount) || 0)) / 100).toFixed(2)}
                    </Text>
                  </View>
                )}
              </View>
              
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>After Discount</Text>
                <Text style={styles.resultValue}>
                  Rs. {useCustomDiscount 
                    ? (result.pricing.order_value - (result.pricing.order_value * (parseFloat(customDiscount) || 0) / 100)).toFixed(2)
                    : result.pricing.price_after_discount.toFixed(2)
                  }
                </Text>
              </View>
              {result.pricing.packing_charges > 0 && (
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>+ Packing ({result.pricing.packing_type}, {result.pricing.packing_percent}%)</Text>
                  <Text style={styles.resultValue}>Rs. {result.pricing.packing_charges.toFixed(2)}</Text>
                </View>
              )}
              <View style={[styles.resultRow, styles.totalRow]}>
                <Text style={styles.totalLabel}>Subtotal (excl. GST & freight)</Text>
                <Text style={styles.totalValue}>Rs. {result.pricing.final_price.toFixed(2)}</Text>
              </View>
            </View>
            )}

            {/* GST - Hide for customers */}
            {!isCustomer && result.gst && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>GST Details</Text>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Destination State</Text>
                  <Text style={styles.resultValue}>{result.gst.destination_state}</Text>
                </View>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Taxable Amount</Text>
                  <Text style={styles.resultValue}>Rs. {result.gst.taxable_amount.toFixed(2)}</Text>
                </View>
                {result.gst.is_same_state ? (
                  <>
                    <View style={styles.resultRow}>
                      <Text style={styles.resultLabel}>CGST ({result.gst.cgst_rate}%)</Text>
                      <Text style={styles.resultValue}>Rs. {result.gst.cgst_amount.toFixed(2)}</Text>
                    </View>
                    <View style={styles.resultRow}>
                      <Text style={styles.resultLabel}>SGST ({result.gst.sgst_rate}%)</Text>
                      <Text style={styles.resultValue}>Rs. {result.gst.sgst_amount.toFixed(2)}</Text>
                    </View>
                  </>
                ) : (
                  <View style={styles.resultRow}>
                    <Text style={styles.resultLabel}>IGST ({result.gst.igst_rate}%)</Text>
                    <Text style={styles.resultValue}>Rs. {result.gst.igst_amount.toFixed(2)}</Text>
                  </View>
                )}
                <View style={[styles.resultRow, styles.totalRow]}>
                  <Text style={styles.totalLabel}>Total GST</Text>
                  <Text style={styles.totalValue}>Rs. {result.gst.total_gst.toFixed(2)}</Text>
                </View>
              </View>
            )}

            {/* Freight - Hide for customers */}
            {!isCustomer && result.freight && (
              <View style={styles.resultCard}>
                <Text style={styles.resultCardTitle}>Freight Charges</Text>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Destination</Text>
                  <Text style={styles.resultValue}>{result.freight.destination_pincode}</Text>
                </View>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Distance</Text>
                  <Text style={styles.resultValue}>{result.freight.distance_km} km</Text>
                </View>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Rate</Text>
                  <Text style={styles.resultValue}>Rs. {result.freight.freight_rate_per_kg}/kg</Text>
                </View>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Single Roller Weight</Text>
                  <Text style={styles.resultValue}>{result.freight.single_roller_weight_kg} kg</Text>
                </View>
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>Total Weight ({result.configuration.quantity} pcs)</Text>
                  <Text style={styles.resultValue}>{result.freight.total_weight_kg} kg</Text>
                </View>
                <View style={[styles.resultRow, styles.totalRow]}>
                  <Text style={styles.totalLabel}>Freight Total</Text>
                  <Text style={styles.totalValue}>Rs. {result.freight.freight_charges.toFixed(2)}</Text>
                </View>
              </View>
            )}

            {/* Grand Total - Hide for customers */}
            {!isCustomer && (
            <View style={styles.grandTotalCard}>
              <View style={styles.grandTotalRow}>
                <Text style={styles.grandTotalLabel}>GRAND TOTAL</Text>
                <Text style={styles.grandTotalValue}>Rs. {result.grand_total.toFixed(2)}</Text>
              </View>
              <Text style={styles.grandTotalHint}>
                ({result.configuration.quantity} roller{result.configuration.quantity > 1 ? 's' : ''}
                {result.gst ? ' + GST' : ''}
                {result.freight ? ' + freight' : ''})
              </Text>
            </View>
            )}

            {/* Customer Selection - Admin only */}
            {!isCustomer && (
            <View style={styles.customerSection}>
              <Text style={styles.customerLabel}>Select Customer for Quote:</Text>
              <TouchableOpacity
                style={styles.customerSelector}
                onPress={() => setShowCustomerPicker(true)}
              >
                {selectedCustomer ? (
                  <View style={styles.selectedCustomer}>
                    <Ionicons name="person" size={20} color="#960018" />
                    <View style={styles.selectedCustomerInfo}>
                      <Text style={styles.selectedCustomerName}>{selectedCustomer.name}</Text>
                      {selectedCustomer.company && (
                        <Text style={styles.selectedCustomerCompany}>{selectedCustomer.company}</Text>
                      )}
                    </View>
                    <TouchableOpacity onPress={() => setSelectedCustomer(null)}>
                      <Ionicons name="close-circle" size={20} color="#666" />
                    </TouchableOpacity>
                  </View>
                ) : (
                  <View style={styles.noCustomerSelected}>
                    <Ionicons name="person-add-outline" size={20} color="#666" />
                    <Text style={styles.noCustomerText}>
                      {customers.length > 0 ? 'Tap to select customer' : 'No customers - Add in Customers tab'}
                    </Text>
                  </View>
                )}
              </TouchableOpacity>
            </View>
            )}

            {/* Save Quote/RFQ Buttons - Admin Only */}
            {!isCustomer && (
            <View style={styles.quoteButtonsContainer}>
              <TouchableOpacity
                style={styles.addToQuoteButton}
                onPress={addToQuote}
              >
                <Ionicons name="add-circle-outline" size={24} color="#fff" />
                <Text style={styles.addToQuoteButtonText}>Add to Quote</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.saveQuoteButton}
                onPress={saveQuote}
                disabled={savingQuote}
              >
                {savingQuote ? (
                  <ActivityIndicator color="#960018" />
                ) : (
                  <>
                    <Ionicons name="save-outline" size={24} color="#960018" />
                    <Text style={styles.saveQuoteButtonText}>Save Single</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
            )}
            
            {/* Download Drawing Button - Admin only */}
            {!isCustomer && (
            <TouchableOpacity
              style={styles.downloadDrawingButton}
              onPress={downloadDrawing}
              disabled={generatingDrawing}
              data-testid="download-drawing-btn"
            >
              {generatingDrawing ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="document-text-outline" size={24} color="#fff" />
                  <Text style={styles.downloadDrawingButtonText}>Download Drawing (PDF)</Text>
                </>
              )}
            </TouchableOpacity>
            )}
          </View>
        )}

        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* Floating Quote Badge - Show for both admin and customer */}
      {quoteItems.length > 0 && (
        <TouchableOpacity 
          style={styles.floatingQuoteBadge}
          onPress={() => setShowQuoteBuilder(true)}
        >
          <Ionicons name="cart" size={24} color="#fff" />
          <View style={styles.badgeCount}>
            <Text style={styles.badgeCountText}>{quoteItems.length}</Text>
          </View>
          {/* Hide price for customers - only show item count */}
          <Text style={styles.floatingBadgeText}>
            {isCustomer ? `${quoteItems.length} item${quoteItems.length !== 1 ? 's' : ''}` : `Rs. ${getQuoteTotal().toFixed(0)}`}
          </Text>
        </TouchableOpacity>
      )}

      {/* Customer Picker Modal */}
      {showCustomerPicker && (
        <View style={styles.modalOverlay}>
          <View style={styles.customerPickerModal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Customer</Text>
              <TouchableOpacity onPress={() => setShowCustomerPicker(false)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.customerPickerScroll}>
              {customers.length === 0 ? (
                <View style={styles.noCustomersMessage}>
                  <Ionicons name="people-outline" size={48} color="#ccc" />
                  <Text style={styles.noCustomersText}>No customers yet</Text>
                  <Text style={styles.noCustomersSubtext}>Add customers in the Customers tab</Text>
                </View>
              ) : (
                customers.map((customer) => (
                  <TouchableOpacity
                    key={customer.id}
                    style={[
                      styles.customerPickerItem,
                      selectedCustomer?.id === customer.id && styles.customerPickerItemSelected
                    ]}
                    onPress={() => {
                      setSelectedCustomer(customer);
                      setShowCustomerPicker(false);
                    }}
                  >
                    <View style={styles.customerPickerItemInfo}>
                      <Text style={styles.customerPickerItemName}>{customer.name}</Text>
                      {customer.company && (
                        <Text style={styles.customerPickerItemCompany}>{customer.company}</Text>
                      )}
                      {customer.city && (
                        <Text style={styles.customerPickerItemLocation}>
                          {customer.city}{customer.state ? `, ${customer.state}` : ''}
                        </Text>
                      )}
                      {customer.gst_number && (
                        <Text style={styles.customerPickerItemGst}>GST: {customer.gst_number}</Text>
                      )}
                    </View>
                    {selectedCustomer?.id === customer.id && (
                      <Ionicons name="checkmark-circle" size={24} color="#960018" />
                    )}
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>

            <View style={styles.customerPickerFooter}>
              <TouchableOpacity
                style={styles.fetchFromGstBtn}
                onPress={openGstLookupFromCalculator}
              >
                <Ionicons name="search" size={18} color="#fff" />
                <Text style={styles.fetchFromGstBtnText}>Fetch from GSTIN</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.clearCustomerBtn}
                onPress={() => {
                  setSelectedCustomer(null);
                  setShowCustomerPicker(false);
                }}
              >
                <Text style={styles.clearCustomerBtnText}>Clear Selection</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* GST Lookup Modal */}
      {showGstLookup && (
        <View style={styles.modalOverlay}>
          <View style={styles.gstLookupModal}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Fetch Customer from GSTIN</Text>
              <TouchableOpacity onPress={() => setShowGstLookup(false)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.gstLookupContent}>
              <View style={styles.gstInfoBox}>
                <Ionicons name="information-circle-outline" size={18} color="#960018" />
                <Text style={styles.gstInfoText}>
                  Enter GSTIN to find existing customer or fetch from GST portal
                </Text>
              </View>

              <Text style={styles.gstInputLabel}>GSTIN (15 characters)</Text>
              <View style={styles.gstInputRow}>
                <TextInput
                  style={[styles.gstInput, { flex: 1, marginBottom: 0 }]}
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
                  <TouchableOpacity style={styles.selectExistingBtn} onPress={selectExistingGstCustomer}>
                    <Ionicons name="person-add" size={18} color="#fff" />
                    <Text style={styles.selectExistingBtnText}>Select This Customer</Text>
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
                    Go to the Customers tab to add this customer with their full details.
                  </Text>
                  <View style={styles.gstinPreview}>
                    <Text style={styles.gstinPreviewLabel}>GSTIN:</Text>
                    <Text style={styles.gstinPreviewValue}>{gstinInput}</Text>
                  </View>
                </View>
              )}

              {gstinInput.length > 0 && gstinInput.length < 15 && (
                <Text style={styles.gstHintText}>
                  {15 - gstinInput.length} more characters needed
                </Text>
              )}
            </ScrollView>
          </View>
        </View>
      )}

      {/* Quote Builder Modal */}
      {showQuoteBuilder && (
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{isCustomer ? 'RFQ Items' : 'Quote Builder'}</Text>
              <TouchableOpacity onPress={() => setShowQuoteBuilder(false)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalScroll}>
              {quoteItems.map((item, index) => (
                <View key={index} style={styles.quoteItem}>
                  <View style={styles.quoteItemHeader}>
                    <Text style={styles.quoteItemCode}>{item.configuration.product_code}</Text>
                    <TouchableOpacity onPress={() => removeFromQuote(index)}>
                      <Ionicons name="trash-outline" size={20} color="#E53935" />
                    </TouchableOpacity>
                  </View>
                  <Text style={styles.quoteItemDesc}>
                    {item.configuration.roller_type.charAt(0).toUpperCase() + item.configuration.roller_type.slice(1)} Roller
                  </Text>
                  <View style={styles.quoteItemRow}>
                    <Text style={styles.quoteItemLabel}>Qty: {item.configuration.quantity}</Text>
                    {/* Hide price for customers */}
                    {!isCustomer && <Text style={styles.quoteItemPrice}>Rs. {item.grand_total.toFixed(2)}</Text>}
                  </View>
                  {/* Show attachments if any */}
                  {item.attachments && item.attachments.length > 0 && (
                    <View style={styles.itemAttachmentRow}>
                      <Ionicons name="attach" size={16} color="#64748B" />
                      <Text style={styles.itemAttachmentText}>
                        {item.attachments.length} attachment{item.attachments.length !== 1 ? 's' : ''}
                      </Text>
                      {item.attachments.map((att: Attachment, attIdx: number) => (
                        att.type === 'image' && att.uri ? (
                          <Image key={attIdx} source={{ uri: att.uri }} style={styles.miniThumbnail} />
                        ) : (
                          <Ionicons key={attIdx} name="document" size={20} color="#960018" style={{ marginLeft: 4 }} />
                        )
                      ))}
                    </View>
                  )}
                </View>
              ))}
            </ScrollView>

            <View style={styles.modalFooter}>
              <View style={styles.modalTotalRow}>
                <Text style={styles.modalTotalLabel}>Total ({quoteItems.length} items)</Text>
                {/* Hide total price for customers */}
                {!isCustomer && <Text style={styles.modalTotalValue}>Rs. {getQuoteTotal().toFixed(2)}</Text>}
              </View>
              <TouchableOpacity 
                style={styles.saveAllButton}
                onPress={saveMultiProductQuote}
                disabled={savingQuote}
              >
                {savingQuote ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.saveAllButtonText}>{isCustomer ? 'Submit RFQ' : 'Save Quote'}</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* RFQ Popup for Customers */}
      {showRfqPopup && isCustomer && (
        <View style={styles.modalOverlay}>
          <View style={styles.rfqPopupContent}>
            <View style={styles.rfqPopupHeader}>
              <Ionicons name="checkmark-circle" size={48} color="#4CAF50" />
              <Text style={styles.rfqPopupTitle}>Item Added!</Text>
              <Text style={styles.rfqPopupSubtitle}>
                {quoteItems.length} item{quoteItems.length !== 1 ? 's' : ''} in your RFQ
              </Text>
            </View>
            
            <View style={styles.rfqPopupButtons}>
              <TouchableOpacity
                style={styles.rfqAddMoreButton}
                onPress={() => {
                  setShowRfqPopup(false);
                }}
              >
                <Ionicons name="add-circle-outline" size={24} color="#960018" />
                <Text style={styles.rfqAddMoreButtonText}>Add More</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.rfqSubmitButtonGreen}
                onPress={async () => {
                  setShowRfqPopup(false);
                  setSavingQuote(true);
                  try {
                    const response = await saveMultiProductQuote();
                    // Show success popup
                    setSubmittedRfqNumber(response?.quote_number || 'RFQ');
                    setShowRfqSuccessPopup(true);
                    // Clear the cart
                    setQuoteItems([]);
                  } catch (error) {
                    console.log('RFQ submission error:', error);
                  } finally {
                    setSavingQuote(false);
                  }
                }}
                disabled={savingQuote}
              >
                {savingQuote ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Ionicons name="send" size={24} color="#fff" />
                    <Text style={styles.rfqSubmitButtonText}>Submit RFQ</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* RFQ Success Popup */}
      {showRfqSuccessPopup && isCustomer && (
        <View style={styles.modalOverlay}>
          <View style={styles.rfqPopupContent}>
            <View style={styles.rfqPopupHeader}>
              <Ionicons name="checkmark-circle" size={64} color="#4CAF50" />
              <Text style={styles.rfqSuccessTitle}>RFQ Submitted!</Text>
              <Text style={styles.rfqSuccessSubtitle}>
                Your Request for Quotation has been sent successfully.
              </Text>
              <Text style={styles.rfqSuccessNumber}>{submittedRfqNumber}</Text>
            </View>
            
            <TouchableOpacity
              style={styles.rfqSuccessButton}
              onPress={() => {
                setShowRfqSuccessPopup(false);
              }}
            >
              <Ionicons name="checkmark" size={24} color="#fff" />
              <Text style={styles.rfqSubmitButtonText}>OK</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#475569',
    fontWeight: '500',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    backgroundColor: '#1E293B',
    paddingTop: 56,
    paddingBottom: 24,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },
  logoContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    alignSelf: 'flex-start',
    marginBottom: 16,
  },
  headerLogo: {
    width: 120,
    height: 40,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -0.5,
  },
  headerSubtitle: {
    fontSize: 15,
    color: '#94A3B8',
    marginTop: 4,
    fontWeight: '400',
  },
  section: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#475569',
    marginBottom: 16,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748B',
    marginBottom: 8,
    marginTop: 16,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 8,
    backgroundColor: '#FFFFFF',
    overflow: 'hidden',
  },
  picker: {
    height: 52,
    color: '#0F172A',
  },
  input: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
    backgroundColor: '#FFFFFF',
    color: '#0F172A',
  },
  inputError: {
    borderColor: '#EF4444',
    borderWidth: 2,
    backgroundColor: '#FEF2F2',
  },
  errorText: {
    color: '#EF4444',
    fontSize: 12,
    marginTop: 6,
    fontWeight: '500',
  },
  hint: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 6,
  },
  noOptionsContainer: {
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  noOptionsText: {
    fontSize: 14,
    color: '#DC2626',
    textAlign: 'center',
    fontWeight: '500',
  },
  toggleContainer: {
    flexDirection: 'row',
    gap: 8,
    backgroundColor: '#F1F5F9',
    borderRadius: 10,
    padding: 4,
  },
  toggleButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: 'transparent',
    gap: 6,
  },
  toggleButtonActive: {
    backgroundColor: '#960018',
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  toggleText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748B',
  },
  toggleTextActive: {
    color: '#FFFFFF',
  },
  calculateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    marginHorizontal: 16,
    marginTop: 24,
    paddingVertical: 16,
    borderRadius: 12,
    gap: 10,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 6,
  },
  calculateButtonDisabled: {
    backgroundColor: '#94A3B8',
    shadowOpacity: 0,
  },
  calculateButtonText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  saveQuoteButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
    paddingVertical: 14,
    borderRadius: 10,
    gap: 8,
    borderWidth: 2,
    borderColor: '#960018',
  },
  saveQuoteButtonText: {
    color: '#960018',
    fontSize: 14,
    fontWeight: '600',
  },
  quoteButtonsContainer: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 16,
  },
  addToQuoteButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#10B981',
    paddingVertical: 14,
    borderRadius: 10,
    gap: 8,
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  addToQuoteButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  downloadDrawingButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1E293B',
    marginTop: 12,
    paddingVertical: 14,
    borderRadius: 10,
    gap: 8,
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  downloadDrawingButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  floatingQuoteBadge: {
    position: 'absolute',
    bottom: 90,
    right: 16,
    backgroundColor: '#960018',
    borderRadius: 28,
    paddingHorizontal: 18,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 8,
  },
  badgeCount: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  badgeCountText: {
    color: '#960018',
    fontSize: 12,
    fontWeight: '700',
  },
  floatingBadgeText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
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
    maxHeight: 300,
    paddingHorizontal: 16,
  },
  quoteItem: {
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    padding: 16,
    marginVertical: 8,
  },
  quoteItemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  quoteItemCode: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  quoteItemDesc: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 4,
  },
  quoteItemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  quoteItemLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  quoteItemPrice: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
  },
  modalFooter: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  modalTotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  modalTotalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
  },
  modalTotalValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  saveAllButton: {
    backgroundColor: '#960018',
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
    elevation: 4,
  },
  saveAllButtonText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '700',
  },
  resultsContainer: {
    marginTop: 24,
    paddingHorizontal: 16,
  },
  productCodeCard: {
    backgroundColor: '#1E293B',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
  },
  productCodeLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#94A3B8',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
  },
  productCode: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  resultCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  resultCardTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#475569',
    marginBottom: 12,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  resultRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  resultLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  resultValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    marginTop: 8,
    paddingTop: 12,
  },
  subtotalRow: {
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
    marginTop: 4,
    paddingTop: 8,
  },
  discountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    backgroundColor: '#ECFDF5',
    marginHorizontal: -16,
    paddingHorizontal: 16,
    marginVertical: 4,
  },
  discountLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#059669',
  },
  discountValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#059669',
  },
  customDiscountContainer: {
    backgroundColor: '#ECFDF5',
    borderRadius: 8,
    padding: 12,
    marginVertical: 8,
    marginHorizontal: -8,
    borderWidth: 1,
    borderColor: '#A7F3D0',
  },
  customDiscountHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  customDiscountLabel: {
    fontSize: 14,
    color: '#059669',
    fontWeight: '600',
  },
  editDiscountBtn: {
    padding: 4,
  },
  customDiscountInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 8,
  },
  customDiscountInput: {
    width: 80,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#10B981',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: '#0F172A',
    textAlign: 'center',
  },
  customDiscountPercent: {
    fontSize: 16,
    color: '#059669',
    fontWeight: '600',
  },
  customDiscountAmount: {
    fontSize: 14,
    color: '#059669',
    fontWeight: '600',
    marginLeft: 8,
  },
  totalLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0F172A',
  },
  totalValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  grandTotalCard: {
    backgroundColor: '#960018',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginTop: 8,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  grandTotalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },
  grandTotalLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  grandTotalValue: {
    fontSize: 26,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  grandTotalHint: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 8,
  },
  bottomSpacer: {
    height: 40,
  },
  customerSection: {
    marginTop: 16,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  customerLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#475569',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  customerSelector: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 10,
    padding: 14,
    backgroundColor: '#FFFFFF',
  },
  selectedCustomer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  selectedCustomerInfo: {
    flex: 1,
  },
  selectedCustomerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
  },
  selectedCustomerCompany: {
    fontSize: 13,
    color: '#64748B',
    marginTop: 2,
  },
  noCustomerSelected: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  noCustomerText: {
    fontSize: 14,
    color: '#64748B',
  },
  customerPickerModal: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    minHeight: 300,
  },
  customerPickerScroll: {
    maxHeight: 400,
    paddingHorizontal: 16,
  },
  customerPickerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  customerPickerItemSelected: {
    borderColor: '#960018',
    backgroundColor: '#FEF2F2',
  },
  customerPickerItemInfo: {
    flex: 1,
  },
  customerPickerItemName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
  },
  customerPickerItemCompany: {
    fontSize: 14,
    color: '#960018',
    marginTop: 2,
  },
  customerPickerItemLocation: {
    fontSize: 13,
    color: '#64748B',
    marginTop: 2,
  },
  customerPickerItemGst: {
    fontSize: 12,
    color: '#94A3B8',
    marginTop: 4,
  },
  customerPickerFooter: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    gap: 12,
    backgroundColor: '#F8FAFC',
  },
  fetchFromGstBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    padding: 14,
    borderRadius: 10,
    gap: 8,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  fetchFromGstBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  clearCustomerBtn: {
    padding: 12,
    alignItems: 'center',
  },
  clearCustomerBtnText: {
    fontSize: 14,
    color: '#64748B',
  },
  noCustomersMessage: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  noCustomersText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    marginTop: 16,
  },
  noCustomersSubtext: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 4,
  },
  gstLookupModal: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '85%',
    minHeight: 400,
  },
  gstLookupContent: {
    padding: 16,
  },
  gstInfoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF5F6',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 10,
    borderWidth: 1,
    borderColor: '#FFD0D6',
  },
  gstInfoText: {
    flex: 1,
    fontSize: 13,
    color: '#333',
  },
  gstInputLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: '#666',
    marginBottom: 8,
  },
  gstInput: {
    backgroundColor: '#F9F9F9',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#E5E5EA',
    marginBottom: 16,
  },
  captchaLoadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 10,
  },
  captchaLoadingText: {
    fontSize: 14,
    color: '#666',
  },
  captchaSection: {
    marginBottom: 8,
  },
  captchaRow: {
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
  verifyGstBtn: {
    backgroundColor: '#960018',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    marginTop: 8,
  },
  verifyGstBtnDisabled: {
    opacity: 0.5,
  },
  verifyGstBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  gstInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
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
  notFoundHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  newCustomerLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F57C00',
  },
  notFoundHint: {
    fontSize: 13,
    color: '#666',
    marginBottom: 12,
    lineHeight: 18,
  },
  gstinPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  gstinPreviewLabel: {
    fontSize: 13,
    color: '#666',
  },
  gstinPreviewValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    fontFamily: 'monospace',
  },
  gstHintText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
  },
  // RFQ Popup Styles
  rfqPopupContent: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 24,
    width: '90%',
    maxWidth: 400,
    alignItems: 'center',
  },
  rfqPopupHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  rfqPopupTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#1E293B',
    marginTop: 16,
  },
  rfqPopupSubtitle: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 8,
    textAlign: 'center',
  },
  rfqPopupButtons: {
    width: '100%',
    gap: 12,
  },
  rfqAddMoreButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#960018',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  rfqAddMoreButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  rfqSubmitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  rfqSubmitButtonGreen: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  rfqSubmitButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  rfqItemCount: {
    fontSize: 13,
    color: '#64748B',
    marginTop: 16,
  },
  rfqSuccessTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1E293B',
    marginTop: 16,
  },
  rfqSuccessSubtitle: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 8,
    textAlign: 'center',
  },
  rfqSuccessNumber: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4CAF50',
    marginTop: 12,
  },
  rfqSuccessButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: 12,
    gap: 8,
    marginTop: 20,
  },
  // Attachment Styles
  attachmentButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 12,
    marginBottom: 16,
  },
  attachmentBtn: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFF5F5',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#960018',
    minWidth: 90,
  },
  attachmentBtnText: {
    fontSize: 12,
    color: '#960018',
    fontWeight: '600',
    marginTop: 4,
  },
  attachmentList: {
    marginTop: 8,
  },
  attachmentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8F9FA',
    padding: 10,
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  attachmentThumbnail: {
    width: 50,
    height: 50,
    borderRadius: 6,
    marginRight: 12,
  },
  attachmentDocIcon: {
    width: 50,
    height: 50,
    borderRadius: 6,
    backgroundColor: '#FFE5E5',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  attachmentName: {
    flex: 1,
    fontSize: 14,
    color: '#1E293B',
  },
  removeAttachmentBtn: {
    padding: 4,
  },
  itemAttachmentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
  },
  itemAttachmentText: {
    fontSize: 12,
    color: '#64748B',
    marginLeft: 4,
    marginRight: 8,
  },
  miniThumbnail: {
    width: 24,
    height: 24,
    borderRadius: 4,
    marginLeft: 4,
  },
});
