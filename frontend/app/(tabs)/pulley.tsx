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
  RefreshControl,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CustomDropdown } from '../../components/CustomDropdown';
import { useAuth } from '../../contexts/AuthContext';
import { useCart } from '../context/CartContext';
import api, { cacheEvents } from '../../utils/api';
import FloatingCartButton from '../../components/FloatingCartButton';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';

// Types
interface PulleyStandards {
  pulley_types: string[];
  pipe_diameters: number[];
  pipe_thickness_map: { [key: string]: number[] };
  shaft_diameters: number[];
  shaft_materials: string[];
  end_plate_thicknesses: number[];
  hub_types: string[];
  hub_diameters: number[];
  kla_shaft_hub_options: number[];
  rubber_lagging_types: string[];
  rubber_plain_thicknesses: number[];
  rubber_ceramic_thicknesses: number[];
}

interface PulleyCostResult {
  configuration: {
    product_code: string;
    product_type: string;
    pulley_type: string;
    pipe_diameter_mm: number;
    pipe_thickness_mm: number;
    face_length_mm: number;
    shaft_diameter_centre_mm: number;
    shaft_material: string;
    shaft_length_mm: number;
    end_plate_thickness_mm: number;
    hub_type: string;
    hub_diameter_mm: number | null;
    hub_length_mm: number | null;
    shaft_dia_hub_mm: number | null;
    kla_model: string | null;
    rubber_type: string;
    rubber_thickness_mm: number | null;
    quantity: number;
  };
  cost_breakdown: {
    pipe_weight_kg: number;
    pipe_rate: number;
    pipe_cost: number;
    shaft_weight_kg: number;
    shaft_rate: number;
    shaft_cost: number;
    end_plate_weight_single_kg: number;
    end_plate_weight_total_kg: number;
    end_plate_rate: number;
    end_plate_cost: number;
    hub_cost: number;
    rubber_cost: number;
    total_raw_material: number;
    single_pulley_weight_kg: number;
    total_weight_kg: number;
    [key: string]: number;
  };
  pricing: {
    raw_material_cost: number;
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
  gst?: {
    taxable_amount: number;
    gst_type: string;
    cgst_rate: number;
    cgst_amount: number;
    sgst_rate: number;
    sgst_amount: number;
    total_gst: number;
  };
  grand_total: number;
}

const PACKING_OPTIONS = [
  { label: 'None', value: 'none' },
  { label: 'Standard (1%)', value: 'standard' },
  { label: 'Pallet (4%)', value: 'pallet' },
  { label: 'Wooden Box (8%)', value: 'wooden_box' },
];

const HUB_TYPE_LABELS: { [key: string]: string } = {
  no_hub: 'No Hub',
  with_hub: 'With Hub',
  kla: 'KLA (Keyless Locking)',
};

const RUBBER_TYPE_LABELS: { [key: string]: string } = {
  none: 'None',
  plain: 'Plain',
  diamond: 'Diamond',
  ceramic: 'Ceramic',
};

export default function PulleyScreen() {
  const { user } = useAuth();
  const { addToCart, cartCount } = useCart();
  const router = useRouter();
  const isCustomer = user?.role === 'customer';

  const [standards, setStandards] = useState<PulleyStandards | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState<PulleyCostResult | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [savingQuote, setSavingQuote] = useState(false);

  // Attachments
  const [currentAttachments, setCurrentAttachments] = useState<any[]>([]);
  const [productRemark, setProductRemark] = useState('');

  // Customer selection (admin)
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);

  // Form state
  const [pulleyType, setPulleyType] = useState('Drive');
  const [pipeDiameter, setPipeDiameter] = useState(219);
  const [pipeThickness, setPipeThickness] = useState<number>(8);
  const [faceLength, setFaceLength] = useState('500');
  const [shaftDiaCentre, setShaftDiaCentre] = useState(80);
  const [shaftMaterial, setShaftMaterial] = useState('MS');
  const [shaftLength, setShaftLength] = useState('700');
  const [endPlateThickness, setEndPlateThickness] = useState(12);
  const [endPlateQty, setEndPlateQty] = useState(2);
  const [hubType, setHubType] = useState('no_hub');
  const [hubDiameter, setHubDiameter] = useState<number>(120);
  const [hubLength, setHubLength] = useState('80');
  const [shaftDiaHub, setShaftDiaHub] = useState<number>(50);
  const [rubberType, setRubberType] = useState('none');
  const [rubberThickness, setRubberThickness] = useState<number>(10);
  const [quantity, setQuantity] = useState('1');
  const [packingType, setPackingType] = useState('none');

  // Available thicknesses for selected pipe
  const [availableThicknesses, setAvailableThicknesses] = useState<number[]>([]);

  // Validation errors
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  // KLA Model info
  const [klaModelInfo, setKlaModelInfo] = useState<any>(null);

  useEffect(() => {
    fetchStandards();
    fetchCustomers();
    const handleRefresh = () => {
      fetchStandards();
      fetchCustomers();
    };
    cacheEvents.on('refresh', handleRefresh);
    return () => {
      cacheEvents.off('refresh', handleRefresh);
    };
  }, []);

  // Update available thicknesses when pipe diameter changes
  useEffect(() => {
    if (standards) {
      const thicknesses = standards.pipe_thickness_map[pipeDiameter.toString()] || [];
      setAvailableThicknesses(thicknesses);
      if (thicknesses.length > 0 && !thicknesses.includes(pipeThickness)) {
        setPipeThickness(thicknesses[0]);
      }
    }
  }, [pipeDiameter, standards]);

  // Update min hub diameter when shaft dia changes
  useEffect(() => {
    if (hubType === 'with_hub') {
      const minHub = shaftDiaCentre + 40;
      if (hubDiameter < minHub) {
        setHubDiameter(minHub);
      }
    }
  }, [shaftDiaCentre, hubType]);

  // Fetch KLA model info when shaft_dia_hub changes
  useEffect(() => {
    if (hubType === 'kla' && shaftDiaHub) {
      const fetchKla = async () => {
        try {
          const response = await api.get(`/pulley-kla-model/${shaftDiaHub}`);
          setKlaModelInfo(response.data);
        } catch {
          setKlaModelInfo(null);
        }
      };
      fetchKla();
    } else {
      setKlaModelInfo(null);
    }
  }, [shaftDiaHub, hubType]);

  const fetchStandards = async () => {
    try {
      const response = await api.get('/pulley-standards');
      setStandards(response.data);
    } catch {
      Alert.alert('Error', 'Failed to load pulley standards');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchStandards(), fetchCustomers()]);
    setRefreshing(false);
  };

  const fetchCustomers = async () => {
    try {
      const response = await api.get('/customers');
      setCustomers(response.data.customers || []);
    } catch { /* ignore */ }
  };

  // Attachment functions
  const pickImage = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') { Alert.alert('Permission Denied', 'Allow photo access.'); return; }
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7, base64: true });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        let base64Data = asset.base64;
        if (!base64Data && asset.uri && Platform.OS === 'web') {
          const resp = await fetch(asset.uri); const blob = await resp.blob();
          base64Data = await new Promise((resolve) => { const reader = new FileReader(); reader.onloadend = () => resolve((reader.result as string).split(',')[1]); reader.readAsDataURL(blob); });
        }
        setCurrentAttachments([...currentAttachments, { uri: asset.uri, name: asset.fileName || `image_${Date.now()}.jpg`, type: 'image', base64: base64Data }]);
      }
    } catch { Alert.alert('Error', 'Failed to pick image'); }
  };

  const takePhoto = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') { Alert.alert('Permission Denied', 'Allow camera access.'); return; }
      const result = await ImagePicker.launchCameraAsync({ quality: 0.7, base64: true });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setCurrentAttachments([...currentAttachments, { uri: asset.uri, name: `photo_${Date.now()}.jpg`, type: 'image', base64: asset.base64 }]);
      }
    } catch { Alert.alert('Error', 'Failed to take photo'); }
  };

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/*', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'], copyToCacheDirectory: true });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        let base64Data: string | undefined;
        try {
          if (Platform.OS === 'web') {
            const resp = await fetch(asset.uri); const blob = await resp.blob();
            base64Data = await new Promise((resolve) => { const reader = new FileReader(); reader.onloadend = () => resolve((reader.result as string).split(',')[1]); reader.readAsDataURL(blob); });
          } else {
            base64Data = await FileSystem.readAsStringAsync(asset.uri, { encoding: FileSystem.EncodingType.Base64 });
          }
        } catch { /* ignore */ }
        setCurrentAttachments([...currentAttachments, { uri: asset.uri, name: asset.name || `file_${Date.now()}`, type: 'document', base64: base64Data }]);
      }
    } catch { Alert.alert('Error', 'Failed to pick document'); }
  };

  const removeAttachment = (index: number) => {
    setCurrentAttachments(currentAttachments.filter((_, i) => i !== index));
  };

  const saveQuote = async () => {
    if (!result) return;
    setSavingQuote(true);
    try {
      const customerDetails = selectedCustomer ? {
        name: selectedCustomer.name, company: selectedCustomer.company, email: selectedCustomer.email,
        phone: selectedCustomer.phone, address: selectedCustomer.address, city: selectedCustomer.city,
        state: selectedCustomer.state, pincode: selectedCustomer.pincode, gst_number: selectedCustomer.gst_number,
      } : null;
      const response = await api.post('/quotes/roller', {
        customer_name: selectedCustomer?.name || user?.name || 'Customer',
        customer_id: selectedCustomer?.id || null,
        customer_details: customerDetails,
        configuration: result.configuration,
        cost_breakdown: result.cost_breakdown,
        pricing: result.pricing,
        freight: null,
        grand_total: result.grand_total,
        notes: `Pulley: ${result.configuration.product_code}`
      });
      Alert.alert('Quote Saved!', `Quote Number: ${response.data.quote_number}\nTotal: Rs. ${response.data.total_price.toFixed(2)}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save quote');
    } finally {
      setSavingQuote(false);
    }
  };

  const validate = () => {
    const errs: { [key: string]: string } = {};
    const fl = parseInt(faceLength);
    if (!faceLength || isNaN(fl) || fl < 100 || fl > 5000) {
      errs.faceLength = 'Face length: 100-5000mm';
    }
    const sl = parseInt(shaftLength);
    if (!shaftLength || isNaN(sl) || sl < 100 || sl > 6000) {
      errs.shaftLength = 'Shaft length: 100-6000mm';
    }
    const qty = parseInt(quantity);
    if (!quantity || isNaN(qty) || qty < 1 || qty > 100000) {
      errs.quantity = 'Quantity: 1-100,000';
    }
    if (hubType === 'with_hub') {
      const hl = parseFloat(hubLength);
      if (!hubLength || isNaN(hl) || hl < 10) {
        errs.hubLength = 'Hub length required (min 10mm)';
      }
      const minHub = shaftDiaCentre + 40;
      if (hubDiameter < minHub) {
        errs.hubDiameter = `Min hub dia: ${minHub}mm`;
      }
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const calculateCost = async () => {
    if (!validate()) return;

    setCalculating(true);
    setResult(null);

    try {
      const payload: any = {
        pulley_type: pulleyType,
        pipe_diameter: pipeDiameter,
        pipe_thickness: pipeThickness,
        face_length: parseFloat(faceLength),
        shaft_diameter_centre: shaftDiaCentre,
        shaft_material: shaftMaterial,
        shaft_length: parseFloat(shaftLength),
        end_plate_thickness: endPlateThickness,
        end_plate_qty: endPlateQty,
        hub_type: hubType,
        quantity: parseInt(quantity),
        packing_type: packingType,
      };

      if (hubType === 'with_hub') {
        payload.hub_diameter = hubDiameter;
        payload.hub_length = parseFloat(hubLength);
      } else if (hubType === 'kla') {
        payload.shaft_dia_hub = shaftDiaHub;
      }

      if (rubberType !== 'none') {
        payload.rubber_type = rubberType;
        payload.rubber_thickness = rubberThickness;
      }

      const response = await api.post('/calculate-pulley-cost', payload);
      setResult(response.data);
    } catch (error: any) {
      Alert.alert('Calculation Error', error.response?.data?.detail || 'Failed to calculate pulley cost');
    } finally {
      setCalculating(false);
    }
  };

  const handleAddToCart = () => {
    if (!result) return;

    addToCart({
      product_id: result.configuration.product_code,
      product_name: `${result.configuration.pulley_type} Pulley - ${result.configuration.product_code}`,
      product_code: result.configuration.product_code,
      roller_type: 'pulley',
      quantity: result.configuration.quantity,
      unit_price: result.pricing.unit_price,
      weight_kg: result.cost_breakdown.single_pulley_weight_kg || 0,
      specifications: {
        pipe_diameter: result.configuration.pipe_diameter_mm,
        pipe_length: result.configuration.face_length_mm,
        pipe_type: `${result.configuration.pipe_thickness_mm}mm wall`,
        shaft_diameter: result.configuration.shaft_diameter_centre_mm,
      },
      remark: productRemark.trim() || undefined,
      attachments: currentAttachments.map(att => ({ uri: att.uri, name: att.name, type: att.type, base64: att.base64 })),
      source: 'pulley',
      calculatorData: result,
    });

    Alert.alert('Added to Cart', `${result.configuration.pulley_type} Pulley added to cart`);
    setCurrentAttachments([]);
    setProductRemark('');
    setResult(null);
  };

  // Hub dia options filtered by min constraint
  const getHubDiaOptions = () => {
    if (!standards) return [];
    const minHub = shaftDiaCentre + 40;
    return standards.hub_diameters
      .filter((d) => d >= minHub)
      .map((d) => ({ label: `${d} mm`, value: d }));
  };

  // Rubber thickness options based on type
  const getRubberThicknessOptions = () => {
    if (!standards) return [];
    const thicknesses =
      rubberType === 'ceramic'
        ? standards.rubber_ceramic_thicknesses
        : standards.rubber_plain_thicknesses;
    return thicknesses.map((t) => ({ label: `${t} mm`, value: t }));
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer} data-testid="pulley-loading">
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading Pulley Standards...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Header */}
      <View style={styles.header} data-testid="pulley-header">
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.headerTitle}>Pulley Calculator</Text>
            <Text style={styles.headerSubtitle}>Belt Conveyor Pulley Pricing</Text>
          </View>
          <View style={styles.headerBadge}>
            <Ionicons name="cog-outline" size={20} color="#FFFFFF" />
          </View>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#960018']} />
        }
      >
        {/* Pulley Type */}
        <View style={styles.card} data-testid="pulley-type-section">
          <Text style={styles.sectionTitle}>Pulley Type</Text>
          <View style={styles.typeRow}>
            {(standards?.pulley_types || []).map((type) => (
              <TouchableOpacity
                key={type}
                style={[styles.typeBtn, pulleyType === type && styles.typeBtnActive]}
                onPress={() => setPulleyType(type)}
                data-testid={`pulley-type-${type.toLowerCase()}`}
              >
                <Text style={[styles.typeBtnText, pulleyType === type && styles.typeBtnTextActive]}>
                  {type}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Pipe Configuration */}
        <View style={styles.card} data-testid="pipe-config-section">
          <Text style={styles.sectionTitle}>Pipe Configuration</Text>

          <CustomDropdown
            label="Pipe Diameter (mm)"
            value={pipeDiameter}
            options={(standards?.pipe_diameters || []).map((d) => ({
              label: `${d} mm`,
              value: d,
            }))}
            onValueChange={(v) => setPipeDiameter(v)}
          />

          <View style={styles.spacer} />

          <CustomDropdown
            label="Wall Thickness (mm)"
            value={pipeThickness}
            options={availableThicknesses.map((t) => ({
              label: `${t} mm`,
              value: t,
            }))}
            onValueChange={(v) => setPipeThickness(v)}
          />

          <View style={styles.spacer} />

          <Text style={styles.inputLabel}>Face Length (mm)</Text>
          <TextInput
            style={[styles.input, errors.faceLength && styles.inputError]}
            value={faceLength}
            onChangeText={(v) => {
              setFaceLength(v);
              setErrors((e) => ({ ...e, faceLength: '' }));
            }}
            keyboardType="numeric"
            placeholder="e.g. 500"
            data-testid="face-length-input"
          />
          {errors.faceLength ? <Text style={styles.errorText}>{errors.faceLength}</Text> : null}
        </View>

        {/* Shaft Configuration */}
        <View style={styles.card} data-testid="shaft-config-section">
          <Text style={styles.sectionTitle}>Shaft Configuration</Text>

          <CustomDropdown
            label="Shaft Dia @ Centre (mm)"
            value={shaftDiaCentre}
            options={(standards?.shaft_diameters || []).map((d) => ({
              label: `${d} mm`,
              value: d,
            }))}
            onValueChange={(v) => setShaftDiaCentre(v)}
          />

          <View style={styles.spacer} />

          <CustomDropdown
            label="Shaft Material"
            value={shaftMaterial}
            options={(standards?.shaft_materials || []).map((m) => ({
              label: m,
              value: m,
            }))}
            onValueChange={(v) => setShaftMaterial(v)}
          />

          <View style={styles.spacer} />

          <Text style={styles.inputLabel}>Shaft Length (mm)</Text>
          <TextInput
            style={[styles.input, errors.shaftLength && styles.inputError]}
            value={shaftLength}
            onChangeText={(v) => {
              setShaftLength(v);
              setErrors((e) => ({ ...e, shaftLength: '' }));
            }}
            keyboardType="numeric"
            placeholder="e.g. 700"
            data-testid="shaft-length-input"
          />
          {errors.shaftLength ? <Text style={styles.errorText}>{errors.shaftLength}</Text> : null}
        </View>

        {/* End Plate */}
        <View style={styles.card} data-testid="end-plate-section">
          <Text style={styles.sectionTitle}>End Plate</Text>
          <CustomDropdown
            label="End Plate Thickness (mm)"
            value={endPlateThickness}
            options={(standards?.end_plate_thicknesses || []).map((t) => ({
              label: `${t} mm`,
              value: t,
            }))}
            onValueChange={(v) => setEndPlateThickness(v)}
          />

          <View style={styles.spacer} />

          <CustomDropdown
            label="End Plate Qty (Nos)"
            value={endPlateQty}
            options={[
              { label: '2 Nos', value: 2 },
              { label: '3 Nos', value: 3 },
              { label: '4 Nos', value: 4 },
            ]}
            onValueChange={(v) => setEndPlateQty(v)}
          />
        </View>

        {/* Hub Configuration */}
        <View style={styles.card} data-testid="hub-config-section">
          <Text style={styles.sectionTitle}>Hub Configuration</Text>

          <View style={styles.hubTypeRow}>
            {['no_hub', 'with_hub'].map((type) => (
              <TouchableOpacity
                key={type}
                style={[styles.hubTypeBtn, hubType === type && styles.hubTypeBtnActive]}
                onPress={() => setHubType(type)}
                data-testid={`hub-type-${type}`}
              >
                <Ionicons
                  name={type === 'no_hub' ? 'close-circle-outline' : type === 'with_hub' ? 'disc-outline' : 'lock-closed-outline'}
                  size={18}
                  color={hubType === type ? '#FFFFFF' : '#64748B'}
                />
                <Text style={[styles.hubTypeBtnText, hubType === type && styles.hubTypeBtnTextActive]}>
                  {HUB_TYPE_LABELS[type]}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {hubType === 'with_hub' && (
            <View style={styles.hubFields}>
              <CustomDropdown
                label={`Hub Diameter (mm) — Min: ${shaftDiaCentre + 40}mm`}
                value={hubDiameter}
                options={getHubDiaOptions()}
                onValueChange={(v) => setHubDiameter(v)}
              />
              {errors.hubDiameter ? <Text style={styles.errorText}>{errors.hubDiameter}</Text> : null}

              <View style={styles.spacer} />

              <Text style={styles.inputLabel}>Hub Length (mm)</Text>
              <TextInput
                style={[styles.input, errors.hubLength && styles.inputError]}
                value={hubLength}
                onChangeText={(v) => {
                  setHubLength(v);
                  setErrors((e) => ({ ...e, hubLength: '' }));
                }}
                keyboardType="numeric"
                placeholder="e.g. 80"
                data-testid="hub-length-input"
              />
              {errors.hubLength ? <Text style={styles.errorText}>{errors.hubLength}</Text> : null}
            </View>
          )}

          {hubType === 'kla' && (
            <View style={styles.hubFields}>
              <CustomDropdown
                label="Shaft Dia @ Hub (mm)"
                value={shaftDiaHub}
                options={(standards?.kla_shaft_hub_options || []).map((d) => ({
                  label: `${d} mm`,
                  value: d,
                }))}
                onValueChange={(v) => setShaftDiaHub(v)}
              />
              {klaModelInfo && (
                <View style={styles.klaInfoBox}>
                  <Ionicons name="information-circle" size={16} color="#3B82F6" />
                  <Text style={styles.klaInfoText}>
                    KLA Model: {klaModelInfo.model} — Price: Rs.{klaModelInfo.price}/unit
                  </Text>
                </View>
              )}
            </View>
          )}
        </View>

        {/* Rubber Lagging */}
        <View style={styles.card} data-testid="rubber-lagging-section">
          <Text style={styles.sectionTitle}>Rubber Lagging</Text>

          <CustomDropdown
            label="Lagging Type"
            value={rubberType}
            options={['none', 'plain', 'diamond', 'ceramic'].map((t) => ({
              label: RUBBER_TYPE_LABELS[t],
              value: t,
            }))}
            onValueChange={(v) => {
              setRubberType(v);
              // Reset thickness when switching types
              if (v === 'ceramic') {
                setRubberThickness(standards?.rubber_ceramic_thicknesses[0] || 12);
              } else if (v !== 'none') {
                setRubberThickness(standards?.rubber_plain_thicknesses[0] || 8);
              }
            }}
          />

          {rubberType !== 'none' && (
            <>
              <View style={styles.spacer} />
              <CustomDropdown
                label="Rubber Thickness (mm)"
                value={rubberThickness}
                options={getRubberThicknessOptions()}
                onValueChange={(v) => setRubberThickness(v)}
              />
            </>
          )}
        </View>

        {/* Quantity & Packing */}
        <View style={styles.card} data-testid="quantity-section">
          <Text style={styles.sectionTitle}>Quantity & Packing</Text>

          <Text style={styles.inputLabel}>Quantity</Text>
          <TextInput
            style={[styles.input, errors.quantity && styles.inputError]}
            value={quantity}
            onChangeText={(v) => {
              setQuantity(v);
              setErrors((e) => ({ ...e, quantity: '' }));
            }}
            keyboardType="numeric"
            placeholder="1"
            data-testid="quantity-input"
          />
          {errors.quantity ? <Text style={styles.errorText}>{errors.quantity}</Text> : null}

          <View style={styles.spacer} />

          <CustomDropdown
            label="Packing Type"
            value={packingType}
            options={PACKING_OPTIONS}
            onValueChange={(v) => setPackingType(v)}
          />
        </View>

        {/* Calculate Button */}
        <TouchableOpacity
          style={[styles.calculateBtn, calculating && styles.calculateBtnDisabled]}
          onPress={calculateCost}
          disabled={calculating}
          data-testid="calculate-pulley-btn"
        >
          {calculating ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="calculator-outline" size={20} color="#FFFFFF" />
              <Text style={styles.calculateBtnText}>Calculate Pulley Price</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Result Card */}
        {result && (
          <View style={styles.resultCard} data-testid="pulley-result-card">
            <View style={styles.resultHeader}>
              <Text style={styles.resultTitle}>Cost Breakdown</Text>
              <View style={styles.resultBadge}>
                <Text style={styles.resultBadgeText}>{result.configuration.pulley_type}</Text>
              </View>
            </View>

            <Text style={styles.productCode}>{result.configuration.product_code}</Text>

            {/* Configuration Summary */}
            <View style={styles.configSummary}>
              <View style={styles.configRow}>
                <Text style={styles.configLabel}>Pipe</Text>
                <Text style={styles.configValue}>
                  {result.configuration.pipe_diameter_mm} x {result.configuration.pipe_thickness_mm}mm
                </Text>
              </View>
              <View style={styles.configRow}>
                <Text style={styles.configLabel}>Face Length</Text>
                <Text style={styles.configValue}>{result.configuration.face_length_mm}mm</Text>
              </View>
              <View style={styles.configRow}>
                <Text style={styles.configLabel}>Shaft</Text>
                <Text style={styles.configValue}>
                  {result.configuration.shaft_diameter_centre_mm}mm ({result.configuration.shaft_material})
                </Text>
              </View>
              <View style={styles.configRow}>
                <Text style={styles.configLabel}>Hub</Text>
                <Text style={styles.configValue}>
                  {HUB_TYPE_LABELS[result.configuration.hub_type]}
                  {result.configuration.kla_model ? ` (${result.configuration.kla_model})` : ''}
                </Text>
              </View>
              {result.configuration.rubber_type !== 'none' && (
                <View style={styles.configRow}>
                  <Text style={styles.configLabel}>Rubber</Text>
                  <Text style={styles.configValue}>
                    {RUBBER_TYPE_LABELS[result.configuration.rubber_type]} {result.configuration.rubber_thickness_mm}mm
                  </Text>
                </View>
              )}
            </View>

            {/* Cost Lines */}
            <View style={styles.costSection}>
              <View style={styles.costLine}>
                <Text style={styles.costLabel}>Pipe ({result.cost_breakdown.pipe_weight_kg} kg)</Text>
                <Text style={styles.costValue}>Rs. {result.cost_breakdown.pipe_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.costLine}>
                <Text style={styles.costLabel}>Shaft ({result.cost_breakdown.shaft_weight_kg} kg)</Text>
                <Text style={styles.costValue}>Rs. {result.cost_breakdown.shaft_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.costLine}>
                <Text style={styles.costLabel}>End Plates x{result.cost_breakdown.end_plate_qty || 2} ({result.cost_breakdown.end_plate_weight_total_kg} kg)</Text>
                <Text style={styles.costValue}>Rs. {result.cost_breakdown.end_plate_cost.toFixed(2)}</Text>
              </View>
              {result.cost_breakdown.hub_cost > 0 && (
                <View style={styles.costLine}>
                  <Text style={styles.costLabel}>Hub / KLA</Text>
                  <Text style={styles.costValue}>Rs. {result.cost_breakdown.hub_cost.toFixed(2)}</Text>
                </View>
              )}
              {result.cost_breakdown.rubber_cost > 0 && (
                <View style={styles.costLine}>
                  <Text style={styles.costLabel}>Rubber Lagging</Text>
                  <Text style={styles.costValue}>Rs. {result.cost_breakdown.rubber_cost.toFixed(2)}</Text>
                </View>
              )}

              <View style={styles.costDivider} />

              <View style={styles.costLine}>
                <Text style={styles.costLabel}>Raw Material Total</Text>
                <Text style={styles.costValue}>Rs. {result.pricing.raw_material_cost.toFixed(2)}</Text>
              </View>
              <View style={styles.costLine}>
                <Text style={styles.costLabel}>Labour (x1.3)</Text>
                <Text style={styles.costValue}>Rs. {result.pricing.labour_cost?.toFixed(2) || '0.00'}</Text>
              </View>
              <View style={styles.costLine}>
                <Text style={styles.costLabel}>Profit (x1.6)</Text>
                <Text style={styles.costValue}>Rs. {result.pricing.profit?.toFixed(2) || '0.00'}</Text>
              </View>
              <View style={styles.costLine}>
                <Text style={styles.costLabelBold}>Unit Price</Text>
                <Text style={styles.costValueBold}>Rs. {result.pricing.unit_price.toFixed(2)}</Text>
              </View>
              <View style={styles.costLine}>
                <Text style={styles.costLabel}>Qty: {result.pricing.quantity}</Text>
                <Text style={styles.costValue}>Rs. {result.pricing.order_value.toFixed(2)}</Text>
              </View>
              {result.pricing.packing_charges > 0 && (
                <View style={styles.costLine}>
                  <Text style={styles.costLabel}>Packing ({result.pricing.packing_percent}%)</Text>
                  <Text style={styles.costValue}>Rs. {result.pricing.packing_charges.toFixed(2)}</Text>
                </View>
              )}
              {result.gst && (
                <View style={styles.costLine}>
                  <Text style={styles.costLabel}>GST (18%)</Text>
                  <Text style={styles.costValue}>Rs. {result.gst.total_gst.toFixed(2)}</Text>
                </View>
              )}

              <View style={styles.costDivider} />

              <View style={styles.costLine}>
                <Text style={styles.grandTotalLabel}>GRAND TOTAL</Text>
                <Text style={styles.grandTotalValue}>Rs. {result.grand_total.toFixed(2)}</Text>
              </View>

              <View style={styles.weightInfo}>
                <Ionicons name="scale-outline" size={14} color="#64748B" />
                <Text style={styles.weightText}>
                  Weight: {result.cost_breakdown.single_pulley_weight_kg} kg/pc | Total: {result.cost_breakdown.total_weight_kg} kg
                </Text>
              </View>
            </View>

            {/* Add to Cart Button */}
            <TouchableOpacity
              style={styles.addToCartBtn}
              onPress={handleAddToCart}
              data-testid="add-pulley-to-cart-btn"
            >
              <Ionicons name="cart-outline" size={20} color="#FFFFFF" />
              <Text style={styles.addToCartText}>Add to Cart</Text>
            </TouchableOpacity>

            {/* Save Single Quote */}
            <TouchableOpacity
              style={styles.saveSingleBtn}
              onPress={saveQuote}
              disabled={savingQuote}
              data-testid="save-single-pulley-btn"
            >
              {savingQuote ? (
                <ActivityIndicator color="#960018" />
              ) : (
                <>
                  <Ionicons name="save-outline" size={20} color="#960018" />
                  <Text style={styles.saveSingleText}>Save Single Quote</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Attachments Section - before calculate or after result */}
        <View style={styles.card} data-testid="attachments-section">
          <Text style={styles.sectionTitle}>Attachments (Optional)</Text>
          <Text style={styles.hintText}>Attach drawing, photo, or document</Text>
          <View style={styles.attachBtnRow}>
            <TouchableOpacity style={styles.attachBtn} onPress={takePhoto}>
              <Ionicons name="camera" size={22} color="#960018" />
              <Text style={styles.attachBtnText}>Camera</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.attachBtn} onPress={pickImage}>
              <Ionicons name="image" size={22} color="#960018" />
              <Text style={styles.attachBtnText}>Gallery</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.attachBtn} onPress={pickDocument}>
              <Ionicons name="document" size={22} color="#960018" />
              <Text style={styles.attachBtnText}>File</Text>
            </TouchableOpacity>
          </View>
          {currentAttachments.length > 0 && (
            <View style={styles.attachList}>
              {currentAttachments.map((att, idx) => (
                <View key={idx} style={styles.attachItem}>
                  {att.type === 'image' ? (
                    <Image source={{ uri: att.uri }} style={styles.attachThumb} />
                  ) : (
                    <View style={styles.attachDocIcon}>
                      <Ionicons name="document-text" size={28} color="#960018" />
                    </View>
                  )}
                  <Text style={styles.attachName} numberOfLines={1}>{att.name}</Text>
                  <TouchableOpacity onPress={() => removeAttachment(idx)}>
                    <Ionicons name="close-circle" size={22} color="#EF4444" />
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* Product Remark */}
        <View style={styles.card} data-testid="remark-section">
          <Text style={styles.sectionTitle}>Remark (Optional)</Text>
          <TextInput
            style={[styles.input, { height: 60, textAlignVertical: 'top' }]}
            value={productRemark}
            onChangeText={setProductRemark}
            placeholder="Add any notes for this pulley..."
            multiline
            data-testid="pulley-remark-input"
          />
        </View>

        {/* Mock pricing notice */}
        <View style={styles.noticeCard} data-testid="mock-pricing-notice">
          <Ionicons name="information-circle-outline" size={18} color="#F59E0B" />
          <Text style={styles.noticeText}>
            Using placeholder pricing. Upload the filled Pulley Pricing Excel template via Admin panel for actual rates.
          </Text>
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

      <FloatingCartButton onPress={() => router.push('/cart')} count={cartCount} />
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
    marginTop: 12,
    fontSize: 16,
    color: '#64748B',
  },
  header: {
    backgroundColor: '#0F172A',
    paddingTop: 56,
    paddingBottom: 20,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginTop: 4,
  },
  headerBadge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(150, 0, 24, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    marginBottom: 12,
  },
  typeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  typeBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  typeBtnActive: {
    backgroundColor: '#960018',
    borderColor: '#960018',
  },
  typeBtnText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#64748B',
  },
  typeBtnTextActive: {
    color: '#FFFFFF',
  },
  spacer: {
    height: 12,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: '#0F172A',
    height: 44,
  },
  inputError: {
    borderColor: '#EF4444',
    backgroundColor: '#FEF2F2',
  },
  errorText: {
    fontSize: 12,
    color: '#EF4444',
    marginTop: 4,
  },
  hubTypeRow: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 4,
  },
  hubTypeBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  hubTypeBtnActive: {
    backgroundColor: '#960018',
    borderColor: '#960018',
  },
  hubTypeBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#64748B',
  },
  hubTypeBtnTextActive: {
    color: '#FFFFFF',
  },
  hubFields: {
    marginTop: 12,
  },
  klaInfoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
    padding: 10,
    backgroundColor: '#EFF6FF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  klaInfoText: {
    fontSize: 13,
    color: '#1E40AF',
    fontWeight: '500',
    flex: 1,
  },
  calculateBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#960018',
    borderRadius: 12,
    paddingVertical: 16,
    marginBottom: 16,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  calculateBtnDisabled: {
    opacity: 0.7,
  },
  calculateBtnText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  resultCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
  },
  resultBadge: {
    backgroundColor: '#960018',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  resultBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  productCode: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
    marginBottom: 12,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  configSummary: {
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  configRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  configLabel: {
    fontSize: 13,
    color: '#64748B',
  },
  configValue: {
    fontSize: 13,
    fontWeight: '600',
    color: '#0F172A',
  },
  costSection: {
    marginBottom: 16,
  },
  costLine: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  costLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  costValue: {
    fontSize: 14,
    color: '#0F172A',
    fontWeight: '500',
  },
  costLabelBold: {
    fontSize: 15,
    fontWeight: '600',
    color: '#0F172A',
  },
  costValueBold: {
    fontSize: 15,
    fontWeight: '700',
    color: '#0F172A',
  },
  costDivider: {
    height: 1,
    backgroundColor: '#E2E8F0',
    marginVertical: 8,
  },
  grandTotalLabel: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
  },
  grandTotalValue: {
    fontSize: 18,
    fontWeight: '800',
    color: '#960018',
  },
  weightInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
    padding: 8,
    backgroundColor: '#F8FAFC',
    borderRadius: 6,
  },
  weightText: {
    fontSize: 12,
    color: '#64748B',
  },
  addToCartBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#10B981',
    borderRadius: 10,
    paddingVertical: 14,
    marginBottom: 8,
  },
  addToCartText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  saveSingleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    paddingVertical: 14,
    borderWidth: 1.5,
    borderColor: '#960018',
  },
  saveSingleText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#960018',
  },
  hintText: {
    fontSize: 12,
    color: '#94A3B8',
    marginBottom: 10,
  },
  attachBtnRow: {
    flexDirection: 'row',
    gap: 12,
  },
  attachBtn: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#FFF5F5',
  },
  attachBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#960018',
  },
  attachList: {
    marginTop: 12,
    gap: 8,
  },
  attachItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#F8FAFC',
    borderRadius: 8,
    padding: 8,
  },
  attachThumb: {
    width: 40,
    height: 40,
    borderRadius: 6,
  },
  attachDocIcon: {
    width: 40,
    height: 40,
    borderRadius: 6,
    backgroundColor: '#FFF5F5',
    justifyContent: 'center',
    alignItems: 'center',
  },
  attachName: {
    flex: 1,
    fontSize: 13,
    color: '#475569',
  },
  noticeCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: '#FFFBEB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
    marginBottom: 16,
  },
  noticeText: {
    fontSize: 12,
    color: '#92400E',
    flex: 1,
    lineHeight: 18,
  },
});
