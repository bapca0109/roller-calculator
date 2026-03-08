import React, { createContext, useContext, useState, ReactNode } from 'react';

// Attachment interface - shared across tabs
export interface Attachment {
  uri: string;
  name: string;
  type: string;
  base64?: string;
}

// Cart item interface - unified structure for both Calculator and Search
export interface CartItem {
  id: string;
  product_id: string;
  product_name: string;
  product_code: string;
  roller_type: string;
  quantity: number;
  unit_price: number;
  weight_kg: number;
  specifications: {
    pipe_diameter?: number;
    pipe_length?: number;
    pipe_type?: string;
    shaft_diameter?: number;
    bearing?: string;
    bearing_make?: string;
    housing?: string;
    rubber_diameter?: number;
    belt_widths?: number[];
  };
  remark?: string;
  attachments?: Attachment[];
  // Source tab for reference
  source: 'calculator' | 'search';
  // Original result data for calculator items (used for grand_total etc.)
  calculatorData?: any;
}

interface CartContextType {
  cartItems: CartItem[];
  addToCart: (item: Omit<CartItem, 'id'>) => void;
  removeFromCart: (id: string) => void;
  updateCartItem: (id: string, updates: Partial<CartItem>) => void;
  clearCart: () => void;
  getCartTotal: () => number;
  getCartWeight: () => number;
  cartCount: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);

  const addToCart = (item: Omit<CartItem, 'id'>) => {
    // Generate unique ID
    const newItem: CartItem = {
      ...item,
      id: `cart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
    setCartItems(prev => [...prev, newItem]);
  };

  const removeFromCart = (id: string) => {
    setCartItems(prev => prev.filter(item => item.id !== id));
  };

  const updateCartItem = (id: string, updates: Partial<CartItem>) => {
    setCartItems(prev => prev.map(item => 
      item.id === id ? { ...item, ...updates } : item
    ));
  };

  const clearCart = () => {
    setCartItems([]);
  };

  const getCartTotal = () => {
    return cartItems.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
  };

  const getCartWeight = () => {
    return cartItems.reduce((sum, item) => sum + (item.weight_kg * item.quantity), 0);
  };

  return (
    <CartContext.Provider value={{
      cartItems,
      addToCart,
      removeFromCart,
      updateCartItem,
      clearCart,
      getCartTotal,
      getCartWeight,
      cartCount: cartItems.length
    }}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};

export default CartContext;
