import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useCart } from '../app/context/CartContext';
import { useAuth } from '../contexts/AuthContext';

interface CartViewModalProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: () => void;
}

export default function CartViewModal({
  visible,
  onClose,
  onSubmit,
}: CartViewModalProps) {
  const { user } = useAuth();
  const { cartItems, removeFromCart, getCartTotal, getCartWeight } = useCart();
  const isCustomer = user?.role === 'customer';

  return (
    <Modal
      visible={visible}
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>
            {isCustomer ? 'RFQ Cart' : 'Quote Cart'}
          </Text>
          <TouchableOpacity onPress={onClose}>
            <Ionicons name="close" size={28} color="#333" />
          </TouchableOpacity>
        </View>

        {/* Cart Items */}
        {cartItems.length === 0 ? (
          <View style={styles.emptyCart}>
            <Ionicons name="cart-outline" size={64} color="#E2E8F0" />
            <Text style={styles.emptyCartTitle}>Your cart is empty</Text>
            <Text style={styles.emptyCartText}>
              Add items from Calculator or Search tabs
            </Text>
          </View>
        ) : (
          <ScrollView style={styles.itemsList}>
            {cartItems.map((item, index) => (
              <View key={item.id} style={styles.cartItem} data-testid={`cart-item-${index}`}>
                <View style={styles.itemHeader}>
                  <View style={styles.itemCodeContainer}>
                    <Text style={styles.itemCode}>{item.product_code}</Text>
                    <View style={[
                      styles.sourceTag,
                      item.source === 'calculator' ? styles.calculatorTag : styles.searchTag
                    ]}>
                      <Text style={styles.sourceTagText}>
                        {item.source === 'calculator' ? 'CALC' : 'SEARCH'}
                      </Text>
                    </View>
                  </View>
                  <TouchableOpacity
                    onPress={() => removeFromCart(item.id)}
                    style={styles.removeBtn}
                    data-testid={`remove-item-${index}`}
                  >
                    <Ionicons name="trash-outline" size={20} color="#EF4444" />
                  </TouchableOpacity>
                </View>

                <Text style={styles.itemName}>{item.product_name}</Text>

                <View style={styles.itemSpecs}>
                  {item.specifications.pipe_diameter && (
                    <Text style={styles.specText}>
                      Pipe: {item.specifications.pipe_diameter}mm x {item.specifications.pipe_length}mm
                    </Text>
                  )}
                  {item.specifications.bearing && (
                    <Text style={styles.specText}>
                      Bearing: {item.specifications.bearing} ({item.specifications.bearing_make?.toUpperCase()})
                    </Text>
                  )}
                </View>

                <View style={styles.itemFooter}>
                  <View style={styles.quantityContainer}>
                    <Text style={styles.quantityLabel}>Qty:</Text>
                    <Text style={styles.quantityValue}>{item.quantity}</Text>
                  </View>
                  <View style={styles.weightContainer}>
                    <Text style={styles.weightLabel}>Weight:</Text>
                    <Text style={styles.weightValue}>{(item.weight_kg * item.quantity).toFixed(2)} kg</Text>
                  </View>
                  {!isCustomer && (
                    <View style={styles.priceContainer}>
                      <Text style={styles.priceValue}>
                        Rs. {(item.unit_price * item.quantity).toFixed(2)}
                      </Text>
                    </View>
                  )}
                </View>

                {/* Show remark if present */}
                {item.remark && (
                  <View style={styles.remarkContainer}>
                    <Ionicons name="chatbubble-outline" size={14} color="#64748B" />
                    <Text style={styles.remarkText}>{item.remark}</Text>
                  </View>
                )}

                {/* Show attachments count */}
                {item.attachments && item.attachments.length > 0 && (
                  <View style={styles.attachmentsRow}>
                    <Ionicons name="attach" size={14} color="#64748B" />
                    <Text style={styles.attachmentsText}>
                      {item.attachments.length} attachment{item.attachments.length !== 1 ? 's' : ''}
                    </Text>
                  </View>
                )}
              </View>
            ))}
          </ScrollView>
        )}

        {/* Summary & Submit */}
        {cartItems.length > 0 && (
          <View style={styles.footer}>
            <View style={styles.summary}>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Total Items:</Text>
                <Text style={styles.summaryValue}>{cartItems.length}</Text>
              </View>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Total Weight:</Text>
                <Text style={styles.summaryValue}>{getCartWeight().toFixed(2)} kg</Text>
              </View>
              {!isCustomer && (
                <View style={styles.summaryRow}>
                  <Text style={styles.summaryLabel}>Total Amount:</Text>
                  <Text style={styles.totalValue}>Rs. {getCartTotal().toFixed(2)}</Text>
                </View>
              )}
            </View>

            <TouchableOpacity
              style={styles.submitButton}
              onPress={onSubmit}
              data-testid="proceed-to-submit-btn"
            >
              <Ionicons name="arrow-forward" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>
                Proceed to {isCustomer ? 'Submit RFQ' : 'Submit Quote'}
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingTop: 56,
    paddingBottom: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
  },
  emptyCart: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  emptyCartTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0F172A',
    marginTop: 16,
  },
  emptyCartText: {
    fontSize: 14,
    color: '#64748B',
    textAlign: 'center',
    marginTop: 8,
  },
  itemsList: {
    flex: 1,
    padding: 16,
  },
  cartItem: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  itemCodeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  itemCode: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  sourceTag: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  calculatorTag: {
    backgroundColor: '#DBEAFE',
  },
  searchTag: {
    backgroundColor: '#D1FAE5',
  },
  sourceTagText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#0F172A',
  },
  removeBtn: {
    padding: 4,
  },
  itemName: {
    fontSize: 14,
    color: '#0F172A',
    marginBottom: 8,
  },
  itemSpecs: {
    marginBottom: 12,
  },
  specText: {
    fontSize: 12,
    color: '#64748B',
    marginBottom: 2,
  },
  itemFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  quantityLabel: {
    fontSize: 12,
    color: '#64748B',
  },
  quantityValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  weightContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginLeft: 16,
  },
  weightLabel: {
    fontSize: 12,
    color: '#64748B',
  },
  weightValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  priceContainer: {
    flex: 1,
    alignItems: 'flex-end',
  },
  priceValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
  },
  remarkContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  remarkText: {
    flex: 1,
    fontSize: 12,
    color: '#64748B',
    fontStyle: 'italic',
  },
  attachmentsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  attachmentsText: {
    fontSize: 12,
    color: '#64748B',
  },
  footer: {
    backgroundColor: '#fff',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
  },
  summary: {
    marginBottom: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  summaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  submitButton: {
    flexDirection: 'row',
    backgroundColor: '#960018',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
});
