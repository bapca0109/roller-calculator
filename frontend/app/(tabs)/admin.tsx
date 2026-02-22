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
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

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

export default function AdminScreen() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [prices, setPrices] = useState<Prices | null>(null);
  const [activeCategory, setActiveCategory] = useState<PriceCategory>('basic');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    fetchPrices();
  }, []);

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

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading prices...</Text>
      </View>
    );
  }

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
          <Text style={styles.priceValue}>Rs. {value.toFixed(2)}</Text>
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
        <Text style={styles.headerSubtitle}>Raw Material Prices</Text>
      </View>

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
});
