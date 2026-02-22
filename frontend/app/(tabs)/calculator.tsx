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
  const { user } = useAuth();
  const [standards, setStandards] = useState<RollerStandards | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState<CostResult | null>(null);
  const [savingQuote, setSavingQuote] = useState(false);
  const [quoteItems, setQuoteItems] = useState<CostResult[]>([]);
  const [showQuoteBuilder, setShowQuoteBuilder] = useState(false);
  
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

  // Error state
  const [errors, setErrors] = useState<{
    pipeLength?: string;
    quantity?: string;
    freightPincode?: string;
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
    setShowCustomerPicker(false);
    setShowGstLookup(true);
    fetchGstCaptcha();
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
      return;
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
      };

      if (rollerType === 'impact' && rubberDiameter) {
        payload.rubber_diameter = rubberDiameter;
      }

      if (freightPincode && freightPincode.length === 6) {
        payload.freight_pincode = freightPincode;
      }

      const response = await api.post('/calculate-detailed-cost', payload);
      setResult(response.data);
    } catch (error: any) {
      Alert.alert('Calculation Error', error.response?.data?.detail || 'Failed to calculate cost');
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
      return;
    }

    setSavingQuote(true);
    try {
      const products = quoteItems.map(item => ({
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
        custom_premium: 0
      }));

      const response = await api.post('/quotes', {
        products,
        delivery_location: quoteItems[0].freight?.destination_pincode || null,
        notes: `Multi-product quote with ${quoteItems.length} items`
      });
      
      Alert.alert(
        'Quote Saved!', 
        `Quote ID: ${response.data.id}\nTotal Items: ${quoteItems.length}\nTotal: Rs. ${response.data.total_price.toFixed(2)}`,
        [{ text: 'OK', onPress: () => {
          setQuoteItems([]);
          setShowQuoteBuilder(false);
        }}]
      );
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save quote');
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

        {/* Calculate Button */}
        <TouchableOpacity
          style={[styles.calculateButton, calculating && styles.calculateButtonDisabled]}
          onPress={calculateCost}
          disabled={calculating}
        >
          {calculating ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="calculator" size={24} color="#fff" />
              <Text style={styles.calculateButtonText}>Calculate Price</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Results */}
        {result && (
          <View style={styles.resultsContainer}>
            {/* Product Code */}
            <View style={styles.productCodeCard}>
              <Text style={styles.productCodeLabel}>Product Code</Text>
              <Text style={styles.productCode}>{result.configuration.product_code}</Text>
            </View>

            {/* Configuration Summary */}
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

            {/* Cost Breakdown */}
            <View style={styles.resultCard}>
              <Text style={styles.resultCardTitle}>Cost Breakdown (Per Roller)</Text>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Pipe</Text>
                <Text style={styles.resultValue}>Rs. {result.cost_breakdown.pipe_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Shaft (2 pcs)</Text>
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

            {/* Pricing */}
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
              {result.pricing.discount_percent > 0 && (
                <View style={styles.discountRow}>
                  <Text style={styles.discountLabel}>- Discount ({result.pricing.discount_percent}%)</Text>
                  <Text style={styles.discountValue}>- Rs. {result.pricing.discount_amount.toFixed(2)}</Text>
                </View>
              )}
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>After Discount</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.price_after_discount.toFixed(2)}</Text>
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

            {/* GST */}
            {result.gst && (
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

            {/* Freight */}
            {result.freight && (
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

            {/* Grand Total */}
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

            {/* Customer Selection */}
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

            {/* Save Quote Button */}
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
          </View>
        )}

        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* Floating Quote Badge */}
      {quoteItems.length > 0 && (
        <TouchableOpacity 
          style={styles.floatingQuoteBadge}
          onPress={() => setShowQuoteBuilder(true)}
        >
          <Ionicons name="cart" size={24} color="#fff" />
          <View style={styles.badgeCount}>
            <Text style={styles.badgeCountText}>{quoteItems.length}</Text>
          </View>
          <Text style={styles.floatingBadgeText}>Rs. {getQuoteTotal().toFixed(0)}</Text>
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
                  Enter GSTIN to auto-fetch and save customer details
                </Text>
              </View>

              <Text style={styles.gstInputLabel}>GSTIN (15 characters)</Text>
              <TextInput
                style={styles.gstInput}
                value={gstinInput}
                onChangeText={(text) => setGstinInput(text.toUpperCase())}
                placeholder="e.g., 27AAACE8661R1Z5"
                maxLength={15}
                autoCapitalize="characters"
              />

              {gstLoading ? (
                <View style={styles.captchaLoadingContainer}>
                  <ActivityIndicator size="small" color="#960018" />
                  <Text style={styles.captchaLoadingText}>Loading captcha...</Text>
                </View>
              ) : captchaData?.captcha_image ? (
                <View style={styles.captchaSection}>
                  <Text style={styles.gstInputLabel}>Enter Captcha</Text>
                  <View style={styles.captchaRow}>
                    <Image
                      source={{ uri: captchaData.captcha_image }}
                      style={styles.captchaImage}
                      resizeMode="contain"
                    />
                    <TouchableOpacity style={styles.refreshCaptchaBtn} onPress={fetchGstCaptcha}>
                      <Ionicons name="refresh" size={20} color="#960018" />
                    </TouchableOpacity>
                  </View>
                  <TextInput
                    style={styles.gstInput}
                    value={captchaInput}
                    onChangeText={setCaptchaInput}
                    placeholder="Enter captcha shown above"
                    autoCapitalize="characters"
                  />
                </View>
              ) : (
                <TouchableOpacity style={styles.loadCaptchaBtn} onPress={fetchGstCaptcha}>
                  <Text style={styles.loadCaptchaBtnText}>Load Captcha</Text>
                </TouchableOpacity>
              )}

              <TouchableOpacity
                style={[styles.verifyGstBtn, (!gstinInput || !captchaInput || gstVerifying) && styles.verifyGstBtnDisabled]}
                onPress={verifyGstinFromCalculator}
                disabled={!gstinInput || !captchaInput || gstVerifying}
              >
                {gstVerifying ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Ionicons name="checkmark-circle" size={20} color="#fff" />
                    <Text style={styles.verifyGstBtnText}>Verify & Create Customer</Text>
                  </>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      )}

      {/* Quote Builder Modal */}
      {showQuoteBuilder && (
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Quote Builder</Text>
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
                    <Text style={styles.quoteItemPrice}>Rs. {item.grand_total.toFixed(2)}</Text>
                  </View>
                </View>
              ))}
            </ScrollView>

            <View style={styles.modalFooter}>
              <View style={styles.modalTotalRow}>
                <Text style={styles.modalTotalLabel}>Total ({quoteItems.length} items)</Text>
                <Text style={styles.modalTotalValue}>Rs. {getQuoteTotal().toFixed(2)}</Text>
              </View>
              <TouchableOpacity 
                style={styles.saveAllButton}
                onPress={saveMultiProductQuote}
                disabled={savingQuote}
              >
                {savingQuote ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.saveAllButtonText}>Save Quote</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
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
  scrollView: {
    flex: 1,
  },
  header: {
    backgroundColor: '#960018',
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  logoContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginBottom: 8,
  },
  headerLogo: {
    width: 150,
    height: 50,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#fff',
    opacity: 0.9,
    marginTop: 4,
  },
  section: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#555',
    marginBottom: 8,
    marginTop: 12,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    backgroundColor: '#FAFAFA',
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  input: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    padding: 14,
    fontSize: 16,
    backgroundColor: '#FAFAFA',
  },
  inputError: {
    borderColor: '#E53935',
    borderWidth: 2,
    backgroundColor: '#FFEBEE',
  },
  errorText: {
    color: '#E53935',
    fontSize: 12,
    marginTop: 4,
    fontWeight: '500',
  },
  hint: {
    fontSize: 12,
    color: '#888',
    marginTop: 6,
  },
  noOptionsContainer: {
    backgroundColor: '#FFE4E6',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  noOptionsText: {
    fontSize: 14,
    color: '#E65100',
    textAlign: 'center',
  },
  toggleContainer: {
    flexDirection: 'row',
    gap: 12,
  },
  toggleButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    borderRadius: 8,
    backgroundColor: '#F0F0F0',
    gap: 8,
  },
  toggleButtonActive: {
    backgroundColor: '#960018',
  },
  toggleText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  toggleTextActive: {
    color: '#fff',
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
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  calculateButtonDisabled: {
    backgroundColor: '#CCC',
    shadowOpacity: 0,
  },
  calculateButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  saveQuoteButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
    borderWidth: 2,
    borderColor: '#960018',
  },
  saveQuoteButtonText: {
    color: '#960018',
    fontSize: 14,
    fontWeight: '700',
  },
  quoteButtonsContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  addToQuoteButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
  },
  addToQuoteButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  floatingQuoteBadge: {
    position: 'absolute',
    bottom: 80,
    right: 16,
    backgroundColor: '#960018',
    borderRadius: 30,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  badgeCount: {
    backgroundColor: '#fff',
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
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
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
    color: '#333',
  },
  modalScroll: {
    maxHeight: 300,
    paddingHorizontal: 16,
  },
  quoteItem: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
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
    color: '#666',
    marginTop: 4,
  },
  quoteItemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  quoteItemLabel: {
    fontSize: 14,
    color: '#666',
  },
  quoteItemPrice: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  modalFooter: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#EEE',
  },
  modalTotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  modalTotalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  modalTotalValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  saveAllButton: {
    backgroundColor: '#960018',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  saveAllButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  resultsContainer: {
    marginTop: 24,
    paddingHorizontal: 16,
  },
  productCodeCard: {
    backgroundColor: '#1A1A2E',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
  },
  productCodeLabel: {
    fontSize: 14,
    color: '#888',
    marginBottom: 8,
  },
  productCode: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#960018',
    letterSpacing: 1,
  },
  resultCard: {
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
  resultCardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  resultRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  resultLabel: {
    fontSize: 14,
    color: '#666',
  },
  resultValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    marginTop: 8,
    paddingTop: 12,
  },
  subtotalRow: {
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    marginTop: 4,
    paddingTop: 8,
  },
  discountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    backgroundColor: '#E8F5E9',
    marginHorizontal: -16,
    paddingHorizontal: 16,
    marginVertical: 4,
  },
  discountLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2E7D32',
  },
  discountValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#2E7D32',
  },
  totalLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#333',
  },
  totalValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  grandTotalCard: {
    backgroundColor: '#960018',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginTop: 8,
  },
  grandTotalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },
  grandTotalLabel: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  grandTotalValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  grandTotalHint: {
    fontSize: 13,
    color: '#fff',
    opacity: 0.8,
    marginTop: 8,
  },
  bottomSpacer: {
    height: 40,
  },
  customerSection: {
    marginTop: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  customerLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#555',
    marginBottom: 12,
  },
  customerSelector: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#FAFAFA',
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
    color: '#333',
  },
  selectedCustomerCompany: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  noCustomerSelected: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  noCustomerText: {
    fontSize: 14,
    color: '#666',
  },
  customerPickerModal: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
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
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#E5E5E5',
  },
  customerPickerItemSelected: {
    borderColor: '#960018',
    backgroundColor: '#FFF5F6',
  },
  customerPickerItemInfo: {
    flex: 1,
  },
  customerPickerItemName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  customerPickerItemCompany: {
    fontSize: 14,
    color: '#960018',
    marginTop: 2,
  },
  customerPickerItemLocation: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  customerPickerItemGst: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
  customerPickerFooter: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
    gap: 12,
  },
  fetchFromGstBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    padding: 14,
    borderRadius: 10,
    gap: 8,
  },
  fetchFromGstBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  clearCustomerBtn: {
    padding: 12,
    alignItems: 'center',
  },
  clearCustomerBtnText: {
    fontSize: 14,
    color: '#666',
  },
  noCustomersMessage: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  noCustomersText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
  },
  noCustomersSubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  gstLookupModal: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
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
});
