import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert,
  Modal,
  ScrollView,
  Platform,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

interface LengthDetail {
  length_mm: number;
  belt_widths: number[];
  weight_kg: number;
  price: number;
  product_code: string;
}

interface ProductResult {
  product_code: string;
  roller_type: string;
  type_code: string;
  shaft_diameter: number;
  pipe_diameter: number;
  rubber_diameter?: number;
  pipe_length?: number;
  pipe_type: string;
  bearing: string;
  bearing_make: string;
  bearing_series: string;
  housing: string;
  base_price: number;
  base_weight_kg?: number;
  available_lengths: number[];
  length_details?: LengthDetail[];
  description: string;
  exact_match?: boolean;
}

interface QuoteItem {
  product_code: string;
  roller_type: string;
  pipe_diameter: number;
  pipe_length: number;
  pipe_type: string;
  shaft_diameter: number;
  bearing: string;
  bearing_make: string;
  housing: string;
  rubber_diameter?: number;
  weight_kg: number;
  unit_price: number;
  quantity: number;
  belt_widths: number[];
}

export default function SearchScreen() {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<ProductResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null);
  
  // Quote builder state
  const [quoteItems, setQuoteItems] = useState<QuoteItem[]>([]);
  const [showQuoteBuilder, setShowQuoteBuilder] = useState(false);
  const [savingQuote, setSavingQuote] = useState(false);
  
  // Customer selection
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [showCustomerPicker, setShowCustomerPicker] = useState(false);
  
  // Quantity modal
  const [showQuantityModal, setShowQuantityModal] = useState(false);
  const [selectedLength, setSelectedLength] = useState<{product: ProductResult, length: LengthDetail} | null>(null);
  const [quantityInput, setQuantityInput] = useState('1');
  
  // Drawing generation
  const [generatingDrawing, setGeneratingDrawing] = useState<string | null>(null);

  useEffect(() => {
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

  // Quote functions
  const openAddToQuote = (product: ProductResult, length: LengthDetail) => {
    setSelectedLength({ product, length });
    setQuantityInput('1');
    setShowQuantityModal(true);
  };

  const addToQuote = () => {
    if (!selectedLength) return;
    
    const qty = parseInt(quantityInput) || 1;
    if (qty < 1 || qty > 10000) {
      Alert.alert('Invalid Quantity', 'Please enter a quantity between 1 and 10,000');
      return;
    }

    const { product, length } = selectedLength;
    
    const newItem: QuoteItem = {
      product_code: length.product_code,
      roller_type: product.roller_type,
      pipe_diameter: product.pipe_diameter,
      pipe_length: length.length_mm,
      pipe_type: product.pipe_type,
      shaft_diameter: product.shaft_diameter,
      bearing: product.bearing,
      bearing_make: product.bearing_make,
      housing: product.housing,
      rubber_diameter: product.rubber_diameter,
      weight_kg: length.weight_kg,
      unit_price: length.price,
      quantity: qty,
      belt_widths: length.belt_widths,
    };

    setQuoteItems([...quoteItems, newItem]);
    setShowQuantityModal(false);
    setSelectedLength(null);
    
    Alert.alert(
      'Added to Quote!', 
      `${length.product_code} x ${qty} added.\nItems in quote: ${quoteItems.length + 1}`,
      [{ text: 'OK' }, { text: 'View Quote', onPress: () => setShowQuoteBuilder(true) }]
    );
  };

  const removeFromQuote = (index: number) => {
    const newItems = [...quoteItems];
    newItems.splice(index, 1);
    setQuoteItems(newItems);
  };

  const getQuoteTotal = () => {
    return quoteItems.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
  };

  const getTotalWeight = () => {
    return quoteItems.reduce((sum, item) => sum + (item.weight_kg * item.quantity), 0);
  };

  const saveQuote = async () => {
    if (quoteItems.length === 0) {
      Alert.alert('Error', 'No items in quote');
      return;
    }

    setSavingQuote(true);
    try {
      const products = quoteItems.map(item => ({
        product_id: item.product_code,
        product_name: `${item.roller_type.charAt(0).toUpperCase() + item.roller_type.slice(1)} Roller - ${item.product_code}`,
        quantity: item.quantity,
        unit_price: item.unit_price,
        specifications: {
          pipe_diameter: item.pipe_diameter,
          pipe_length: item.pipe_length,
          pipe_type: item.pipe_type,
          shaft_diameter: item.shaft_diameter,
          bearing: item.bearing,
          bearing_make: item.bearing_make,
          housing: item.housing,
          rubber_diameter: item.rubber_diameter,
          weight_kg: item.weight_kg,
          belt_widths: item.belt_widths,
        },
        calculated_discount: 0,
        custom_premium: 0
      }));

      const response = await api.post('/quotes', {
        products,
        customer_id: selectedCustomer?.id || null,
        delivery_location: null,
        notes: `Quote from Search - ${quoteItems.length} items`
      });
      
      Alert.alert(
        'Quote Saved!', 
        `Quote Number: ${response.data.quote_number}\nCustomer: ${selectedCustomer?.name || 'N/A'}\nTotal Items: ${quoteItems.length}\nTotal: Rs. ${response.data.total_price.toFixed(2)}`,
        [{ text: 'OK', onPress: () => {
          setQuoteItems([]);
          setShowQuoteBuilder(false);
          setSelectedCustomer(null);
        }}]
      );
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to save quote');
    } finally {
      setSavingQuote(false);
    }
  };

  // Download Drawing function
  const downloadDrawing = async (product: ProductResult, length: LengthDetail) => {
    const drawingKey = `${length.product_code}`;
    setGeneratingDrawing(drawingKey);
    
    try {
      const response = await api.post('/generate-drawing', {
        product_code: length.product_code,
        roller_type: product.roller_type,
        pipe_diameter: product.pipe_diameter,
        pipe_length: length.length_mm,
        pipe_type: product.pipe_type,
        shaft_diameter: product.shaft_diameter,
        bearing: product.bearing,
        bearing_make: product.bearing_make,
        housing: product.housing,
        weight_kg: length.weight_kg,
        unit_price: length.price,
        rubber_diameter: product.rubber_diameter || null,
        belt_widths: length.belt_widths,
        quantity: 1
      }, {
        responseType: 'blob'
      });
      
      // Convert blob to base64 for file system
      const reader = new FileReader();
      reader.readAsDataURL(response.data);
      reader.onloadend = async () => {
        const base64data = reader.result as string;
        const base64 = base64data.split(',')[1];
        
        const filename = `Drawing_${length.product_code.replace(/ /g, '_').replace(/\//g, '-')}.pdf`;
        const fileUri = FileSystem.documentDirectory + filename;
        
        await FileSystem.writeAsStringAsync(fileUri, base64, {
          encoding: FileSystem.EncodingType.Base64,
        });
        
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(fileUri, {
            mimeType: 'application/pdf',
            dialogTitle: `Drawing: ${length.product_code}`
          });
        } else {
          Alert.alert('Success', `Drawing saved to: ${fileUri}`);
        }
      };
    } catch (error: any) {
      console.error('Drawing error:', error);
      Alert.alert('Error', 'Failed to generate drawing');
    } finally {
      setGeneratingDrawing(null);
    }
  };

  const renderResultItem = ({ item }: { item: ProductResult }) => {
    const isExpanded = expandedProduct === item.product_code;
    
    return (
      <View 
        style={[styles.resultCard, item.exact_match && styles.exactMatchCard]} 
        data-testid={`product-${item.product_code}`}
      >
        <View style={styles.resultHeader}>
          <View style={styles.productCodeContainer}>
            <Text style={styles.productCodeLabel}>Product Code</Text>
            <Text style={styles.productCode}>{item.product_code}</Text>
          </View>
          <View style={[
            styles.typeTag, 
            item.roller_type === 'impact' && styles.impactTag,
            item.roller_type === 'return' && styles.returnTag
          ]}>
            <Text style={styles.typeTagText}>
              {item.roller_type === 'impact' ? 'Impact' : item.roller_type === 'return' ? 'Return' : 'Carrying'}
            </Text>
          </View>
        </View>

        <View style={styles.resultBody}>
          <View style={styles.specRow}>
            <View style={styles.specItem}>
              <Ionicons name="disc-outline" size={16} color="#888" />
              <Text style={styles.specLabel}>Pipe</Text>
              <Text style={styles.specValue}>
                {item.pipe_diameter}mm {item.rubber_diameter ? `/ ${item.rubber_diameter}mm` : ''}
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

          {/* Base Weight */}
          {item.base_weight_kg && (
            <View style={styles.specRow}>
              <View style={styles.specItem}>
                <Ionicons name="scale-outline" size={16} color="#888" />
                <Text style={styles.specLabel}>Base Weight</Text>
                <Text style={styles.specValue}>{item.base_weight_kg} kg</Text>
              </View>
            </View>
          )}

          <View style={styles.divider} />

          <View style={styles.pricingRow}>
            <View>
              <Text style={styles.priceLabel}>
                {item.exact_match ? 'Price' : 'Base Price'}
              </Text>
              <Text style={styles.priceValue}>Rs. {(item.base_price || 0).toFixed(2)}</Text>
            </View>
          </View>

          {/* Expandable Length Details with Add to Quote */}
          {item.length_details && item.length_details.length > 0 && (
            <>
              <TouchableOpacity 
                style={styles.expandButton}
                onPress={() => setExpandedProduct(isExpanded ? null : item.product_code)}
              >
                <Text style={styles.expandButtonText}>
                  {isExpanded ? 'Hide' : 'Show'} Length Details ({item.length_details.length})
                </Text>
                <Ionicons 
                  name={isExpanded ? "chevron-up" : "chevron-down"} 
                  size={18} 
                  color="#960018" 
                />
              </TouchableOpacity>

              {isExpanded && (
                <View style={styles.lengthDetailsContainer}>
                  <View style={styles.lengthTableHeader}>
                    <Text style={[styles.lengthTableCell, styles.lengthTableHeaderText, { flex: 1.1 }]}>Code</Text>
                    <Text style={[styles.lengthTableCell, styles.lengthTableHeaderText, { flex: 0.5 }]}>Len</Text>
                    <Text style={[styles.lengthTableCell, styles.lengthTableHeaderText, { flex: 0.4 }]}>Wt</Text>
                    <Text style={[styles.lengthTableCell, styles.lengthTableHeaderText, { flex: 0.7 }]}>Price</Text>
                    <Text style={[styles.lengthTableCell, styles.lengthTableHeaderText, { flex: 0.8 }]}>Actions</Text>
                  </View>
                  {item.length_details.map((ld, idx) => (
                    <View key={idx} style={[styles.lengthTableRow, idx % 2 === 0 && styles.lengthTableRowAlt]}>
                      <Text style={[styles.lengthTableCell, styles.lengthCodeCell, { flex: 1.1 }]} numberOfLines={1}>
                        {ld.product_code}
                      </Text>
                      <Text style={[styles.lengthTableCell, { flex: 0.5 }]}>{ld.length_mm}</Text>
                      <Text style={[styles.lengthTableCell, { flex: 0.4 }]}>{ld.weight_kg}</Text>
                      <Text style={[styles.lengthTableCell, styles.priceCell, { flex: 0.7 }]}>₹{ld.price}</Text>
                      <View style={[styles.actionButtons, { flex: 0.8 }]}>
                        <TouchableOpacity 
                          style={styles.actionBtn}
                          onPress={() => openAddToQuote(item, ld)}
                          data-testid={`add-quote-${ld.product_code}`}
                        >
                          <Ionicons name="add-circle" size={22} color="#960018" />
                        </TouchableOpacity>
                        <TouchableOpacity 
                          style={styles.actionBtn}
                          onPress={() => downloadDrawing(item, ld)}
                          disabled={generatingDrawing === ld.product_code}
                          data-testid={`download-drawing-${ld.product_code}`}
                        >
                          {generatingDrawing === ld.product_code ? (
                            <ActivityIndicator size="small" color="#1A1A2E" />
                          ) : (
                            <Ionicons name="document-text" size={20} color="#1A1A2E" />
                          )}
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))}
                </View>
              )}
            </>
          )}
        </View>
      </View>
    );
  };

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

      {/* Quote Builder Button */}
      {quoteItems.length > 0 && (
        <TouchableOpacity 
          style={styles.quoteBuilderButton}
          onPress={() => setShowQuoteBuilder(true)}
          data-testid="view-quote-btn"
        >
          <View style={styles.quoteBuilderContent}>
            <Ionicons name="cart" size={20} color="#fff" />
            <Text style={styles.quoteBuilderText}>View Quote ({quoteItems.length} items)</Text>
          </View>
          <Text style={styles.quoteBuilderTotal}>Rs. {getQuoteTotal().toFixed(2)}</Text>
        </TouchableOpacity>
      )}

      {/* Search Tips */}
      {!hasSearched && (
        <View style={styles.tipsContainer}>
          <View style={styles.tipCard}>
            <Ionicons name="bulb-outline" size={24} color="#960018" />
            <View style={styles.tipContent}>
              <Text style={styles.tipTitle}>Search Tips</Text>
              <Text style={styles.tipText}>
                Search by product code or specifications:{'\n'}
                • Full code: "CR20 88 465A 63S"{'\n'}
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

      {/* Quantity Modal */}
      <Modal
        visible={showQuantityModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowQuantityModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.quantityModal}>
            <Text style={styles.modalTitle}>Add to Quote</Text>
            {selectedLength && (
              <>
                <Text style={styles.modalProductCode}>{selectedLength.length.product_code}</Text>
                <View style={styles.modalDetails}>
                  <Text style={styles.modalDetailText}>Length: {selectedLength.length.length_mm}mm</Text>
                  <Text style={styles.modalDetailText}>Weight: {selectedLength.length.weight_kg} kg</Text>
                  <Text style={styles.modalDetailText}>Price: Rs. {selectedLength.length.price}</Text>
                </View>
                <Text style={styles.quantityLabel}>Quantity:</Text>
                <TextInput
                  style={styles.quantityInput}
                  value={quantityInput}
                  onChangeText={setQuantityInput}
                  keyboardType="number-pad"
                  placeholder="Enter quantity"
                  data-testid="quantity-input"
                />
                <View style={styles.modalButtons}>
                  <TouchableOpacity 
                    style={styles.cancelButton}
                    onPress={() => setShowQuantityModal(false)}
                  >
                    <Text style={styles.cancelButtonText}>Cancel</Text>
                  </TouchableOpacity>
                  <TouchableOpacity 
                    style={styles.confirmButton}
                    onPress={addToQuote}
                    data-testid="confirm-add-btn"
                  >
                    <Text style={styles.confirmButtonText}>Add to Quote</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        </View>
      </Modal>

      {/* Quote Builder Modal */}
      <Modal
        visible={showQuoteBuilder}
        animationType="slide"
        onRequestClose={() => setShowQuoteBuilder(false)}
      >
        <View style={styles.quoteBuilderModal}>
          <View style={styles.quoteBuilderHeader}>
            <Text style={styles.quoteBuilderTitle}>Quote Builder</Text>
            <TouchableOpacity onPress={() => setShowQuoteBuilder(false)}>
              <Ionicons name="close" size={28} color="#333" />
            </TouchableOpacity>
          </View>

          {/* Customer Selection */}
          <TouchableOpacity 
            style={styles.customerSelector}
            onPress={() => setShowCustomerPicker(true)}
          >
            <Ionicons name="person-outline" size={20} color="#666" />
            <Text style={styles.customerSelectorText}>
              {selectedCustomer ? selectedCustomer.name : 'Select Customer (Optional)'}
            </Text>
            <Ionicons name="chevron-down" size={20} color="#666" />
          </TouchableOpacity>

          <ScrollView style={styles.quoteItemsList}>
            {quoteItems.map((item, index) => (
              <View key={index} style={styles.quoteItem}>
                <View style={styles.quoteItemHeader}>
                  <Text style={styles.quoteItemCode}>{item.product_code}</Text>
                  <TouchableOpacity onPress={() => removeFromQuote(index)}>
                    <Ionicons name="trash-outline" size={20} color="#FF5252" />
                  </TouchableOpacity>
                </View>
                <View style={styles.quoteItemDetails}>
                  <Text style={styles.quoteItemDetail}>Type: {item.roller_type}</Text>
                  <Text style={styles.quoteItemDetail}>Weight: {item.weight_kg} kg</Text>
                  <Text style={styles.quoteItemDetail}>Qty: {item.quantity}</Text>
                </View>
                <View style={styles.quoteItemPricing}>
                  <Text style={styles.quoteItemUnitPrice}>Rs. {item.unit_price.toFixed(2)} x {item.quantity}</Text>
                  <Text style={styles.quoteItemTotal}>Rs. {(item.unit_price * item.quantity).toFixed(2)}</Text>
                </View>
              </View>
            ))}
          </ScrollView>

          <View style={styles.quoteSummary}>
            <View style={styles.quoteSummaryRow}>
              <Text style={styles.quoteSummaryLabel}>Total Items:</Text>
              <Text style={styles.quoteSummaryValue}>{quoteItems.length}</Text>
            </View>
            <View style={styles.quoteSummaryRow}>
              <Text style={styles.quoteSummaryLabel}>Total Weight:</Text>
              <Text style={styles.quoteSummaryValue}>{getTotalWeight().toFixed(2)} kg</Text>
            </View>
            <View style={styles.quoteSummaryRow}>
              <Text style={styles.quoteSummaryLabel}>Total Amount:</Text>
              <Text style={styles.quoteTotalValue}>Rs. {getQuoteTotal().toFixed(2)}</Text>
            </View>
          </View>

          <TouchableOpacity 
            style={styles.saveQuoteButton}
            onPress={saveQuote}
            disabled={savingQuote || quoteItems.length === 0}
            data-testid="save-quote-btn"
          >
            {savingQuote ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="save-outline" size={20} color="#fff" />
                <Text style={styles.saveQuoteButtonText}>Save Quote</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </Modal>

      {/* Customer Picker Modal */}
      <Modal
        visible={showCustomerPicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowCustomerPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.customerPickerModal}>
            <View style={styles.customerPickerHeader}>
              <Text style={styles.customerPickerTitle}>Select Customer</Text>
              <TouchableOpacity onPress={() => setShowCustomerPicker(false)}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.customerList}>
              <TouchableOpacity 
                style={styles.customerOption}
                onPress={() => {
                  setSelectedCustomer(null);
                  setShowCustomerPicker(false);
                }}
              >
                <Text style={styles.customerOptionText}>No Customer</Text>
              </TouchableOpacity>
              {customers.map((customer) => (
                <TouchableOpacity 
                  key={customer.id}
                  style={[
                    styles.customerOption,
                    selectedCustomer?.id === customer.id && styles.customerOptionSelected
                  ]}
                  onPress={() => {
                    setSelectedCustomer(customer);
                    setShowCustomerPicker(false);
                  }}
                >
                  <Text style={styles.customerOptionName}>{customer.name}</Text>
                  {customer.company && (
                    <Text style={styles.customerOptionCompany}>{customer.company}</Text>
                  )}
                  {customer.gst_number && (
                    <Text style={styles.customerOptionGst}>GST: {customer.gst_number}</Text>
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    backgroundColor: '#960018',
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
    backgroundColor: '#960018',
    width: 52,
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quoteBuilderButton: {
    backgroundColor: '#1A1A2E',
    marginHorizontal: 16,
    marginTop: 12,
    padding: 14,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  quoteBuilderContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  quoteBuilderText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  quoteBuilderTotal: {
    color: '#4CAF50',
    fontSize: 16,
    fontWeight: 'bold',
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
    backgroundColor: '#960018',
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
    color: '#960018',
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
  returnTag: {
    backgroundColor: '#FF9800',
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
    color: '#960018',
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
  expandButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    gap: 6,
  },
  expandButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
  },
  lengthDetailsContainer: {
    marginTop: 8,
    backgroundColor: '#F9F9F9',
    borderRadius: 8,
    overflow: 'hidden',
  },
  lengthTableHeader: {
    flexDirection: 'row',
    backgroundColor: '#960018',
    paddingVertical: 10,
    paddingHorizontal: 8,
    alignItems: 'center',
  },
  lengthTableHeaderText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 11,
  },
  lengthTableRow: {
    flexDirection: 'row',
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
    alignItems: 'center',
  },
  lengthTableRowAlt: {
    backgroundColor: '#F0F0F0',
  },
  lengthTableCell: {
    fontSize: 12,
    color: '#333',
  },
  lengthCodeCell: {
    fontWeight: '500',
    color: '#1A1A2E',
  },
  priceCell: {
    fontWeight: '600',
    color: '#960018',
  },
  addButton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  actionBtn: {
    padding: 4,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  quantityModal: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '85%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  modalProductCode: {
    fontSize: 18,
    fontWeight: '600',
    color: '#960018',
    marginBottom: 16,
  },
  modalDetails: {
    backgroundColor: '#F5F5F5',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  modalDetailText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  quantityLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  quantityInput: {
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    padding: 12,
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    padding: 14,
    borderRadius: 8,
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  confirmButton: {
    flex: 1,
    padding: 14,
    borderRadius: 8,
    backgroundColor: '#960018',
    alignItems: 'center',
  },
  confirmButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  // Quote Builder Modal
  quoteBuilderModal: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  quoteBuilderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingTop: 50,
    paddingBottom: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  quoteBuilderTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  customerSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 16,
    padding: 14,
    borderRadius: 12,
    gap: 10,
  },
  customerSelectorText: {
    flex: 1,
    fontSize: 15,
    color: '#333',
  },
  quoteItemsList: {
    flex: 1,
    paddingHorizontal: 16,
  },
  quoteItem: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  quoteItemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  quoteItemCode: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#960018',
  },
  quoteItemDetails: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 8,
  },
  quoteItemDetail: {
    fontSize: 13,
    color: '#666',
  },
  quoteItemPricing: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  quoteItemUnitPrice: {
    fontSize: 14,
    color: '#666',
  },
  quoteItemTotal: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  quoteSummary: {
    backgroundColor: '#fff',
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 12,
  },
  quoteSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  quoteSummaryLabel: {
    fontSize: 14,
    color: '#666',
  },
  quoteSummaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  quoteTotalValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#960018',
  },
  saveQuoteButton: {
    flexDirection: 'row',
    backgroundColor: '#960018',
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  saveQuoteButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  // Customer Picker Modal
  customerPickerModal: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    width: '100%',
    position: 'absolute',
    bottom: 0,
  },
  customerPickerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  customerPickerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  customerList: {
    padding: 16,
  },
  customerOption: {
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  customerOptionSelected: {
    backgroundColor: '#FFF0F0',
  },
  customerOptionText: {
    fontSize: 15,
    color: '#666',
  },
  customerOptionName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  customerOptionCompany: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  customerOptionGst: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
});
