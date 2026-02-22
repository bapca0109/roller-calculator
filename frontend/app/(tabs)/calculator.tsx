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
    product_price: number;
    packing_type: string;
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
  63.5: [90, 114],
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

  // Form state
  const [rollerType, setRollerType] = useState<'carrying' | 'impact'>('carrying');
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

  useEffect(() => {
    fetchStandards();
  }, []);

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

  const calculateCost = async () => {
    if (!pipeLength || parseInt(pipeLength) <= 0) {
      Alert.alert('Error', 'Please enter a valid pipe length');
      return;
    }
    if (!quantity || parseInt(quantity) <= 0) {
      Alert.alert('Error', 'Please enter a valid quantity');
      return;
    }

    setCalculating(true);
    setResult(null);

    try {
      const payload: any = {
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

  const availableBearings = standards?.bearing_options[shaftDiameter.toString()] || [];
  const availableRubberDiameters = RUBBER_DIAMETERS[pipeDiameter] || [];

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#FF6B00" />
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
                Standard
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
            style={styles.input}
            value={pipeLength}
            onChangeText={setPipeLength}
            keyboardType="numeric"
            placeholder="Enter pipe length"
          />

          <Text style={styles.label}>Pipe Thickness (IS-1239)</Text>
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

        {/* Impact Roller Options */}
        {rollerType === 'impact' && availableRubberDiameters.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Rubber Lagging</Text>
            <Text style={styles.label}>Rubber Diameter</Text>
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
          </View>
        )}

        {/* Quantity & Packing */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quantity & Packing</Text>

          <Text style={styles.label}>Quantity</Text>
          <TextInput
            style={styles.input}
            value={quantity}
            onChangeText={setQuantity}
            keyboardType="numeric"
            placeholder="Number of rollers"
          />

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
            style={styles.input}
            value={freightPincode}
            onChangeText={setFreightPincode}
            keyboardType="numeric"
            placeholder="Enter 6-digit pincode"
            maxLength={6}
          />
          <Text style={styles.hint}>Dispatch from: 382433 (Gujarat)</Text>
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
                  {result.configuration.roller_type === 'impact' ? 'Impact Roller' : 'Carrying Roller'}
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
              <Text style={styles.resultCardTitle}>Pricing (Per Roller)</Text>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Raw Material</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.raw_material_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>+ Layout (32%)</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.layout_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>+ Profit (60%)</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.profit.toFixed(2)}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Product Price</Text>
                <Text style={styles.resultValue}>Rs. {result.pricing.product_price.toFixed(2)}</Text>
              </View>
              {result.pricing.packing_charges > 0 && (
                <View style={styles.resultRow}>
                  <Text style={styles.resultLabel}>+ Packing ({result.pricing.packing_type})</Text>
                  <Text style={styles.resultValue}>Rs. {result.pricing.packing_charges.toFixed(2)}</Text>
                </View>
              )}
              <View style={[styles.resultRow, styles.totalRow]}>
                <Text style={styles.totalLabel}>Unit Price</Text>
                <Text style={styles.totalValue}>Rs. {result.pricing.final_price.toFixed(2)}</Text>
              </View>
            </View>

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
                {result.freight ? ' + freight' : ''})
              </Text>
            </View>
          </View>
        )}

        <View style={styles.bottomSpacer} />
      </ScrollView>
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
    backgroundColor: '#FF6B00',
    paddingTop: 60,
    paddingBottom: 24,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 16,
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
  hint: {
    fontSize: 12,
    color: '#888',
    marginTop: 6,
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
    backgroundColor: '#FF6B00',
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
    backgroundColor: '#FF6B00',
    marginHorizontal: 16,
    marginTop: 24,
    paddingVertical: 16,
    borderRadius: 12,
    gap: 10,
    shadowColor: '#FF6B00',
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
    color: '#FF6B00',
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
  totalLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#333',
  },
  totalValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FF6B00',
  },
  grandTotalCard: {
    backgroundColor: '#FF6B00',
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
});
