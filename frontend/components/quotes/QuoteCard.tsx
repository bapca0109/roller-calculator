import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Quote } from './types';

// Helper function to get packing percentage from packing_type
const getPackingPercentLabel = (packingType: string | undefined): string => {
  if (!packingType) return 'Standard (1%)';
  if (packingType === 'standard') return 'Standard (1%)';
  if (packingType === 'pallet') return 'Pallet (4%)';
  if (packingType === 'wooden_box') return 'Wooden Box (8%)';
  if (packingType.startsWith('custom_')) {
    const percent = packingType.split('_')[1] || '0';
    return `Custom (${percent}%)`;
  }
  return packingType;
};

interface QuoteCardProps {
  quote: Quote;
  isAdmin: boolean;
  isCustomer: boolean;
  docLabel: string;
  onPress: (quote: Quote) => void;
  formatDate: (dateString: string) => string;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => any;
}

export const QuoteCard: React.FC<QuoteCardProps> = ({
  quote,
  isAdmin,
  isCustomer,
  docLabel,
  onPress,
  formatDate,
  getStatusColor,
  getStatusIcon,
}) => {
  const isRfq = quote.quote_number?.startsWith('RFQ');
  const isApproved = quote.status?.toLowerCase() === 'approved';
  const isRejected = quote.status?.toLowerCase() === 'rejected';
  const isUnread = isAdmin && quote.status === 'pending' && isRfq && quote.read_by_admin !== true;

  return (
    <TouchableOpacity
      style={[styles.card, isUnread && styles.unreadCard]}
      onPress={() => onPress(quote)}
      data-testid={`quote-card-${quote.id}`}
    >
      <View style={styles.header}>
        <View style={styles.info}>
          <View style={styles.idRow}>
            {isUnread && <View style={styles.unreadDot} />}
            <Text style={[styles.quoteId, isUnread && styles.unreadQuoteId]}>
              {quote.quote_number || `${docLabel} #${quote.id.slice(-6).toUpperCase()}`}
            </Text>
            {/* Show revision badge for approved quotes */}
            {isApproved && (
              <View style={styles.revisionBadge}>
                <Text style={styles.revisionText}>
                  R{quote.revision_history && quote.revision_history.length > 0 
                    ? quote.revision_history.length 
                    : 0}
                </Text>
              </View>
            )}
            {quote.original_rfq_number && (
              <Text style={styles.rfqRef}>({quote.original_rfq_number})</Text>
            )}
          </View>
          <Text style={styles.date}>
            {isApproved && (quote.approved_at_ist || quote.approved_at)
              ? (quote.approved_at_ist || formatDate(quote.approved_at!))
              : (quote.created_at_ist || formatDate(quote.created_at))}
          </Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: `${getStatusColor(quote.status)}20` }]}>
          <Ionicons name={getStatusIcon(quote.status)} size={16} color={getStatusColor(quote.status)} />
          <Text style={[styles.statusText, { color: getStatusColor(quote.status) }]}>
            {quote.status?.charAt(0).toUpperCase() + quote.status?.slice(1)}
          </Text>
        </View>
      </View>

      {/* Customer & Company Name */}
      <View style={styles.customerRow}>
        {quote.customer_code && (
          <View style={styles.customerCodeBadge}>
            <Text style={styles.customerCodeText}>{quote.customer_code}</Text>
          </View>
        )}
        <Ionicons name="person-outline" size={16} color="#64748B" />
        <Text style={styles.customerName}>{quote.customer_name || 'Unknown Customer'}</Text>
      </View>
      
      {(quote.customer_details?.company || quote.customer_company) && (
        <View style={styles.companyRow}>
          <Ionicons name="business-outline" size={16} color="#64748B" />
          <Text style={styles.companyName}>{quote.customer_details?.company || quote.customer_company}</Text>
        </View>
      )}

      <View style={styles.productsList}>
        {quote.products.slice(0, 2).map((product, index) => (
          <Text key={index} style={styles.productItem} numberOfLines={1}>
            • {product.product_name || product.product_id} (Qty: {product.quantity})
          </Text>
        ))}
        {quote.products.length > 2 && (
          <Text style={styles.moreProducts}>+{quote.products.length - 2} more items</Text>
        )}
      </View>

      <View style={styles.footer}>
        <View>
          <Text style={styles.totalLabel}>{quote.products.length} item{quote.products.length !== 1 ? 's' : ''}</Text>
          {(!isCustomer || isApproved) && (
            <>
              <Text style={styles.discountBadge}>
                Discount: {quote.subtotal > 0 ? ((quote.total_discount / quote.subtotal) * 100).toFixed(1) : 0}%
              </Text>
              <Text style={styles.packingBadge}>
                Packing: {getPackingPercentLabel(quote.packing_type)}
              </Text>
            </>
          )}
        </View>
        {(!isCustomer || isApproved) && (
          <Text style={styles.totalPrice}>Rs. {quote.total_price?.toFixed(2) || '0.00'}</Text>
        )}
      </View>
      
      {isApproved && isRfq && (
        <View style={styles.approvedBadge}>
          <Ionicons name="checkmark-circle" size={18} color="#fff" />
          <Text style={styles.badgeText}>Approved</Text>
        </View>
      )}
      
      {isRejected && isRfq && (
        <View style={styles.rejectedBadge}>
          <Ionicons name="close-circle" size={18} color="#fff" />
          <Text style={styles.badgeText}>Rejected</Text>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  unreadCard: {
    borderLeftWidth: 4,
    borderLeftColor: '#EF4444',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  info: {
    flex: 1,
  },
  idRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  quoteId: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  unreadQuoteId: {
    fontWeight: '800',
  },
  rfqRef: {
    fontSize: 11,
    color: '#0066cc',
    fontWeight: '500',
  },
  revisionBadge: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  revisionText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  unreadDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#EF4444',
  },
  date: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  customerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  customerCodeBadge: {
    backgroundColor: '#960018',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  customerCodeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  customerName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  companyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  companyName: {
    fontSize: 13,
    fontWeight: '500',
    color: '#960018',
  },
  productsList: {
    marginBottom: 12,
  },
  productItem: {
    fontSize: 14,
    color: '#333',
    marginBottom: 4,
  },
  moreProducts: {
    fontSize: 13,
    color: '#666',
    fontStyle: 'italic',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#EEE',
  },
  totalLabel: {
    fontSize: 14,
    color: '#666',
  },
  discountBadge: {
    fontSize: 12,
    color: '#4CAF50',
    fontWeight: 'bold',
    marginTop: 2,
  },
  packingBadge: {
    fontSize: 12,
    color: '#2196F3',
    fontWeight: '600',
    marginTop: 2,
  },
  totalPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  approvedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  rejectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#C41E3A',
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  badgeText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default QuoteCard;
