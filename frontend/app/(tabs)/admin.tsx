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
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

type MainTab = 'prices' | 'standards';
type PriceCategory = 'basic' | 'bearing' | 'seal' | 'circlip' | 'rubber' | 'locking';

interface Prices {
  basic_rates: {
    pipe_cost_per_kg: number;
    shaft_cost_per_kg: number;
  };
  bearing_costs: Record<string, Record<string, number>>;
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
  
  // Prices state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [prices, setPrices] = useState<Prices | null>(null);
  const [activeCategory, setActiveCategory] = useState<PriceCategory>('basic');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  // Standards state
  const [standardsSummary, setStandardsSummary] = useState<StandardsCollection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [collectionData, setCollectionData] = useState<StandardItem[]>([]);
  const [loadingStandards, setLoadingStandards] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<StandardItem | null>(null);

  useEffect(() => {
    if (mainTab === 'prices') {
      fetchPrices();
    } else {
      fetchStandardsSummary();
    }
  }, [mainTab]);

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

  const handleResetPrices = async () => {
    Alert.alert(
      'Reset Prices',
      'Are you sure you want to reset all prices to default values?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            try {
              setSaving(true);
              await api.post('/admin/prices/reset');
              await fetchPrices();
              Alert.alert('Success', 'All prices reset to default');
            } catch (error: any) {
              Alert.alert('Error', error.response?.data?.detail || 'Failed to reset prices');
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
              <Ionicons name="close" size={24} color="#333" />
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
        </View>
      </View>
    </Modal>
  );

  // ============= MAIN RENDER =============
  const categories: { key: PriceCategory; label: string; icon: string }[] = [
    { key: 'basic', label: 'Basic', icon: 'cash-outline' },
    { key: 'bearing', label: 'Bearing', icon: 'ellipse-outline' },
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
        </View>
      </View>

      {mainTab === 'prices' ? (
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
            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
              {activeCategory === 'basic' && renderBasicRates()}
              {activeCategory === 'bearing' && renderBearingCosts()}
              {activeCategory === 'seal' && renderSealCosts()}
              {activeCategory === 'circlip' && renderCirclipCosts()}
              {activeCategory === 'rubber' && renderRubberRingCosts()}
              {activeCategory === 'locking' && renderLockingRingCosts()}

              <TouchableOpacity
                style={styles.resetButton}
                onPress={handleResetPrices}
                disabled={saving}
              >
                <Ionicons name="refresh" size={20} color="#C41E3A" />
                <Text style={styles.resetButtonText}>Reset All to Default</Text>
              </TouchableOpacity>

              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}
        </>
      ) : (
        <>
          {loadingStandards ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#960018" />
              <Text style={styles.loadingText}>Loading standards...</Text>
            </View>
          ) : selectedCollection ? (
            renderCollectionData()
          ) : (
            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
              <Text style={styles.standardsTitle}>Product Standards Data</Text>
              <Text style={styles.standardsSubtitle}>
                Tap a collection to view and manage its data
              </Text>
              {renderStandardsSummary()}
              <View style={styles.bottomSpacer} />
            </ScrollView>
          )}
        </>
      )}

      {renderDetailModal()}

      {saving && (
        <View style={styles.savingOverlay}>
          <ActivityIndicator size="large" color="#960018" />
          <Text style={styles.savingText}>Saving...</Text>
        </View>
      )}
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
  accessDenied: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  accessDeniedText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
  },
  accessDeniedSubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
  header: {
    backgroundColor: '#960018',
    paddingTop: 60,
    paddingBottom: 16,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
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
    backgroundColor: 'rgba(255,255,255,0.2)',
    gap: 6,
  },
  mainTabActive: {
    backgroundColor: '#fff',
  },
  mainTabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  mainTabTextActive: {
    color: '#960018',
  },
  categoryTabs: {
    backgroundColor: '#fff',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  categoryTab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginHorizontal: 4,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    gap: 6,
  },
  categoryTabActive: {
    backgroundColor: '#960018',
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
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
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
    borderBottomColor: '#E5E5EA',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
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
});
