import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useCart } from '../app/context/CartContext';
import { useAuth } from '../contexts/AuthContext';

interface FloatingCartButtonProps {
  onPress: () => void;
}

export default function FloatingCartButton({ onPress }: FloatingCartButtonProps) {
  const { user } = useAuth();
  const { cartItems, getCartTotal, getCartWeight } = useCart();
  const isCustomer = user?.role === 'customer';

  if (cartItems.length === 0) {
    return null;
  }

  return (
    <TouchableOpacity
      style={styles.button}
      onPress={onPress}
      data-testid="floating-cart-btn"
    >
      <View style={styles.iconContainer}>
        <Ionicons name="cart" size={24} color="#fff" />
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{cartItems.length}</Text>
        </View>
      </View>
      <View style={styles.textContainer}>
        <Text style={styles.itemsText}>
          {cartItems.length} item{cartItems.length !== 1 ? 's' : ''}
        </Text>
        {!isCustomer ? (
          <Text style={styles.totalText}>Rs. {getCartTotal().toFixed(0)}</Text>
        ) : (
          <Text style={styles.weightText}>{getCartWeight().toFixed(1)} kg</Text>
        )}
      </View>
      <Ionicons name="chevron-forward" size={20} color="#fff" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    position: 'absolute',
    bottom: 100,
    left: 16,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#960018',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 12,
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  iconContainer: {
    position: 'relative',
  },
  badge: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#fff',
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#960018',
  },
  textContainer: {
    flex: 1,
    marginLeft: 16,
  },
  itemsText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  totalText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 2,
  },
  weightText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 2,
  },
});
