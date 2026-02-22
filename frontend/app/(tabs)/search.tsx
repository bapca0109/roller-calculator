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

interface SearchResult {
  id: string;
  product_code: string;
  roller_type: string;
  configuration: {
    pipe_diameter_mm: number;
    pipe_length_mm: number;
    pipe_type: string;
    shaft_diameter_mm: number;
    bearing: string;
    bearing_make: string;
    housing: string;
    rubber_diameter_mm?: number;
    quantity: number;
  };
  pricing: {
    unit_price: number;
    order_value: number;
    discount_percent: number;
    final_price: number;
  };
  grand_total: number;
  customer_name: string;
  created_at: string;
  quote_number: string;
}

export default function SearchScreen() {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
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
      const response = await api.get('/search/product-code', {
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
    // Trigger search after setting query
    setTimeout(() => {
      handleSearchWithQuery(query);
    }, 100);
  };

  const handleSearchWithQuery = async (query: string) => {
    setLoading(true);
    setHasSearched(true);

    try {
      const response = await api.get('/search/product-code', {
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const renderResultItem = ({ item }: { item: SearchResult }) => (
    <View style={styles.resultCard} data-testid={`search-result-${item.id}`}>
      <View style={styles.resultHeader}>
        <View style={styles.productCodeContainer}>
          <Text style={styles.productCodeLabel}>Product Code</Text>
          <Text style={styles.productCode}>{item.product_code}</Text>
        </View>
        <View style={styles.quoteTag}>
          <Text style={styles.quoteTagText}>{item.quote_number}</Text>
        </View>
      </View>

      <View style={styles.resultBody}>
        <View style={styles.specRow}>
          <View style={styles.specItem}>
            <Text style={styles.specLabel}>Type</Text>
            <Text style={styles.specValue}>
              {item.roller_type === 'impact' ? 'Impact' : 'Carrying'}
            </Text>
          </View>
          <View style={styles.specItem}>
            <Text style={styles.specLabel}>Pipe</Text>
            <Text style={styles.specValue}>
              {item.configuration.pipe_diameter_mm}mm x {item.configuration.pipe_length_mm}mm
            </Text>
          </View>
        </View>

        <View style={styles.specRow}>
          <View style={styles.specItem}>
            <Text style={styles.specLabel}>Shaft</Text>
            <Text style={styles.specValue}>{item.configuration.shaft_diameter_mm}mm</Text>
          </View>
          <View style={styles.specItem}>
            <Text style={styles.specLabel}>Bearing</Text>
            <Text style={styles.specValue}>
              {item.configuration.bearing} ({item.configuration.bearing_make.toUpperCase()})
            </Text>
          </View>
        </View>

        {item.configuration.rubber_diameter_mm && (
          <View style={styles.specRow}>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>Rubber</Text>
              <Text style={styles.specValue}>{item.configuration.rubber_diameter_mm}mm</Text>
            </View>
            <View style={styles.specItem}>
              <Text style={styles.specLabel}>Quantity</Text>
              <Text style={styles.specValue}>{item.configuration.quantity} pcs</Text>
            </View>
          </View>
        )}

        <View style={styles.divider} />

        <View style={styles.pricingRow}>
          <View style={styles.priceItem}>
            <Text style={styles.priceLabel}>Unit Price</Text>
            <Text style={styles.priceValue}>Rs. {item.pricing.unit_price.toFixed(2)}</Text>
          </View>
          <View style={styles.priceItem}>
            <Text style={styles.priceLabel}>Total</Text>
            <Text style={styles.totalValue}>Rs. {item.grand_total.toFixed(2)}</Text>
          </View>
        </View>

        <View style={styles.metaRow}>
          <Text style={styles.metaText}>
            <Ionicons name="person-outline" size={12} color="#888" /> {item.customer_name}
          </Text>
          <Text style={styles.metaText}>
            <Ionicons name="calendar-outline" size={12} color="#888" /> {formatDate(item.created_at)}
          </Text>
        </View>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Search Products</Text>
        <Text style={styles.headerSubtitle}>Find rollers by product code</Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Ionicons name="search" size={20} color="#888" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="Enter product code (e.g., CR25 89)"
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
                Search by full or partial product code:{'\n'}
                - "CR25" - All carrying rollers with 25mm shaft{'\n'}
                - "IR" - All impact rollers{'\n'}
                - "89" - All 89mm pipe rollers{'\n'}
                - "62S" - All SKF 62 series bearing rollers
              </Text>
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
              {results.length} {results.length === 1 ? 'result' : 'results'} found
            </Text>
            {results.length > 0 && (
              <Text style={styles.searchedFor}>for "{searchQuery.toUpperCase()}"</Text>
            )}
          </View>

          {results.length === 0 && !loading ? (
            <View style={styles.noResults}>
              <Ionicons name="search-outline" size={64} color="#DDD" />
              <Text style={styles.noResultsTitle}>No Results Found</Text>
              <Text style={styles.noResultsText}>
                No products match "{searchQuery.toUpperCase()}".{'\n'}
                Try a different search term.
              </Text>
            </View>
          ) : (
            <FlatList
              data={results}
              renderItem={renderResultItem}
              keyExtractor={(item) => item.id}
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
  quoteTag: {
    backgroundColor: '#FF6B00',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  quoteTagText: {
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
  },
  specLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 2,
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
    marginBottom: 12,
  },
  priceItem: {
    alignItems: 'flex-start',
  },
  priceLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 2,
  },
  priceValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FF6B00',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F0F0F0',
  },
  metaText: {
    fontSize: 12,
    color: '#888',
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
