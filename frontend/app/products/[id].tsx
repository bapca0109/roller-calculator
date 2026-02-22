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

interface Product {
  id: string;
  name: string;
  sku: string;
  description: string;
  category: string;
  base_price: number;
  specifications: {
    dimensions?: string;
    weight?: string;
    material?: string;
    technical_specs?: Record<string, any>;
  };
}

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    fetchProduct();
  }, [id]);

  const fetchProduct = async () => {
    try {
      const response = await api.get(`/products/${id}`);
      setProduct(response.data);
    } catch (error: any) {
      Alert.alert('Error', 'Failed to load product');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    Alert.alert(
      'Delete Product',
      'Are you sure you want to delete this product?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.delete(`/products/${id}`);
              Alert.alert('Success', 'Product deleted successfully');
              router.back();
            } catch (error: any) {
              Alert.alert('Error', 'Failed to delete product');
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!product) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#007AFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Product Details</Text>
        {user?.role === 'admin' && (
          <TouchableOpacity onPress={handleDelete} style={styles.deleteButton}>
            <Ionicons name="trash-outline" size={24} color="#C41E3A" />
          </TouchableOpacity>
        )}
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <View style={styles.titleSection}>
            <Text style={styles.productName}>{product.name}</Text>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{product.category}</Text>
            </View>
          </View>

          <Text style={styles.sku}>SKU: {product.sku}</Text>
          <Text style={styles.price}>${product.base_price.toFixed(2)}</Text>

          <View style={styles.divider} />

          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.description}>{product.description}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Specifications</Text>

          {product.specifications.dimensions && (
            <View style={styles.specRow}>
              <View style={styles.specLabel}>
                <Ionicons name="resize-outline" size={20} color="#8E8E93" />
                <Text style={styles.specLabelText}>Dimensions</Text>
              </View>
              <Text style={styles.specValue}>{product.specifications.dimensions}</Text>
            </View>
          )}

          {product.specifications.weight && (
            <>
              <View style={styles.specDivider} />
              <View style={styles.specRow}>
                <View style={styles.specLabel}>
                  <Ionicons name="barbell-outline" size={20} color="#8E8E93" />
                  <Text style={styles.specLabelText}>Weight</Text>
                </View>
                <Text style={styles.specValue}>{product.specifications.weight}</Text>
              </View>
            </>
          )}

          {product.specifications.material && (
            <>
              <View style={styles.specDivider} />
              <View style={styles.specRow}>
                <View style={styles.specLabel}>
                  <Ionicons name="cube-outline" size={20} color="#8E8E93" />
                  <Text style={styles.specLabelText}>Material</Text>
                </View>
                <Text style={styles.specValue}>{product.specifications.material}</Text>
              </View>
            </>
          )}

          {product.specifications.technical_specs &&
            Object.entries(product.specifications.technical_specs).map(
              ([key, value], index) => (
                <React.Fragment key={key}>
                  <View style={styles.specDivider} />
                  <View style={styles.specRow}>
                    <View style={styles.specLabel}>
                      <Ionicons name="information-circle-outline" size={20} color="#8E8E93" />
                      <Text style={styles.specLabelText}>
                        {key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
                      </Text>
                    </View>
                    <Text style={styles.specValue}>{String(value)}</Text>
                  </View>
                </React.Fragment>
              )
            )}
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
  deleteButton: {
    padding: 8,
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
  titleSection: {
    marginBottom: 8,
  },
  productName: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
    marginBottom: 8,
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: '#007AFF20',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  badgeText: {
    color: '#007AFF',
    fontSize: 12,
    fontWeight: '600',
  },
  sku: {
    fontSize: 14,
    color: '#8E8E93',
    marginBottom: 8,
  },
  price: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 16,
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E5EA',
    marginVertical: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000',
    marginBottom: 12,
  },
  description: {
    fontSize: 16,
    color: '#3C3C43',
    lineHeight: 24,
  },
  specRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  specLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  specLabelText: {
    fontSize: 16,
    color: '#3C3C43',
  },
  specValue: {
    fontSize: 16,
    color: '#8E8E93',
    fontWeight: '500',
    maxWidth: '45%',
    textAlign: 'right',
  },
  specDivider: {
    height: 1,
    backgroundColor: '#E5E5EA',
  },
});
