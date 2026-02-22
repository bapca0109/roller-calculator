import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

interface QuoteProduct {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  specifications?: Record<string, any>;
}

interface Quote {
  id: string;
  customer_name: string;
  customer_email: string;
  total_price: number;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  products: QuoteProduct[];
}

export default function QuoteDetailScreen() {
  const { id } = useLocalSearchParams();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    fetchQuote();
  }, [id]);

  const fetchQuote = async () => {
    try {
      const response = await api.get(`/quotes/${id}`);
      setQuote(response.data);
    } catch (error: any) {
      Alert.alert('Error', 'Failed to load quote');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (newStatus: string) => {
    try {
      await api.put(`/quotes/${id}`, { status: newStatus });
      Alert.alert('Success', `Quote ${newStatus} successfully`);
      fetchQuote();
    } catch (error: any) {
      Alert.alert('Error', 'Failed to update quote');
    }
  };

  const handleStatusUpdate = () => {
    Alert.alert(
      'Update Status',
      'Select new status for this quote',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Pending', onPress: () => updateStatus('pending') },
        { text: 'Processing', onPress: () => updateStatus('processing') },
        { text: 'Approved', onPress: () => updateStatus('approved') },
        { text: 'Rejected', onPress: () => updateStatus('rejected') },
      ]
    );
  };

  const getStatusColor = (status: string) => {
    switch (status) {
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

  const getStatusIcon = (status: string) => {
    switch (status) {
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

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!quote) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#007AFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Quote Details</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <View style={styles.statusSection}>
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: `${getStatusColor(quote.status)}20` },
              ]}
            >
              <Ionicons
                name={getStatusIcon(quote.status)}
                size={20}
                color={getStatusColor(quote.status)}
              />
              <Text style={[styles.statusText, { color: getStatusColor(quote.status) }]}>
                {quote.status.charAt(0).toUpperCase() + quote.status.slice(1)}
              </Text>
            </View>
            {(user?.role === 'admin' || user?.role === 'sales') && (
              <TouchableOpacity style={styles.updateButton} onPress={handleStatusUpdate}>
                <Text style={styles.updateButtonText}>Update Status</Text>
              </TouchableOpacity>
            )}
          </View>

          <View style={styles.divider} />

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Customer</Text>
            <Text style={styles.infoValue}>{quote.customer_name}</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Email</Text>
            <Text style={styles.infoValue}>{quote.customer_email}</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Created</Text>
            <Text style={styles.infoValue}>
              {new Date(quote.created_at).toLocaleDateString()}
            </Text>
          </View>

          {quote.notes && (
            <>
              <View style={styles.divider} />
              <Text style={styles.notesLabel}>Notes</Text>
              <Text style={styles.notesText}>{quote.notes}</Text>
            </>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Products</Text>

          {quote.products.map((product, index) => (
            <View key={index}>
              {index > 0 && <View style={styles.productDivider} />}
              <View style={styles.productItem}>
                <View style={styles.productInfo}>
                  <Text style={styles.productName}>{product.product_name}</Text>
                  <Text style={styles.productQuantity}>Qty: {product.quantity}</Text>
                </View>
                <View style={styles.productPricing}>
                  <Text style={styles.unitPrice}>${product.unit_price.toFixed(2)}</Text>
                  <Text style={styles.lineTotal}>
                    ${(product.quantity * product.unit_price).toFixed(2)}
                  </Text>
                </View>
              </View>
            </View>
          ))}

          <View style={styles.divider} />

          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Total Amount</Text>
            <Text style={styles.totalPrice}>${quote.total_price.toFixed(2)}</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#000',
    flex: 1,
    textAlign: 'center',
  },
  content: {
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusSection: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 16,
    gap: 6,
  },
  statusText: {
    fontSize: 16,
    fontWeight: '600',
  },
  updateButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  updateButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E5EA',
    marginVertical: 16,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  infoLabel: {
    fontSize: 16,
    color: '#8E8E93',
  },
  infoValue: {
    fontSize: 16,
    color: '#3C3C43',
    fontWeight: '500',
  },
  notesLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    marginBottom: 8,
  },
  notesText: {
    fontSize: 14,
    color: '#3C3C43',
    lineHeight: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000',
    marginBottom: 16,
  },
  productItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
  },
  productInfo: {
    flex: 1,
    marginRight: 16,
  },
  productName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#000',
    marginBottom: 4,
  },
  productQuantity: {
    fontSize: 14,
    color: '#8E8E93',
  },
  productPricing: {
    alignItems: 'flex-end',
  },
  unitPrice: {
    fontSize: 14,
    color: '#8E8E93',
    marginBottom: 4,
  },
  lineTotal: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
  productDivider: {
    height: 1,
    backgroundColor: '#F2F2F7',
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  totalLabel: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  totalPrice: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#007AFF',
  },
});
