import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { router } from 'expo-router';

interface ProductResult {
  product_code: string;
  roller_type: string;
  type_code: string;
  shaft_diameter: number;
  pipe_diameter: number;
  pipe_length?: number;
  pipe_type: string;
  bearing: string;
  bearing_make: string;
  bearing_series: string;
  housing: string;
  base_price: number;
  available_lengths: number[];
  description: string;
  exact_match?: boolean;
}

export default function SearchScreen() {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<ProductResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      Alert.alert('Enter Search Term', 'Please enter a product code to search');
      return;
    }

    setLoading(true);
    setHasSearched(true);

    try {
      const response = await api.get('/search/product-catalog', {
        params: { query: searchQuery.trim().toUpperCase() }
      });
      setResults(response.data.results || []);
      
      // Add to recent searches
      if (!recentSearches.includes(searchQuery.trim().toUpperCase())) {
        setRecentSearches(prev => [searchQuery.trim().toUpperCase(), ...prev.slice(0, 4)]);
      }
    } catch (error: any) {
      console.error('Search error:', error);
      Alert.alert('Search Error', error.response?.data?.detail || 'Failed to search');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRecentSearch = (query: string) => {
    setSearchQuery(query);
    setTimeout(() => {
      handleSearchWithQuery(query);
    }, 100);
  };

  const handleSearchWithQuery = async (query: string) => {
    setLoading(true);
    setHasSearched(true);

    try {
      const response = await api.get('/search/product-catalog', {
        params: { query: query.toUpperCase() }
      });
      setResults(response.data.results || []);
    } catch (error: any) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setResults([]);
    setHasSearched(false);
  };

  const handleSelectProduct = (item: ProductResult) => {
    // Navigate to calculator with pre-filled values
    Alert.alert(
      'Configure Product',
      `${item.description}\n\nBase price (1000mm): Rs. ${item.base_price_1000mm.toFixed(2)}`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Go to Calculator', 
          onPress: () => router.push('/(tabs)/calculator')
        }
      ]
    );
  };

  const renderResultItem = ({ item }: { item: ProductResult }) => (
    <TouchableOpacity 
      style={[styles.resultCard, item.exact_match && styles.exactMatchCard]} 
      onPress={() => handleSelectProduct(item)}
      data-testid={`product-${item.product_code}`}
    >
      <View style={styles.resultHeader}>
        <View style={styles.productCodeContainer}>
          <Text style={styles.productCodeLabel}>Product Code</Text>
          <Text style={styles.productCode}>{item.product_code}</Text>
        </View>
        <View style={[styles.typeTag, item.roller_type === 'impact' && styles.impactTag]}>
          <Text style={styles.typeTagText}>
            {item.roller_type === 'impact' ? 'Impact' : 'Carrying'}
          </Text>
        </View>
      </View>

      <View style={styles.resultBody}>
        <View style={styles.specRow}>
          <View style={styles.specItem}>
            <Ionicons name="disc-outline" size={16} color="#888" />
            <Text style={styles.specLabel}>Pipe</Text>
            <Text style={styles.specValue}>
              {item.pipe_diameter}mm {item.pipe_length ? `x ${item.pipe_length}mm` : ''}
            </Text>
          </View>
          <View style={styles.specItem}>
            <Ionicons name="git-commit-outline" size={16} color="#888" />
            <Text style={styles.specLabel}>Shaft</Text>
            <Text style={styles.specValue}>{item.shaft_diameter}mm</Text>
          </View>
        </View>

        <View style={styles.specRow}>
          <View style={styles.specItem}>
            <Ionicons name="settings-outline" size={16} color="#888" />
            <Text style={styles.specLabel}>Bearing</Text>
            <Text style={styles.specValue}>{item.bearing}</Text>
          </View>
          <View style={styles.specItem}>
            <Ionicons name="business-outline" size={16} color="#888" />
            <Text style={styles.specLabel}>Make</Text>
            <Text style={styles.specValue}>{item.bearing_make.toUpperCase()}</Text>
          </View>
        </View>

        <View style={styles.divider} />

        <View style={styles.pricingRow}>
          <View>
            <Text style={styles.priceLabel}>
              {item.exact_match ? 'Price' : 'Base Price (1000mm)'}
            </Text>
            <Text style={styles.priceValue}>Rs. {item.base_price.toFixed(2)}</Text>
          </View>
          <View style={styles.configButton}>
            <Text style={styles.configButtonText}>Configure</Text>
            <Ionicons name="arrow-forward" size={16} color="#FF6B00" />
          </View>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Product Catalog</Text>
        <Text style={styles.headerSubtitle}>Search available roller configurations</Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Ionicons name="search" size={20} color="#888" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search by code (CR, IR, 25, 6205...)"
            placeholderTextColor="#999"
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={handleSearch}
            autoCapitalize="characters"
            returnKeyType="search"
            data-testid="search-input"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={clearSearch} style={styles.clearButton} data-testid="clear-search-btn">
              <Ionicons name="close-circle" size={20} color="#888" />
            </TouchableOpacity>
          )}
        </View>
        <TouchableOpacity
          style={styles.searchButton}
          onPress={handleSearch}
          disabled={loading}
          data-testid="search-btn"
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Ionicons name="search" size={24} color="#fff" />
          )}
        </TouchableOpacity>
      </View>

      {/* Search Tips */}
      {!hasSearched && (
        <View style={styles.tipsContainer}>
          <View style={styles.tipCard}>
            <Ionicons name="bulb-outline" size={24} color="#FF6B00" />
            <View style={styles.tipContent}>
              <Text style={styles.tipTitle}>Search Tips</Text>
              <Text style={styles.tipText}>
                Search by product code or specifications:{'\n'}
                • Full code: "CR20 88465A 63S"{'\n'}
                • "CR" - Carrying rollers{'\n'}
                • "IR" - Impact rollers{'\n'}
                • "25" - 25mm shaft rollers{'\n'}
                • "6205" - Specific bearing{'\n'}
                • "SKF" - SKF branded bearings
              </Text>
            </View>
          </View>

          {/* Quick Filters */}
          <View style={styles.quickFilters}>
            <Text style={styles.quickFiltersTitle}>Quick Search</Text>
            <View style={styles.filterTags}>
              {['CR', 'IR', '25', '30', '89', '114', 'SKF', 'FAG'].map((tag) => (
                <TouchableOpacity
                  key={tag}
                  style={styles.filterTag}
                  onPress={() => handleRecentSearch(tag)}
                >
                  <Text style={styles.filterTagText}>{tag}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Recent Searches */}
          {recentSearches.length > 0 && (
            <View style={styles.recentContainer}>
              <Text style={styles.recentTitle}>Recent Searches</Text>
              <View style={styles.recentTags}>
                {recentSearches.map((search, index) => (
                  <TouchableOpacity
                    key={index}
                    style={styles.recentTag}
                    onPress={() => handleRecentSearch(search)}
                    data-testid={`recent-search-${index}`}
                  >
                    <Ionicons name="time-outline" size={14} color="#666" />
                    <Text style={styles.recentTagText}>{search}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}
        </View>
      )}

      {/* Results */}
      {hasSearched && (
        <View style={styles.resultsContainer}>
          <View style={styles.resultsHeader}>
            <Text style={styles.resultsCount}>
              {results.length} {results.length === 1 ? 'product' : 'products'} found
            </Text>
            {results.length > 0 && (
              <Text style={styles.searchedFor}>for "{searchQuery.toUpperCase()}"</Text>
            )}
          </View>

          {results.length === 0 && !loading ? (
            <View style={styles.noResults}>
              <Ionicons name="cube-outline" size={64} color="#DDD" />
              <Text style={styles.noResultsTitle}>No Products Found</Text>
              <Text style={styles.noResultsText}>
                No products match "{searchQuery.toUpperCase()}".{'\n'}
                Try a different search term.
              </Text>
            </View>
          ) : (
            <FlatList
              data={results}
              renderItem={renderResultItem}
              keyExtractor={(item, index) => `${item.product_code}-${item.bearing_make}-${index}`}
              contentContainerStyle={styles.resultsList}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    backgroundColor: '#FF6B00',
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
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
  searchContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
    gap: 12,
  },
  searchInputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    paddingHorizontal: 12,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    paddingVertical: 14,
    color: '#333',
  },
  clearButton: {
    padding: 4,
  },
  searchButton: {
    backgroundColor: '#FF6B00',
    width: 52,
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  tipsContainer: {
    padding: 16,
  },
  tipCard: {
    flexDirection: 'row',
    backgroundColor: '#FFF8F0',
    borderRadius: 12,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#FFE0C0',
  },
  tipContent: {
    flex: 1,
  },
  tipTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
  },
  tipText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 22,
  },
  quickFilters: {
    marginTop: 20,
  },
  quickFiltersTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  filterTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  filterTag: {
    backgroundColor: '#FF6B00',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  filterTagText: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  recentContainer: {
    marginTop: 20,
  },
  recentTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  recentTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  recentTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 6,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  recentTagText: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
  resultsContainer: {
    flex: 1,
  },
  resultsHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
    gap: 8,
  },
  resultsCount: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  searchedFor: {
    fontSize: 14,
    color: '#888',
  },
  resultsList: {
    padding: 16,
    paddingBottom: 100,
  },
  resultCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    overflow: 'hidden',
  },
  exactMatchCard: {
    borderWidth: 2,
    borderColor: '#4CAF50',
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    backgroundColor: '#1A1A2E',
    padding: 16,
  },
  productCodeContainer: {
    flex: 1,
  },
  productCodeLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 4,
  },
  productCode: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FF6B00',
    letterSpacing: 0.5,
  },
  typeTag: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  impactTag: {
    backgroundColor: '#2196F3',
  },
  typeTagText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  resultBody: {
    padding: 16,
  },
  specRow: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  specItem: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  specLabel: {
    fontSize: 12,
    color: '#888',
  },
  specValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  divider: {
    height: 1,
    backgroundColor: '#E0E0E0',
    marginVertical: 12,
  },
  pricingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  priceLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 2,
  },
  priceValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FF6B00',
  },
  configButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FFF3E0',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  configButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF6B00',
  },
  noResults: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingTop: 60,
  },
  noResultsTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#333',
    marginTop: 16,
    marginBottom: 8,
  },
  noResultsText: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    lineHeight: 22,
  },
});
