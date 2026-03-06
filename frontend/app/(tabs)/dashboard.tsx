import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Dimensions,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LineChart, BarChart, PieChart } from 'react-native-chart-kit';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';

const screenWidth = Dimensions.get('window').width;

interface DashboardSummary {
  total_quotes: number;
  approved_quotes: number;
  pending_rfqs: number;
  total_customers: number;
  new_customers_this_month: number;
  total_revenue: number;
  monthly_revenue: number;
  revenue_growth: number;
  avg_quote_value: number;
  conversion_rate: number;
}

interface RevenueTrend {
  month: string;
  year: number;
  revenue: number;
  quotes: number;
}

interface TopCustomer {
  customer_id: string;
  customer_name: string;
  company: string;
  total_revenue: number;
  quote_count: number;
}

interface RollerTypeData {
  roller_type: string;
  count: number;
  total_value: number;
}

interface RecentQuote {
  quote_number: string;
  customer_name: string;
  company: string;
  total_price: number;
  status: string;
  created_at: string;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrend[]>([]);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [rollerTypes, setRollerTypes] = useState<RollerTypeData[]>([]);
  const [recentQuotes, setRecentQuotes] = useState<RecentQuote[]>([]);
  const [quoteStatus, setQuoteStatus] = useState<{approved: number, pending: number}>({approved: 0, pending: 0});

  const fetchDashboardData = useCallback(async () => {
    try {
      const [
        summaryRes,
        trendRes,
        customersRes,
        statusRes,
        rollerRes,
        activityRes
      ] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get('/analytics/revenue-trend?months=6'),
        api.get('/analytics/top-customers?limit=5'),
        api.get('/analytics/quote-status'),
        api.get('/analytics/roller-type-distribution'),
        api.get('/analytics/recent-activity?limit=5')
      ]);

      setSummary(summaryRes.data.summary);
      setRevenueTrend(trendRes.data.trends);
      setTopCustomers(customersRes.data.top_customers);
      setQuoteStatus(statusRes.data.distribution);
      setRollerTypes(rollerRes.data.distribution);
      setRecentQuotes(activityRes.data.recent_quotes);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  const formatCurrency = (value: number) => {
    if (value >= 10000000) {
      return `₹${(value / 10000000).toFixed(2)}Cr`;
    } else if (value >= 100000) {
      return `₹${(value / 100000).toFixed(2)}L`;
    } else if (value >= 1000) {
      return `₹${(value / 1000).toFixed(1)}K`;
    }
    return `₹${value.toFixed(0)}`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  };

  if (user?.role !== 'admin') {
    return (
      <View style={styles.container}>
        <View style={styles.accessDenied}>
          <Ionicons name="lock-closed" size={64} color="#94A3B8" />
          <Text style={styles.accessDeniedText}>Admin Access Required</Text>
          <Text style={styles.accessDeniedSubtext}>
            Dashboard is only available for administrators
          </Text>
        </View>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading Dashboard...</Text>
      </View>
    );
  }

  const chartConfig = {
    backgroundGradientFrom: '#FFFFFF',
    backgroundGradientTo: '#FFFFFF',
    color: (opacity = 1) => `rgba(150, 0, 24, ${opacity})`,
    strokeWidth: 2,
    barPercentage: 0.6,
    useShadowColorFromDataset: false,
    decimalPlaces: 0,
    labelColor: (opacity = 1) => `rgba(100, 116, 139, ${opacity})`,
    propsForLabels: {
      fontSize: 10,
    },
  };

  const revenueChartData = {
    labels: revenueTrend.map(t => t.month),
    datasets: [
      {
        data: revenueTrend.map(t => t.revenue / 1000), // Convert to thousands
        color: (opacity = 1) => `rgba(150, 0, 24, ${opacity})`,
        strokeWidth: 2,
      },
    ],
  };

  const quotesChartData = {
    labels: revenueTrend.map(t => t.month),
    datasets: [
      {
        data: revenueTrend.map(t => t.quotes || 0),
      },
    ],
  };

  const pieData = [
    {
      name: 'Approved',
      count: quoteStatus.approved || 0,
      color: '#4CAF50',
      legendFontColor: '#64748B',
      legendFontSize: 12,
    },
    {
      name: 'Pending',
      count: quoteStatus.pending || 0,
      color: '#F59E0B',
      legendFontColor: '#64748B',
      legendFontSize: 12,
    },
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#960018']} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Dashboard</Text>
        <Text style={styles.headerSubtitle}>Analytics & Insights</Text>
      </View>

      {/* Summary Cards Row 1 */}
      <View style={styles.cardsRow}>
        <View style={[styles.summaryCard, styles.cardRevenue]}>
          <View style={styles.cardIconContainer}>
            <Ionicons name="cash-outline" size={24} color="#4CAF50" />
          </View>
          <Text style={styles.cardValue}>{formatCurrency(summary?.total_revenue || 0)}</Text>
          <Text style={styles.cardLabel}>Total Revenue</Text>
          <View style={[styles.badge, summary?.revenue_growth && summary.revenue_growth >= 0 ? styles.badgeGreen : styles.badgeRed]}>
            <Ionicons 
              name={summary?.revenue_growth && summary.revenue_growth >= 0 ? "trending-up" : "trending-down"} 
              size={12} 
              color={summary?.revenue_growth && summary.revenue_growth >= 0 ? "#4CAF50" : "#EF4444"} 
            />
            <Text style={[styles.badgeText, summary?.revenue_growth && summary.revenue_growth >= 0 ? styles.badgeTextGreen : styles.badgeTextRed]}>
              {summary?.revenue_growth?.toFixed(1)}%
            </Text>
          </View>
        </View>

        <View style={[styles.summaryCard, styles.cardQuotes]}>
          <View style={styles.cardIconContainer}>
            <Ionicons name="document-text-outline" size={24} color="#960018" />
          </View>
          <Text style={styles.cardValue}>{summary?.total_quotes || 0}</Text>
          <Text style={styles.cardLabel}>Total Quotes</Text>
          <View style={styles.miniStats}>
            <Text style={styles.miniStatsText}>
              {summary?.approved_quotes || 0} approved
            </Text>
          </View>
        </View>
      </View>

      {/* Summary Cards Row 2 */}
      <View style={styles.cardsRow}>
        <View style={[styles.summaryCard, styles.cardCustomers]}>
          <View style={styles.cardIconContainer}>
            <Ionicons name="people-outline" size={24} color="#3B82F6" />
          </View>
          <Text style={styles.cardValue}>{summary?.total_customers || 0}</Text>
          <Text style={styles.cardLabel}>Customers</Text>
          <View style={styles.miniStats}>
            <Text style={styles.miniStatsText}>
              +{summary?.new_customers_this_month || 0} this month
            </Text>
          </View>
        </View>

        <View style={[styles.summaryCard, styles.cardConversion]}>
          <View style={styles.cardIconContainer}>
            <Ionicons name="analytics-outline" size={24} color="#8B5CF6" />
          </View>
          <Text style={styles.cardValue}>{summary?.conversion_rate?.toFixed(0)}%</Text>
          <Text style={styles.cardLabel}>Conversion Rate</Text>
          <View style={styles.miniStats}>
            <Text style={styles.miniStatsText}>
              Avg: {formatCurrency(summary?.avg_quote_value || 0)}
            </Text>
          </View>
        </View>
      </View>

      {/* Revenue Trend Chart */}
      <View style={styles.chartCard}>
        <Text style={styles.chartTitle}>Revenue Trend (₹ in Thousands)</Text>
        {revenueTrend.length > 0 ? (
          <LineChart
            data={revenueChartData}
            width={screenWidth - 48}
            height={200}
            chartConfig={chartConfig}
            bezier
            style={styles.chart}
            withInnerLines={false}
            withOuterLines={true}
            withDots={true}
            withShadow={false}
          />
        ) : (
          <View style={styles.noDataContainer}>
            <Text style={styles.noDataText}>No revenue data available</Text>
          </View>
        )}
      </View>

      {/* Quotes Chart */}
      <View style={styles.chartCard}>
        <Text style={styles.chartTitle}>Monthly Quotes</Text>
        {revenueTrend.length > 0 && revenueTrend.some(t => t.quotes > 0) ? (
          <BarChart
            data={quotesChartData}
            width={screenWidth - 48}
            height={200}
            chartConfig={{
              ...chartConfig,
              color: (opacity = 1) => `rgba(59, 130, 246, ${opacity})`,
            }}
            style={styles.chart}
            withInnerLines={false}
            showValuesOnTopOfBars={true}
            fromZero={true}
            yAxisLabel=""
            yAxisSuffix=""
          />
        ) : (
          <View style={styles.noDataContainer}>
            <Text style={styles.noDataText}>No quote data available</Text>
          </View>
        )}
      </View>

      {/* Quote Status Distribution */}
      <View style={styles.chartCard}>
        <Text style={styles.chartTitle}>Quote Status</Text>
        {(quoteStatus.approved > 0 || quoteStatus.pending > 0) ? (
          <PieChart
            data={pieData}
            width={screenWidth - 48}
            height={180}
            chartConfig={chartConfig}
            accessor="count"
            backgroundColor="transparent"
            paddingLeft="15"
            absolute
          />
        ) : (
          <View style={styles.noDataContainer}>
            <Text style={styles.noDataText}>No status data available</Text>
          </View>
        )}
      </View>

      {/* Top Customers */}
      <View style={styles.listCard}>
        <Text style={styles.chartTitle}>Top Customers by Revenue</Text>
        {topCustomers.length > 0 ? (
          topCustomers.map((customer, index) => (
            <View key={customer.customer_id} style={styles.listItem}>
              <View style={styles.listRank}>
                <Text style={styles.rankText}>#{index + 1}</Text>
              </View>
              <View style={styles.listContent}>
                <Text style={styles.listName}>{customer.customer_name}</Text>
                <Text style={styles.listCompany}>{customer.company || 'N/A'}</Text>
              </View>
              <View style={styles.listStats}>
                <Text style={styles.listRevenue}>{formatCurrency(customer.total_revenue)}</Text>
                <Text style={styles.listQuotes}>{customer.quote_count} quotes</Text>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.noDataContainer}>
            <Text style={styles.noDataText}>No customer data available</Text>
          </View>
        )}
      </View>

      {/* Roller Type Distribution */}
      <View style={styles.listCard}>
        <Text style={styles.chartTitle}>Roller Type Distribution</Text>
        {rollerTypes.length > 0 ? (
          rollerTypes.map((type, index) => (
            <View key={type.roller_type} style={styles.rollerItem}>
              <View style={[styles.rollerIcon, { backgroundColor: index === 0 ? '#960018' : index === 1 ? '#3B82F6' : '#8B5CF6' }]}>
                <Text style={styles.rollerIconText}>{type.roller_type.charAt(0)}</Text>
              </View>
              <View style={styles.rollerContent}>
                <Text style={styles.rollerName}>{type.roller_type}</Text>
                <View style={styles.progressBar}>
                  <View 
                    style={[
                      styles.progressFill, 
                      { 
                        width: `${Math.min((type.count / (rollerTypes[0]?.count || 1)) * 100, 100)}%`,
                        backgroundColor: index === 0 ? '#960018' : index === 1 ? '#3B82F6' : '#8B5CF6'
                      }
                    ]} 
                  />
                </View>
              </View>
              <View style={styles.rollerStats}>
                <Text style={styles.rollerCount}>{type.count}</Text>
                <Text style={styles.rollerValue}>{formatCurrency(type.total_value)}</Text>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.noDataContainer}>
            <Text style={styles.noDataText}>No roller data available</Text>
          </View>
        )}
      </View>

      {/* Recent Quotes */}
      <View style={styles.listCard}>
        <Text style={styles.chartTitle}>Recent Quotes</Text>
        {recentQuotes.length > 0 ? (
          recentQuotes.map((quote) => (
            <View key={quote.quote_number} style={styles.recentItem}>
              <View style={styles.recentLeft}>
                <Text style={styles.recentNumber}>{quote.quote_number}</Text>
                <Text style={styles.recentCustomer}>{quote.customer_name}</Text>
              </View>
              <View style={styles.recentRight}>
                <Text style={styles.recentPrice}>{formatCurrency(quote.total_price || 0)}</Text>
                <View style={[styles.statusBadge, quote.status === 'approved' ? styles.statusApproved : styles.statusPending]}>
                  <Text style={[styles.statusText, quote.status === 'approved' ? styles.statusTextApproved : styles.statusTextPending]}>
                    {quote.status === 'approved' ? 'Approved' : 'Pending'}
                  </Text>
                </View>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.noDataContainer}>
            <Text style={styles.noDataText}>No recent quotes</Text>
          </View>
        )}
      </View>

      {/* Footer Spacing */}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F1F5F9',
  },
  content: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F1F5F9',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#64748B',
  },
  accessDenied: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  accessDeniedText: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
    marginTop: 16,
  },
  accessDeniedSubtext: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 8,
    textAlign: 'center',
  },
  header: {
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#0F172A',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#64748B',
    marginTop: 4,
  },
  cardsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  cardRevenue: {
    borderLeftWidth: 4,
    borderLeftColor: '#4CAF50',
  },
  cardQuotes: {
    borderLeftWidth: 4,
    borderLeftColor: '#960018',
  },
  cardCustomers: {
    borderLeftWidth: 4,
    borderLeftColor: '#3B82F6',
  },
  cardConversion: {
    borderLeftWidth: 4,
    borderLeftColor: '#8B5CF6',
  },
  cardIconContainer: {
    marginBottom: 8,
  },
  cardValue: {
    fontSize: 24,
    fontWeight: '800',
    color: '#0F172A',
  },
  cardLabel: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 4,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  badgeGreen: {
    backgroundColor: '#DCFCE7',
  },
  badgeRed: {
    backgroundColor: '#FEE2E2',
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 4,
  },
  badgeTextGreen: {
    color: '#4CAF50',
  },
  badgeTextRed: {
    color: '#EF4444',
  },
  miniStats: {
    marginTop: 8,
  },
  miniStatsText: {
    fontSize: 11,
    color: '#94A3B8',
  },
  chartCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  chartTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 16,
  },
  chart: {
    borderRadius: 8,
    marginLeft: -16,
  },
  noDataContainer: {
    padding: 40,
    alignItems: 'center',
  },
  noDataText: {
    fontSize: 14,
    color: '#94A3B8',
  },
  listCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  listRank: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#F1F5F9',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#64748B',
  },
  listContent: {
    flex: 1,
  },
  listName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  listCompany: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 2,
  },
  listStats: {
    alignItems: 'flex-end',
  },
  listRevenue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#4CAF50',
  },
  listQuotes: {
    fontSize: 11,
    color: '#94A3B8',
    marginTop: 2,
  },
  rollerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  rollerIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rollerIconText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  rollerContent: {
    flex: 1,
  },
  rollerName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
    marginBottom: 6,
  },
  progressBar: {
    height: 6,
    backgroundColor: '#F1F5F9',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  rollerStats: {
    alignItems: 'flex-end',
    marginLeft: 12,
  },
  rollerCount: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
  },
  rollerValue: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 2,
  },
  recentItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  recentLeft: {
    flex: 1,
  },
  recentNumber: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
  },
  recentCustomer: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 2,
  },
  recentRight: {
    alignItems: 'flex-end',
  },
  recentPrice: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginTop: 4,
  },
  statusApproved: {
    backgroundColor: '#DCFCE7',
  },
  statusPending: {
    backgroundColor: '#FEF3C7',
  },
  statusText: {
    fontSize: 10,
    fontWeight: '600',
  },
  statusTextApproved: {
    color: '#4CAF50',
  },
  statusTextPending: {
    color: '#F59E0B',
  },
});
