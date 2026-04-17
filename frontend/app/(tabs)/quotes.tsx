import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
  Modal,
  ScrollView,
  Platform,
  TextInput,
  Pressable,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api, { cacheEvents } from '../../utils/api';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system/legacy';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Import extracted components and types
import {
  Quote,
  QuoteProduct,
  RevisionHistoryEntry,
  QuoteCard,
  RevisionHistoryModal,
  ApprovalSuccessModal,
  RejectReasonModal,
  QuoteDetailModal,
  EditQuoteModal,
  // Utilities
  getStatusColor,
  getStatusIcon,
  formatDate,
  // PDF Generator
  generatePdfHtml,
} from '../../components/quotes';
import { ExportButtons } from '../../components/shared/ExportButtons';

function OrdersAndWOView({ orders, ordersLoading, fetchOrders, workOrders, woLoading, fetchWorkOrders, isAdmin }: {
  orders: any[]; ordersLoading: boolean; fetchOrders: () => void;
  workOrders: any[]; woLoading: boolean; fetchWorkOrders: () => void;
  isAdmin: boolean;
}) {
  const [subTab, setSubTab] = useState<'so' | 'wo'>('so');

  return (
    <View style={{ flex: 1 }}>
      {/* Floating SO / WO toggle */}
      <View style={{ position: 'absolute', bottom: 20, left: 0, right: 0, zIndex: 100, alignItems: 'center' }}>
        <View style={{ flexDirection: 'row', backgroundColor: '#0F172A', borderRadius: 28, padding: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.25, shadowRadius: 16, elevation: 10 }}>
          <Pressable
            style={[{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 24 }, subTab === 'so' && { backgroundColor: '#C5964A' }]}
            onPress={() => { setSubTab('so'); if (orders.length === 0) fetchOrders(); }}
          >
            <Ionicons name="cube-outline" size={16} color={subTab === 'so' ? '#fff' : '#94A3B8'} />
            <Text style={{ fontSize: 13, fontWeight: '700', color: subTab === 'so' ? '#fff' : '#94A3B8' }}>Sales Orders</Text>
          </Pressable>
          <Pressable
            style={[{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 24 }, subTab === 'wo' && { backgroundColor: '#C5964A' }]}
            onPress={() => { setSubTab('wo'); if (workOrders.length === 0) fetchWorkOrders(); }}
          >
            <Ionicons name="construct-outline" size={16} color={subTab === 'wo' ? '#fff' : '#94A3B8'} />
            <Text style={{ fontSize: 13, fontWeight: '700', color: subTab === 'wo' ? '#fff' : '#94A3B8' }}>Work Orders</Text>
          </Pressable>
        </View>
      </View>

      {subTab === 'so' ? (
        <OrdersView orders={orders} loading={ordersLoading} onRefresh={fetchOrders} isAdmin={isAdmin} />
      ) : (
        <WorkOrdersView workOrders={workOrders} loading={woLoading} onRefresh={fetchWorkOrders} isAdmin={isAdmin} />
      )}
    </View>
  );
}

const WO_STAGE_COLORS: Record<string, string> = { created: '#3B82F6', material_issued: '#8B5CF6', in_progress: '#C5964A', qc: '#F59E0B', completed: '#10B981' };
const WO_STAGE_LABELS: Record<string, string> = { created: 'Created', material_issued: 'Material Issued', in_progress: 'In Progress', qc: 'QC', completed: 'Completed' };

function WorkOrdersView({ workOrders, loading, onRefresh, isAdmin }: { workOrders: any[]; loading: boolean; onRefresh: () => void; isAdmin: boolean }) {
  const [selectedWO, setSelectedWO] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const openWODetail = async (wo: any) => {
    setDetailLoading(true);
    try {
      const res = await api.get(`/work-orders/${wo.id}`);
      setSelectedWO(res.data);
    } catch { setSelectedWO(wo); }
    finally { setDetailLoading(false); }
  };

  const updateStage = async (woId: string, stage: string) => {
    try { await api.put(`/work-orders/${woId}/stage?stage=${stage}`); onRefresh(); }
    catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const downloadPDF = async (woId: string) => {
    try {
      const token = await AsyncStorage.getItem('token');
      const url = api.defaults.baseURL + `/work-orders/${woId}/pdf?token=${token}`;
      if (typeof window !== 'undefined') window.open(url, '_blank');
      else Alert.alert('PDF', 'Open in browser to download');
    } catch { Alert.alert('Error', 'Failed to download PDF'); }
  };

  if (loading) return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><ActivityIndicator size="large" color="#C5964A" /></View>;

  return (
    <View style={{ flex: 1 }}>
      <FlatList
        data={workOrders}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 14 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} colors={['#C5964A']} />}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', paddingVertical: 60 }}>
            <Ionicons name="construct-outline" size={48} color="#CBD5E1" />
            <Text style={{ color: '#94A3B8', fontSize: 15, marginTop: 12 }}>No work orders yet</Text>
            <Text style={{ color: '#CBD5E1', fontSize: 13, marginTop: 4 }}>Create from Sales Orders</Text>
          </View>
        }
        renderItem={({ item: wo }) => (
          <TouchableOpacity style={wos.card} onPress={() => openWODetail(wo)} activeOpacity={0.7}>
            <View style={wos.cardHeader}>
              <View style={{ flex: 1 }}>
                <Text style={wos.woNumber}>{wo.wo_number}</Text>
                <Text style={wos.customer}>{wo.customer_name} | SO: {wo.so_number}</Text>
              </View>
              <View style={[wos.stageBadge, { backgroundColor: (WO_STAGE_COLORS[wo.stage] || '#94A3B8') + '18' }]}>
                <Text style={[wos.stageText, { color: WO_STAGE_COLORS[wo.stage] || '#94A3B8' }]}>{WO_STAGE_LABELS[wo.stage] || wo.stage}</Text>
              </View>
            </View>
            <Text style={wos.itemCount}>{wo.items?.length || 0} item(s) | Created: {wo.created_at?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$3-$2-$1') || ''}</Text>
            {/* Items preview */}
            {(wo.items || []).slice(0, 3).map((item: any, i: number) => (
              <View key={i} style={wos.itemPreview}>
                <Text style={wos.itemName} numberOfLines={1}>{item.product_name}</Text>
                <Text style={wos.itemMeta}>Qty: {item.quantity} | Dwg: {item.drawing_number || 'N/A'} | BOM: {item.bom?.length || 0} parts</Text>
              </View>
            ))}
            {isAdmin && (
              <View style={wos.actions}>
                <TouchableOpacity style={wos.actionBtn} onPress={() => downloadPDF(wo.id)}>
                  <Ionicons name="download-outline" size={14} color="#C5964A" />
                  <Text style={[wos.actionText, { color: '#C5964A' }]}>PDF</Text>
                </TouchableOpacity>
                {wo.stage !== 'completed' && (() => {
                  const stages = ['created', 'completed'];
                  const next = stages[stages.indexOf(wo.stage) + 1];
                  return next ? (
                    <TouchableOpacity style={[wos.actionBtn, { borderColor: WO_STAGE_COLORS[next] }]} onPress={() => updateStage(wo.id, next)}>
                      <Ionicons name="arrow-forward" size={14} color={WO_STAGE_COLORS[next]} />
                      <Text style={[wos.actionText, { color: WO_STAGE_COLORS[next] }]}>{WO_STAGE_LABELS[next]}</Text>
                    </TouchableOpacity>
                  ) : null;
                })()}
              </View>
            )}
          </TouchableOpacity>
        )}
      />

      {/* WO Detail Modal */}
      <Modal visible={!!selectedWO} animationType="slide" transparent>
        <View style={wos.modalOverlay}>
          <View style={[wos.modal, { maxHeight: '92%' }]}>
            <View style={wos.modalHead}>
              <Text style={wos.modalTitle}>{selectedWO?.wo_number || 'Work Order'}</Text>
              <TouchableOpacity onPress={() => setSelectedWO(null)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
            </View>
            {detailLoading ? <ActivityIndicator size="large" color="#C5964A" style={{ paddingVertical: 40 }} /> :
            selectedWO ? (
              <ScrollView showsVerticalScrollIndicator={false}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                  <Text style={{ fontSize: 13, color: '#64748B' }}>SO: {selectedWO.so_number} | {selectedWO.customer_name}</Text>
                  <View style={[wos.stageBadge, { backgroundColor: (WO_STAGE_COLORS[selectedWO.stage] || '#94A3B8') + '18' }]}>
                    <Text style={[wos.stageText, { color: WO_STAGE_COLORS[selectedWO.stage] }]}>{WO_STAGE_LABELS[selectedWO.stage]}</Text>
                  </View>
                </View>

                {/* Items with BOM */}
                {(selectedWO.items || []).map((item: any, i: number) => (
                  <View key={i} style={{ backgroundColor: 'rgba(241,245,249,0.7)', borderRadius: 12, marginBottom: 14, overflow: 'hidden' }}>
                    <View style={{ backgroundColor: '#0F172A', padding: 10 }}>
                      <Text style={{ color: '#fff', fontSize: 13, fontWeight: '700' }}>{item.product_name} | Qty: {item.quantity}</Text>
                    </View>
                    <View style={{ padding: 12 }}>
                      {/* Production details */}
                      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 8 }}>
                        <View style={{ minWidth: 120 }}><Text style={{ fontSize: 9, color: '#C5964A', fontWeight: '700', textTransform: 'uppercase' }}>Drawing</Text><Text style={{ fontSize: 13, fontWeight: '600' }}>{item.drawing_number || 'N/A'}</Text></View>
                        <View style={{ minWidth: 120 }}><Text style={{ fontSize: 9, color: '#C5964A', fontWeight: '700', textTransform: 'uppercase' }}>Paint</Text><Text style={{ fontSize: 13 }}>{item.paint_details || 'N/A'}</Text></View>
                        <View style={{ minWidth: 100 }}><Text style={{ fontSize: 9, color: '#C5964A', fontWeight: '700', textTransform: 'uppercase' }}>Shaft Length</Text><Text style={{ fontSize: 13, fontWeight: '600' }}>{item.shaft_length_mm || 'N/A'} mm</Text></View>
                        <View style={{ minWidth: 120 }}><Text style={{ fontSize: 9, color: '#C5964A', fontWeight: '700', textTransform: 'uppercase' }}>Shaft Slot</Text><Text style={{ fontSize: 13, fontWeight: '700', color: '#960018' }}>{item.shaft_slot || 'N/A'}</Text></View>
                      </View>
                      {item.production_notes && <Text style={{ fontSize: 12, color: '#475569', backgroundColor: '#F8FAFC', padding: 8, borderRadius: 6, marginBottom: 8 }}>{item.production_notes}</Text>}

                      {/* BOM Table */}
                      {item.bom && item.bom.length > 0 && (
                        <View>
                          <Text style={{ fontSize: 10, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Bill of Materials</Text>
                          <View style={{ borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 8, overflow: 'hidden' }}>
                            <View style={{ flexDirection: 'row', backgroundColor: '#1E293B', padding: 6 }}>
                              <Text style={{ flex: 2, color: '#fff', fontSize: 10, fontWeight: '600' }}>Component</Text>
                              <Text style={{ flex: 3, color: '#fff', fontSize: 10, fontWeight: '600' }}>Description</Text>
                              <Text style={{ flex: 1, color: '#fff', fontSize: 10, fontWeight: '600', textAlign: 'center' }}>Qty</Text>
                              <Text style={{ flex: 1, color: '#fff', fontSize: 10, fontWeight: '600', textAlign: 'right' }}>Wt(kg)</Text>
                            </View>
                            {item.bom.map((b: any, bi: number) => (
                              <View key={bi} style={{ flexDirection: 'row', padding: 6, borderBottomWidth: 1, borderBottomColor: '#F1F5F9', backgroundColor: bi % 2 === 0 ? '#fff' : '#F8FAFC' }}>
                                <Text style={{ flex: 2, fontSize: 11, fontWeight: '600', color: '#0F172A' }}>{b.component}</Text>
                                <Text style={{ flex: 3, fontSize: 10, color: '#64748B' }}>{b.description}</Text>
                                <Text style={{ flex: 1, fontSize: 11, textAlign: 'center', fontWeight: '600' }}>{b.total_qty}</Text>
                                <Text style={{ flex: 1, fontSize: 11, textAlign: 'right' }}>{b.total_weight_kg || '-'}</Text>
                              </View>
                            ))}
                          </View>
                        </View>
                      )}
                    </View>
                  </View>
                ))}

                {/* Stage History */}
                {selectedWO.stage_history && selectedWO.stage_history.length > 0 && (
                  <View style={{ marginTop: 8 }}>
                    <Text style={{ fontSize: 10, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Stage History</Text>
                    {selectedWO.stage_history.map((sh: any, i: number) => (
                      <View key={i} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8, paddingVertical: 4 }}>
                        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: WO_STAGE_COLORS[sh.stage] || '#94A3B8', marginTop: 4 }} />
                        <View><Text style={{ fontSize: 12, fontWeight: '600' }}>{WO_STAGE_LABELS[sh.stage] || sh.stage}</Text><Text style={{ fontSize: 10, color: '#94A3B8' }}>{sh.timestamp?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$3-$2-$1') || ''} {sh.notes ? `— ${sh.notes}` : ''}</Text></View>
                      </View>
                    ))}
                  </View>
                )}

                {/* Actions */}
                {isAdmin && (
                  <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#C5964A', borderRadius: 12, paddingVertical: 14, marginTop: 16 }} onPress={() => { downloadPDF(selectedWO.id); }}>
                    <Ionicons name="download" size={18} color="#fff" />
                    <Text style={{ color: '#fff', fontSize: 15, fontWeight: '700' }}>Download Work Order PDF</Text>
                  </TouchableOpacity>
                )}
                <View style={{ height: 20 }} />
              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const wos = StyleSheet.create({
  card: { backgroundColor: 'rgba(255,255,255,0.82)', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.35)', shadowColor: '#0F172A', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.04, shadowRadius: 12, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 },
  woNumber: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
  customer: { fontSize: 12, color: '#64748B', marginTop: 2 },
  stageBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  stageText: { fontSize: 11, fontWeight: '700' },
  itemCount: { fontSize: 11, color: '#94A3B8', marginBottom: 8 },
  itemPreview: { backgroundColor: 'rgba(241,245,249,0.6)', borderRadius: 8, padding: 8, marginBottom: 4 },
  itemName: { fontSize: 12, fontWeight: '600', color: '#0F172A' },
  itemMeta: { fontSize: 10, color: '#64748B', marginTop: 2 },
  actions: { flexDirection: 'row', gap: 8, marginTop: 8 },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#E2E8F0' },
  actionText: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 22 },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
});

const ORDER_STAGE_COLORS: Record<string, string> = {
  confirmed: '#3B82F6', in_production: '#C5964A', ready: '#8B5CF6', dispatched: '#F59E0B', delivered: '#10B981'
};
const ORDER_STAGE_LABELS: Record<string, string> = {
  confirmed: 'Confirmed', in_production: 'Production', ready: 'Ready', dispatched: 'Dispatched', delivered: 'Delivered'
};
const PAYMENT_COLORS: Record<string, string> = { unpaid: '#EF4444', partial: '#F59E0B', paid: '#10B981' };

function OrdersView({ orders, loading, onRefresh, isAdmin }: { orders: any[]; loading: boolean; onRefresh: () => void; isAdmin: boolean }) {
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [showPayment, setShowPayment] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [detailOrder, setDetailOrder] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCreateWO, setShowCreateWO] = useState(false);
  const [woOrder, setWoOrder] = useState<any>(null);
  const [woItems, setWoItems] = useState<any[]>([]);
  const [woCreating, setWoCreating] = useState(false);
  const [woRalCode, setWoRalCode] = useState('');
  const [woPaintType, setWoPaintType] = useState('');
  const [woPaintSpec, setWoPaintSpec] = useState('');
  const [payAmount, setPayAmount] = useState('');
  const [payMode, setPayMode] = useState('bank_transfer');
  const [payRef, setPayRef] = useState('');
  const [processing, setProcessing] = useState(false);

  const openCreateWO = (order: any) => {
    setWoOrder(order);
    const items = (order.products || []).map((_: any, i: number) => ({
      item_index: i,
      drawing_number: '',
      shaft_length: '',
      slot_width: '',
      slot_dimension: '',
      slot_type: 'A',
      production_notes: '',
    }));
    setWoItems(items);
    setWoRalCode('');
    setWoPaintType('');
    setWoPaintSpec(order.commercial_terms?.color_finish || '');
    setShowCreateWO(true);
  };

  const createWorkOrder = async () => {
    if (!woOrder) return;
    // Validate
    for (let i = 0; i < woItems.length; i++) {
      const item = woItems[i];
      if (!item.drawing_number) { Alert.alert('Error', `Item ${i+1}: Drawing number required`); return; }
      if (!item.shaft_length) { Alert.alert('Error', `Item ${i+1}: Shaft length required`); return; }
      if (!item.slot_width || !item.slot_dimension || !item.slot_type) { Alert.alert('Error', `Item ${i+1}: Shaft slot details required`); return; }
    }
    setWoCreating(true);
    try {
      const payload = {
        items: woItems.map(item => ({
          item_index: item.item_index,
          drawing_number: item.drawing_number,
          shaft_length: parseFloat(item.shaft_length),
          shaft_slot: { width: parseFloat(item.slot_width), dimension: parseFloat(item.slot_dimension), slot_type: item.slot_type },
          production_notes: item.production_notes,
        })),
        ral_code: woRalCode,
        paint_type: woPaintType,
        paint_spec: woPaintSpec,
      };
      const res = await api.post(`/orders/${woOrder.id}/create-work-order`, payload);
      Alert.alert('Success', res.data.message);
      setShowCreateWO(false);
      onRefresh();
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to create work order');
    } finally { setWoCreating(false); }
  };

  const openOrderDetail = async (order: any) => {
    setDetailLoading(true);
    setShowDetail(true);
    try {
      const res = await api.get(`/orders/${order.id}`);
      setDetailOrder(res.data);
    } catch {
      setDetailOrder(order);
    } finally {
      setDetailLoading(false);
    }
  };

  const addPayment = async () => {
    if (!selectedOrder || !payAmount) return;
    setProcessing(true);
    try {
      await api.post(`/orders/${selectedOrder.id}/payments`, { amount: parseFloat(payAmount), mode: payMode, reference: payRef });
      Alert.alert('Success', `Payment of Rs.${payAmount} recorded`);
      setShowPayment(false); setPayAmount(''); setPayRef('');
      onRefresh();
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
    finally { setProcessing(false); }
  };

  const updateStage = async (orderId: string, stage: string) => {
    try {
      await api.put(`/orders/${orderId}/stage`, { stage });
      onRefresh();
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const generateInvoice = async (orderId: string, type: 'proforma' | 'tax-invoice') => {
    try {
      const res = await api.post(`/orders/${orderId}/${type}`);
      Alert.alert('Success', res.data.message);
      onRefresh();
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  if (loading) return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}><ActivityIndicator size="large" color="#C5964A" /></View>;

  return (
    <View style={{ flex: 1 }}>
      {/* Export Buttons for Orders */}
      {isAdmin && (
        <View style={{ flexDirection: 'row', justifyContent: 'flex-end', paddingHorizontal: 14, paddingTop: 10 }}>
          <ExportButtons
            endpoint="/orders/export/excel"
            pdfEndpoint="/orders/export/pdf"
            filenamePrefix="Orders"
            compact={true}
            showPdf={true}
            showExcel={true}
          />
        </View>
      )}
      <FlatList
        data={orders}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 14 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} colors={['#C5964A']} />}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', paddingVertical: 60 }}>
            <Ionicons name="cube-outline" size={48} color="#CBD5E1" />
            <Text style={{ color: '#94A3B8', fontSize: 15, marginTop: 12 }}>No orders yet</Text>
            <Text style={{ color: '#CBD5E1', fontSize: 13, marginTop: 4 }}>Convert approved quotes to orders</Text>
          </View>
        }
        renderItem={({ item: order }) => (
          <TouchableOpacity style={os.card} onPress={() => openOrderDetail(order)} activeOpacity={0.7}>
            <View style={os.cardHeader}>
              <View style={{ flex: 1 }}>
                <Text style={os.soNumber}>{order.so_number}</Text>
                <Text style={os.customer}>{order.customer_name}{order.customer_company ? ` - ${order.customer_company}` : ''}</Text>
              </View>
              <View style={[os.stageBadge, { backgroundColor: (ORDER_STAGE_COLORS[order.stage] || '#94A3B8') + '18' }]}>
                <Text style={[os.stageText, { color: ORDER_STAGE_COLORS[order.stage] || '#94A3B8' }]}>{ORDER_STAGE_LABELS[order.stage] || order.stage}</Text>
              </View>
            </View>

            <View style={os.metaRow}>
              <View style={os.metaItem}>
                <Text style={os.metaLabel}>Total</Text>
                <Text style={os.metaValue}>Rs.{order.total_price?.toLocaleString()}</Text>
              </View>
              <View style={os.metaItem}>
                <Text style={os.metaLabel}>Paid</Text>
                <Text style={[os.metaValue, { color: PAYMENT_COLORS[order.payment_status] }]}>Rs.{order.total_paid?.toLocaleString()}</Text>
              </View>
              <View style={os.metaItem}>
                <Text style={os.metaLabel}>Due</Text>
                <Text style={[os.metaValue, { color: order.balance_due > 0 ? '#EF4444' : '#10B981' }]}>Rs.{order.balance_due?.toLocaleString()}</Text>
              </View>
            </View>

            {/* Payment status bar */}
            <View style={os.payBar}>
              <View style={[os.payBarFill, { width: `${Math.min((order.total_paid / order.total_price) * 100, 100)}%`, backgroundColor: PAYMENT_COLORS[order.payment_status] }]} />
            </View>

            {/* Invoices */}
            <View style={os.invoiceRow}>
              {order.proforma_invoice && <View style={os.invoiceTag}><Ionicons name="document-outline" size={12} color="#8B5CF6" /><Text style={os.invoiceTagText}>PI: {order.proforma_invoice}</Text></View>}
              {order.quote_number && <View style={os.invoiceTag}><Ionicons name="document-text-outline" size={12} color="#94A3B8" /><Text style={os.invoiceTagText}>{order.quote_number}</Text></View>}
              {order.work_order && <View style={os.invoiceTag}><Ionicons name="construct" size={12} color="#10B981" /><Text style={os.invoiceTagText}>{order.work_order}</Text></View>}
            </View>

            {/* Actions */}
            {isAdmin && (
              <View style={os.actions}>
                <TouchableOpacity style={os.actionBtn} onPress={() => { setSelectedOrder(order); setShowPayment(true); }}>
                  <Ionicons name="cash-outline" size={15} color="#C5964A" />
                  <Text style={os.actionText}>Payment</Text>
                </TouchableOpacity>
                <Pressable style={[os.actionBtn, { backgroundColor: 'rgba(15,23,42,0.06)', borderColor: '#0F172A' }]} onPress={async () => {
                  try {
                    const token = await AsyncStorage.getItem('token');
                    if (token) {
                      const url = api.defaults.baseURL + `/orders/${order.id}/pdf?token=${token}`;
                      if (typeof window !== 'undefined') window.open(url, '_blank');
                      else Alert.alert('SO PDF', order.so_number);
                    }
                  } catch { Alert.alert('Error', 'Could not download SO'); }
                }}>
                  <Ionicons name="download-outline" size={15} color="#0F172A" />
                  <Text style={[os.actionText, { color: '#0F172A' }]}>SO PDF</Text>
                </Pressable>
                {order.proforma_invoice && (
                  <TouchableOpacity style={[os.actionBtn, { backgroundColor: 'rgba(139,92,246,0.1)', borderColor: '#8B5CF6' }]} onPress={async () => {
                    try {
                      const token = await AsyncStorage.getItem('token');
                      const res = await api.get('/invoices');
                      const inv = res.data.invoices?.find((i: any) => i.so_number === order.so_number && i.invoice_type === 'proforma');
                      if (inv && token) {
                        const url = api.defaults.baseURL + `/invoices/${inv.id}/pdf?token=${token}`;
                        if (typeof window !== 'undefined') window.open(url, '_blank');
                        else Alert.alert('Proforma', inv.invoice_number);
                      } else Alert.alert('Error', 'Invoice or token not found');
                    } catch { Alert.alert('Error', 'Could not load proforma'); }
                  }}>
                    <Ionicons name="download-outline" size={15} color="#8B5CF6" />
                    <Text style={[os.actionText, { color: '#8B5CF6' }]}>PI PDF</Text>
                  </TouchableOpacity>
                )}
                {!order.work_order && (
                  <Pressable style={[os.actionBtn, { backgroundColor: 'rgba(197,150,74,0.1)', borderColor: '#C5964A' }]} onPress={() => openCreateWO(order)}>
                    <Ionicons name="construct-outline" size={15} color="#C5964A" />
                    <Text style={[os.actionText, { color: '#C5964A' }]}>Create WO</Text>
                  </Pressable>
                )}
                {order.work_order && (
                  <View style={[os.actionBtn, { backgroundColor: 'rgba(16,185,129,0.08)', borderColor: '#10B981' }]}>
                    <Ionicons name="construct" size={15} color="#10B981" />
                    <Text style={[os.actionText, { color: '#10B981' }]}>{order.work_order}</Text>
                  </View>
                )}
              </View>
            )}
          </TouchableOpacity>
        )}
      />

      {/* Order Detail Modal */}
      <Modal visible={showDetail} animationType="slide" transparent>
        <View style={os.modalOverlay}>
          <View style={[os.modal, { maxHeight: '90%' }]}>
            <View style={os.modalHead}>
              <Text style={os.modalTitle}>{detailOrder?.so_number || 'Order Detail'}</Text>
              <TouchableOpacity onPress={() => { setShowDetail(false); setDetailOrder(null); }}>
                <Ionicons name="close" size={24} color="#64748B" />
              </TouchableOpacity>
            </View>
            {detailLoading ? (
              <ActivityIndicator size="large" color="#C5964A" style={{ paddingVertical: 40 }} />
            ) : detailOrder ? (
              <ScrollView style={{ maxHeight: 600 }} showsVerticalScrollIndicator={false}>
                {/* Order Header */}
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 14 }}>
                  <View>
                    <Text style={{ fontSize: 13, color: '#64748B' }}>{detailOrder.customer_name}{detailOrder.customer_company ? ` - ${detailOrder.customer_company}` : ''}</Text>
                    {detailOrder.quote_number && <Text style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>Quote: {detailOrder.quote_number}</Text>}
                  </View>
                  <View style={[os.stageBadge, { backgroundColor: (ORDER_STAGE_COLORS[detailOrder.stage] || '#94A3B8') + '18' }]}>
                    <Text style={[os.stageText, { color: ORDER_STAGE_COLORS[detailOrder.stage] || '#94A3B8' }]}>{ORDER_STAGE_LABELS[detailOrder.stage] || detailOrder.stage}</Text>
                  </View>
                </View>

                {/* Products / Items */}
                <Text style={os.label}>Items</Text>
                {(detailOrder.products || []).map((p: any, i: number) => (
                  <View key={i} style={{ backgroundColor: 'rgba(241,245,249,0.7)', borderRadius: 10, padding: 12, marginBottom: 8 }}>
                    <Text style={{ fontSize: 14, fontWeight: '700', color: '#0F172A' }}>{p.product_name || p.product_id}</Text>
                    <View style={{ flexDirection: 'row', gap: 16, marginTop: 6 }}>
                      <View>
                        <Text style={{ fontSize: 10, color: '#94A3B8' }}>Qty</Text>
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '#0F172A' }}>{p.quantity}</Text>
                      </View>
                      <View>
                        <Text style={{ fontSize: 10, color: '#94A3B8' }}>Unit Price</Text>
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '#0F172A' }}>Rs.{p.unit_price?.toLocaleString()}</Text>
                      </View>
                      <View>
                        <Text style={{ fontSize: 10, color: '#94A3B8' }}>Total</Text>
                        <Text style={{ fontSize: 14, fontWeight: '700', color: '#960018' }}>Rs.{(p.quantity * p.unit_price)?.toLocaleString()}</Text>
                      </View>
                    </View>
                    {p.specifications && (
                      <View style={{ flexDirection: 'row', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
                        {p.specifications.pipe_diameter && <Text style={{ fontSize: 11, color: '#64748B' }}>Pipe: {p.specifications.pipe_diameter}mm</Text>}
                        {p.specifications.shaft_diameter && <Text style={{ fontSize: 11, color: '#64748B' }}>Shaft: {p.specifications.shaft_diameter}mm</Text>}
                        {p.specifications.pipe_type && <Text style={{ fontSize: 11, color: '#64748B' }}>{p.specifications.pipe_type}</Text>}
                      </View>
                    )}
                    {p.weight_kg && <Text style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>Weight: {p.weight_kg} kg</Text>}
                    {p.remark && <Text style={{ fontSize: 11, color: '#C5964A', marginTop: 4 }}>Remark: {p.remark}</Text>}
                  </View>
                ))}

                {/* Payment Summary */}
                <Text style={[os.label, { marginTop: 16 }]}>Payment</Text>
                <View style={{ backgroundColor: 'rgba(241,245,249,0.7)', borderRadius: 10, padding: 12, marginBottom: 8 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                    <Text style={{ fontSize: 13, color: '#64748B' }}>Total</Text>
                    <Text style={{ fontSize: 15, fontWeight: '700', color: '#0F172A' }}>Rs.{detailOrder.total_price?.toLocaleString()}</Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                    <Text style={{ fontSize: 13, color: '#64748B' }}>Paid</Text>
                    <Text style={{ fontSize: 15, fontWeight: '700', color: '#10B981' }}>Rs.{detailOrder.total_paid?.toLocaleString()}</Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    <Text style={{ fontSize: 13, fontWeight: '600', color: '#0F172A' }}>Balance Due</Text>
                    <Text style={{ fontSize: 15, fontWeight: '800', color: detailOrder.balance_due > 0 ? '#EF4444' : '#10B981' }}>Rs.{detailOrder.balance_due?.toLocaleString()}</Text>
                  </View>
                </View>

                {/* Payment History */}
                {detailOrder.payments && detailOrder.payments.length > 0 && (
                  <>
                    <Text style={[os.label, { marginTop: 12 }]}>Payment History</Text>
                    {detailOrder.payments.map((pay: any, i: number) => (
                      <View key={i} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: 'rgba(226,232,240,0.4)' }}>
                        <View>
                          <Text style={{ fontSize: 13, fontWeight: '600', color: '#0F172A' }}>Rs.{pay.amount?.toLocaleString()}</Text>
                          <Text style={{ fontSize: 11, color: '#94A3B8' }}>{pay.mode?.replace('_', ' ')} {pay.reference ? `| ${pay.reference}` : ''}</Text>
                        </View>
                        <Text style={{ fontSize: 11, color: '#94A3B8' }}>{pay.recorded_at?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$3-$2-$1') || ''}</Text>
                      </View>
                    ))}
                  </>
                )}

                {/* Invoices */}
                {(detailOrder.proforma_invoice || detailOrder.tax_invoice) && (
                  <>
                    <Text style={[os.label, { marginTop: 16 }]}>Invoices</Text>
                    <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
                      {detailOrder.proforma_invoice && (
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: 'rgba(139,92,246,0.08)', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 }}>
                          <Ionicons name="document-outline" size={14} color="#8B5CF6" />
                          <Text style={{ fontSize: 12, fontWeight: '600', color: '#8B5CF6' }}>{detailOrder.proforma_invoice}</Text>
                        </View>
                      )}
                      {detailOrder.tax_invoice && (
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: 'rgba(16,185,129,0.08)', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 }}>
                          <Ionicons name="receipt-outline" size={14} color="#10B981" />
                          <Text style={{ fontSize: 12, fontWeight: '600', color: '#10B981' }}>{detailOrder.tax_invoice}</Text>
                        </View>
                      )}
                    </View>
                  </>
                )}

                {/* Stage History */}
                {detailOrder.stage_history && detailOrder.stage_history.length > 0 && (
                  <>
                    <Text style={[os.label, { marginTop: 16 }]}>Stage History</Text>
                    {detailOrder.stage_history.map((sh: any, i: number) => (
                      <View key={i} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10, paddingVertical: 6 }}>
                        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: ORDER_STAGE_COLORS[sh.stage] || '#94A3B8', marginTop: 4 }} />
                        <View style={{ flex: 1 }}>
                          <Text style={{ fontSize: 13, fontWeight: '600', color: '#0F172A' }}>{ORDER_STAGE_LABELS[sh.stage] || sh.stage}</Text>
                          <Text style={{ fontSize: 11, color: '#94A3B8' }}>{sh.timestamp?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$3-$2-$1') || ''} {sh.by ? `by ${sh.by}` : ''}</Text>
                          {sh.notes && <Text style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{sh.notes}</Text>}
                        </View>
                      </View>
                    ))}
                  </>
                )}

                {/* Commercial Terms */}
                {detailOrder.commercial_terms && (
                  <>
                    <Text style={[os.label, { marginTop: 16 }]}>Commercial Terms</Text>
                    <View style={{ backgroundColor: 'rgba(241,245,249,0.7)', borderRadius: 10, padding: 12 }}>
                      {Object.entries(detailOrder.commercial_terms).map(([key, value]: [string, any]) => (
                        <View key={key} style={{ marginBottom: 4 }}>
                          <Text style={{ fontSize: 10, color: '#94A3B8', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</Text>
                          <Text style={{ fontSize: 12, color: '#0F172A' }}>{value}</Text>
                        </View>
                      ))}
                    </View>
                  </>
                )}

                {/* Actions */}
                {isAdmin && (
                  <View style={{ flexDirection: 'row', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
                    <TouchableOpacity style={[os.actionBtn, { flex: 1 }]} onPress={() => { setSelectedOrder(detailOrder); setShowDetail(false); setShowPayment(true); }}>
                      <Ionicons name="cash-outline" size={15} color="#C5964A" />
                      <Text style={os.actionText}>Record Payment</Text>
                    </TouchableOpacity>
                  </View>
                )}

                <View style={{ height: 20 }} />
              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>

      {/* Payment Modal */}
      <Modal visible={showPayment} animationType="slide" transparent>
        <View style={os.modalOverlay}>
          <View style={os.modal}>
            <View style={os.modalHead}><Text style={os.modalTitle}>Record Payment</Text><TouchableOpacity onPress={() => setShowPayment(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
            {selectedOrder && <Text style={os.modalSub}>{selectedOrder.so_number} — Balance: Rs.{selectedOrder.balance_due?.toLocaleString()}</Text>}
            <Text style={os.label}>Amount (Rs.)</Text>
            <TextInput style={os.input} value={payAmount} onChangeText={setPayAmount} keyboardType="numeric" placeholder="Enter amount" />
            <Text style={os.label}>Mode</Text>
            <View style={os.chipRow}>
              {['bank_transfer', 'cheque', 'upi', 'cash'].map(m => (
                <TouchableOpacity key={m} style={[os.chip, payMode === m && os.chipActive]} onPress={() => setPayMode(m)}>
                  <Text style={[os.chipText, payMode === m && os.chipTextActive]}>{m.replace('_', ' ')}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={os.label}>Reference (UTR/Cheque No.)</Text>
            <TextInput style={os.input} value={payRef} onChangeText={setPayRef} placeholder="Optional" />
            <TouchableOpacity style={os.saveBtn} onPress={addPayment} disabled={processing}>
              {processing ? <ActivityIndicator color="#fff" /> : <><Ionicons name="checkmark" size={20} color="#fff" /><Text style={os.saveBtnText}>Record Payment</Text></>}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Create Work Order Modal */}
      <Modal visible={showCreateWO} animationType="slide" transparent>
        <View style={os.modalOverlay}>
          <View style={[os.modal, { maxHeight: '90%' }]}>
            <View style={os.modalHead}>
              <Text style={os.modalTitle}>Create Work Order</Text>
              <TouchableOpacity onPress={() => setShowCreateWO(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
            </View>
            {woOrder && <Text style={os.modalSub}>{woOrder.so_number} — {woOrder.customer_name}</Text>}
            <ScrollView style={{ maxHeight: 500 }} showsVerticalScrollIndicator={false}>
              {/* Paint Details — Common for all items */}
              <View style={{ backgroundColor: 'rgba(197,150,74,0.08)', borderRadius: 12, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: 'rgba(197,150,74,0.2)' }}>
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#C5964A', marginBottom: 10 }}>PAINT DETAILS (All Items)</Text>
                <Text style={os.label}>RAL Code</Text>
                <TextInput style={os.input} value={woRalCode} onChangeText={setWoRalCode} placeholder="RAL 9005" />
                <Text style={os.label}>Paint Type</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                  {['Synthetic Enamel', 'Auto Paint', 'Epoxy', 'PU'].map(pt => (
                    <Pressable key={pt} style={[os.chip, woPaintType === pt && os.chipActive]} onPress={() => setWoPaintType(pt)}>
                      <Text style={[os.chipText, woPaintType === pt && os.chipTextActive]}>{pt}</Text>
                    </Pressable>
                  ))}
                </View>
                <Text style={os.label}>Paint Specification (from Quote)</Text>
                <TextInput style={[os.input, { height: 50, textAlignVertical: 'top' }]} value={woPaintSpec} onChangeText={setWoPaintSpec} placeholder="1+1 Red oxide + finish" multiline />
              </View>

              {/* Per Item Details */}
              {woItems.map((item: any, idx: number) => (
                <View key={idx} style={{ backgroundColor: 'rgba(241,245,249,0.7)', borderRadius: 12, padding: 14, marginBottom: 12 }}>
                  <Text style={{ fontSize: 13, fontWeight: '700', color: '#0F172A', marginBottom: 10 }}>
                    Item {idx + 1}: {woOrder?.products?.[idx]?.product_name || 'Product'}
                  </Text>
                  <Text style={os.label}>Drawing Number *</Text>
                  <TextInput style={os.input} value={item.drawing_number} onChangeText={v => { const arr = [...woItems]; arr[idx].drawing_number = v; setWoItems(arr); }} placeholder="DWG-001" />
                  <Text style={os.label}>Shaft Length (mm) *</Text>
                  <TextInput style={os.input} value={item.shaft_length} onChangeText={v => { const arr = [...woItems]; arr[idx].shaft_length = v; setWoItems(arr); }} placeholder="600" keyboardType="numeric" />
                  <Text style={os.label}>Shaft End Slot *</Text>
                  <View style={{ flexDirection: 'row', gap: 8 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#94A3B8' }}>Width</Text>
                      <TextInput style={os.input} value={item.slot_width} onChangeText={v => { const arr = [...woItems]; arr[idx].slot_width = v; setWoItems(arr); }} placeholder="14" keyboardType="numeric" />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#94A3B8' }}>Dim</Text>
                      <TextInput style={os.input} value={item.slot_dimension} onChangeText={v => { const arr = [...woItems]; arr[idx].slot_dimension = v; setWoItems(arr); }} placeholder="9" keyboardType="numeric" />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#94A3B8' }}>Type</Text>
                      <TextInput style={os.input} value={item.slot_type} onChangeText={v => { const arr = [...woItems]; arr[idx].slot_type = v; setWoItems(arr); }} placeholder="A / B5 / C35" />
                    </View>
                  </View>
                  <Text style={os.label}>Production Notes</Text>
                  <TextInput style={[os.input, { height: 50, textAlignVertical: 'top' }]} value={item.production_notes} onChangeText={v => { const arr = [...woItems]; arr[idx].production_notes = v; setWoItems(arr); }} placeholder="Notes..." multiline />
                </View>
              ))}
            </ScrollView>
            <Pressable style={[os.saveBtn, woCreating && { opacity: 0.6 }]} onPress={createWorkOrder} disabled={woCreating}>
              {woCreating ? <ActivityIndicator color="#fff" /> : <><Ionicons name="construct" size={18} color="#fff" /><Text style={os.saveBtnText}>Create Work Order + BOM</Text></>}
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const os = StyleSheet.create({
  card: { backgroundColor: 'rgba(255,255,255,0.82)', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.35)', shadowColor: '#0F172A', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.04, shadowRadius: 12, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  soNumber: { fontSize: 16, fontWeight: '700', color: '#0F172A', letterSpacing: -0.2 },
  customer: { fontSize: 13, color: '#64748B', marginTop: 2 },
  stageBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  stageText: { fontSize: 11, fontWeight: '700' },
  metaRow: { flexDirection: 'row', gap: 16, marginBottom: 10 },
  metaItem: {},
  metaLabel: { fontSize: 11, color: '#94A3B8', fontWeight: '500' },
  metaValue: { fontSize: 15, fontWeight: '700', color: '#0F172A', marginTop: 2 },
  payBar: { height: 4, backgroundColor: '#F1F5F9', borderRadius: 2, marginBottom: 10, overflow: 'hidden' },
  payBarFill: { height: '100%', borderRadius: 2 },
  invoiceRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 10 },
  invoiceTag: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: 'rgba(241,245,249,0.7)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  invoiceTagText: { fontSize: 11, color: '#64748B', fontWeight: '500' },
  actions: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: 'rgba(241,245,249,0.5)' },
  actionText: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 22 },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  modalSub: { fontSize: 14, color: '#C5964A', fontWeight: '600', marginBottom: 16 },
  label: { fontSize: 12, fontWeight: '600', color: '#C5964A', letterSpacing: 0.5, marginBottom: 6, marginTop: 14 },
  input: { backgroundColor: 'rgba(241,245,249,0.8)', borderWidth: 1, borderColor: 'rgba(226,232,240,0.5)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#0F172A' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 8, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#F8FAFC' },
  chipActive: { backgroundColor: '#960018', borderColor: '#960018' },
  chipText: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  chipTextActive: { color: '#fff' },
  saveBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#960018', borderRadius: 14, paddingVertical: 15, marginTop: 18 },
  saveBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },
});

export default function QuotesScreen() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [viewMode, setViewMode] = useState<'quotes' | 'orders' | 'workorders'>('quotes');
  const [orders, setOrders] = useState<any[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [workOrders, setWorkOrders] = useState<any[]>([]);
  const [woLoading, setWoLoading] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [editingQuote, setEditingQuote] = useState<Quote | null>(null);
  const [editedProducts, setEditedProducts] = useState<QuoteProduct[]>([]);
  const [editedDiscount, setEditedDiscount] = useState<string>('0');
  const [editedFreight, setEditedFreight] = useState<string>('0');  // Editable freight for Edit Quote modal
  const [editedPackingType, setEditedPackingType] = useState<string>('standard');  // Editable packing type
  const [useItemDiscounts, setUseItemDiscounts] = useState(false);
  const [bulkDiscountPercent, setBulkDiscountPercent] = useState<string>('0');
  const [savingEdit, setSavingEdit] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approveModalQuote, setApproveModalQuote] = useState<Quote | null>(null);
  const [freightPercent, setFreightPercent] = useState<string>('0');
  const [customFreightAmount, setCustomFreightAmount] = useState<string>('');
  const [useCustomFreight, setUseCustomFreight] = useState(false);
  const [calculatedFreightFromPincode, setCalculatedFreightFromPincode] = useState<number>(0);
  const [freightLoading, setFreightLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'approved' | 'rejected' | 'active' | 'history'>('all');
  const [showConvertSO, setShowConvertSO] = useState(false);
  const [convertQuote, setConvertQuote] = useState<any>(null);
  const [deliveryDate, setDeliveryDate] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Approval success popup state
  const [showApprovalSuccess, setShowApprovalSuccess] = useState(false);
  const [approvedQuoteNumber, setApprovedQuoteNumber] = useState('');
  
  // Rejection modal state
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectingQuote, setRejectingQuote] = useState<Quote | null>(null);
  const [selectedRejectReason, setSelectedRejectReason] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  
  // Revision history state
  const [showRevisionHistory, setShowRevisionHistory] = useState(false);
  const [revisionHistory, setRevisionHistory] = useState<RevisionHistoryEntry[]>([]);
  
  // Commercial terms state
  const [commercialTermsOptions, setCommercialTermsOptions] = useState<any>(null);
  const [selectedPaymentTerms, setSelectedPaymentTerms] = useState<string>('100% Advance against pro-forma');
  const [selectedFreightTerms, setSelectedFreightTerms] = useState<string>('Ex-Works');
  const [selectedColorFinish, setSelectedColorFinish] = useState<string>('1+1 : Red oxide + finish paint black color approx 50-60 micron');
  const [selectedDeliveryTimeline, setSelectedDeliveryTimeline] = useState<string>('25-30 working days');
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // Edit RFQ modal state for viewing items
  const [editPackingType, setEditPackingType] = useState<string>('standard');
  const [editDeliveryPincode, setEditDeliveryPincode] = useState<string>('');
  const [customPackingPercent, setCustomPackingPercent] = useState<string>('');
  const [editableProducts, setEditableProducts] = useState<QuoteProduct[]>([]);
  const [pincodeError, setPincodeError] = useState<string>('');
  const [pincodeValid, setPincodeValid] = useState<boolean>(true);
  
  // Discount editing state
  const [useItemDiscount, setUseItemDiscount] = useState<boolean>(false);
  const [totalDiscountPercent, setTotalDiscountPercent] = useState<string>('0');
  const [itemDiscounts, setItemDiscounts] = useState<{[key: number]: string}>({});
  
  // Calculate approval modal totals in real-time
  const calculateApprovalTotal = () => {
    const quote = approveModalQuote || selectedQuote;
    if (!quote) return { subtotal: 0, discountAmount: 0, afterDiscount: 0, packingCharges: 0, freightAmount: 0, taxableAmount: 0, total: 0 };
    
    // Use editableProducts if available, otherwise fall back to quote's original products
    const productsToUse = editableProducts.length > 0 ? editableProducts : (quote.products || []);
    
    // Calculate subtotal (original, before discount)
    const subtotal = productsToUse.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
    
    // Calculate discount
    let discountAmount = 0;
    if (useItemDiscount) {
      // Item-wise discount
      productsToUse.forEach((product, index) => {
        const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
        const itemSubtotal = product.unit_price * product.quantity;
        discountAmount += itemSubtotal * (itemDiscountPct / 100);
      });
    } else {
      // Total discount mode
      const discountPct = parseFloat(totalDiscountPercent) || 0;
      discountAmount = subtotal * (discountPct / 100);
    }
    
    const afterDiscount = subtotal - discountAmount;
    
    // Calculate packing charges based on DISCOUNTED subtotal
    let packingPercent = 0;
    if (editPackingType === 'standard') packingPercent = 1;
    else if (editPackingType === 'pallet') packingPercent = 4;
    else if (editPackingType === 'wooden_box') packingPercent = 8;
    else if (editPackingType === 'custom') packingPercent = parseFloat(customPackingPercent) || 0;
    
    const packingCharges = afterDiscount * (packingPercent / 100);
    
    // Get freight amount
    const freightAmount = parseFloat(customFreightAmount) || 0;
    
    // Calculate final total
    const taxableAmount = afterDiscount + packingCharges + freightAmount;
    const total = taxableAmount * 1.18; // Include 18% GST
    
    return {
      subtotal,
      discountAmount,
      afterDiscount,
      packingCharges,
      freightAmount,
      taxableAmount,
      total
    };
  };

  const { user, loading: authLoading } = useAuth();
  
  // Check if user is customer - show RFQ terminology
  const isCustomer = user?.role === 'customer';
  const isAdmin = user?.role === 'admin';
  const docLabel = isCustomer ? 'RFQ' : 'Quote';
  
  // Debug log
  console.log('QuotesScreen - user:', user, 'isCustomer:', isCustomer, 'isAdmin:', isAdmin, 'authLoading:', authLoading);

  // Authenticated file download function
  const downloadAttachment = async (quoteId: string, productIdx: number, attachmentIdx: number, filename: string) => {
    try {
      const token = await AsyncStorage.getItem('token');
      const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const url = `${baseUrl}/api/quotes/${quoteId}/attachments/${productIdx}/${attachmentIdx}/download`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      
      const blob = await response.blob();
      
      // Create download link
      if (Platform.OS === 'web') {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        Alert.alert('Info', 'File download is available on web only');
      }
    } catch (error: any) {
      console.error('Download error:', error);
      Alert.alert('Download Failed', error.message || 'Failed to download attachment');
    }
  };

  // Download all attachments as ZIP
  const downloadAllAsZip = async (quoteId: string, quoteNumber: string) => {
    try {
      const token = await AsyncStorage.getItem('token');
      const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const url = `${baseUrl}/api/quotes/${quoteId}/attachments/download-all`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }
      
      const blob = await response.blob();
      
      // Create download link
      if (Platform.OS === 'web') {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `${quoteNumber.replace(/\//g, '-')}_attachments.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        Alert.alert('Info', 'File download is available on web only');
      }
    } catch (error: any) {
      console.error('Download error:', error);
      Alert.alert('Download Failed', error.message || 'Failed to download attachments');
    }
  };

  useEffect(() => {
    // Only fetch quotes when auth is loaded and user exists
    if (!authLoading && user) {
      fetchQuotes();
      fetchCommercialTermsOptions();
    }
    
    // Listen for global refresh events
    const handleRefresh = () => {
      console.log('[Quotes] Received refresh event, refetching data...');
      if (user) {
        fetchQuotes();
        fetchCommercialTermsOptions();
      }
    };
    
    cacheEvents.on('refresh', handleRefresh);
    
    return () => {
      cacheEvents.off('refresh', handleRefresh);
    };
  }, [authLoading, user]);

  // Fetch commercial terms options
  const fetchCommercialTermsOptions = async () => {
    try {
      const response = await api.get('/commercial-terms-options');
      setCommercialTermsOptions(response.data);
    } catch (error: any) {
      console.error('Error fetching commercial terms options:', error);
    }
  };

  // Recalculate freight when discount changes (if freight is percentage-based)
  useEffect(() => {
    // Only recalculate if we're in approval mode and using freight percentage
    if ((selectedQuote || approveModalQuote) && !useCustomFreight && parseFloat(freightPercent) > 0) {
      // Freight percentage mode - recalculate based on new discount
      // The calculateFreightAmount function already handles this
      // Just trigger a re-render by updating a dummy state or relying on deps
    }
  }, [totalDiscountPercent, itemDiscounts, useItemDiscount, freightPercent, useCustomFreight]);

  const fetchQuotes = async () => {
    try {
      const response = await api.get('/quotes');
      setQuotes(response.data);
    } catch (error: any) {
      console.error('Error fetching quotes:', error);
      Alert.alert('Error', `Failed to load ${docLabel.toLowerCase()}s`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchOrders = async () => {
    setOrdersLoading(true);
    try {
      const response = await api.get('/orders');
      setOrders(response.data.orders || []);
    } catch (error: any) {
      console.error('Error fetching orders:', error);
    } finally {
      setOrdersLoading(false);
    }
  };

  const fetchWorkOrders = async () => {
    setWoLoading(true);
    try {
      const response = await api.get('/work-orders');
      setWorkOrders(response.data.work_orders || []);
    } catch (error: any) {
      console.error('Error fetching work orders:', error);
    } finally {
      setWoLoading(false);
    }
  };

  // Mark RFQ as read by admin
  const markAsRead = async (quoteId: string) => {
    if (!isAdmin) return;
    
    try {
      await api.post(`/quotes/${quoteId}/mark-read`);
      // Update local state to reflect read status
      setQuotes(prevQuotes => 
        prevQuotes.map(q => 
          q.id === quoteId ? { ...q, read_by_admin: true } : q
        )
      );
    } catch (error) {
      console.error('Error marking quote as read:', error);
    }
  };

  // Fetch revision history for a quote
  const fetchRevisionHistory = async (quoteId: string) => {
    setLoadingHistory(true);
    try {
      const response = await api.get(`/quotes/${quoteId}/history`);
      const history = response.data.history || [];
      
      // Transform old format to new format if needed
      const transformedHistory: RevisionHistoryEntry[] = history.map((entry: any) => {
        // Check if it's old format (has 'revision' field) or new format (has 'action' field)
        if (entry.revision && !entry.action) {
          // Old format - transform to new format
          return {
            timestamp: entry.revised_at || '',
            changed_by: entry.revised_by || 'Unknown',
            changed_by_name: entry.revised_by || 'Unknown',
            action: 'revised',
            changes: {
              'Discount %': { old: '', new: `${entry.discount_percent || 0}%` },
              'Discount Amount': { old: '', new: `Rs. ${(entry.discount_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` },
              'Total Price': { old: '', new: `Rs. ${(entry.total_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` },
            },
            summary: `${entry.revision}: ${entry.notes || 'Quote revised'}`
          };
        }
        // New format - return as is
        return entry;
      });
      
      setRevisionHistory(transformedHistory);
      setShowRevisionHistory(true);
    } catch (error) {
      console.error('Error fetching revision history:', error);
      Alert.alert('Error', 'Failed to load revision history');
    } finally {
      setLoadingHistory(false);
    }
  };

  // Format revision timestamp
  const formatRevisionDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  // Open quote detail and mark as read
  const openQuoteDetail = async (quote: Quote) => {
    setSelectedQuote(quote);
    // Initialize editable fields for admin
    setEditPackingType(quote.packing_type || 'standard');
    setEditDeliveryPincode(quote.delivery_location || '');
    setFreightPercent(quote.freight_details?.freight_percent?.toString() || '0');
    setCustomFreightAmount(quote.shipping_cost?.toString() || '0');
    setUseCustomFreight(false);
    setCustomPackingPercent('');
    setEditableProducts([...(quote.products || [])]);
    setPincodeError('');
    setPincodeValid(true);
    setCalculatedFreightFromPincode(0);
    // Initialize discount state
    setUseItemDiscount(quote.use_item_discounts || false);
    setTotalDiscountPercent(quote.discount_percent?.toString() || '0');
    // Initialize commercial terms from quote or use defaults
    const ct = quote.commercial_terms || {};
    setSelectedPaymentTerms(ct.payment_terms || '100% Advance against pro-forma');
    setSelectedFreightTerms(ct.freight_terms || 'Ex-Works');
    setSelectedColorFinish(ct.color_finish || '1+1 : Red oxide + finish paint black color approx 50-60 micron');
    setSelectedDeliveryTimeline(ct.delivery_timeline || '25-30 working days');
    // Ensure commercial terms options are loaded
    if (!commercialTermsOptions) {
      await fetchCommercialTermsOptions();
    }
    // Initialize item discounts from products - use item_discount_percent field
    const discounts: {[key: number]: string} = {};
    quote.products?.forEach((p, idx) => {
      discounts[idx] = p.item_discount_percent?.toString() || '0';
    });
    setItemDiscounts(discounts);
    // Mark as read if admin and quote is pending RFQ and unread
    const isRfq = quote.quote_number?.startsWith('RFQ/');
    if (isAdmin && quote.status === 'pending' && isRfq && !quote.read_by_admin) {
      markAsRead(quote.id);
    }
    // DON'T auto-calculate freight from pincode here - use the original freight
    // The calculateFreightAmount function will recalculate based on discount changes
    // Just validate the pincode if it exists
    if (quote.delivery_location && quote.delivery_location.length === 6) {
      setTimeout(async () => {
        await validatePincode(quote.delivery_location!);
      }, 100);
    }
  };

  // Validate pincode using API
  const validatePincode = async (pincode: string) => {
    if (!pincode || pincode.length !== 6) {
      setPincodeError('Pincode must be 6 digits');
      setPincodeValid(false);
      return false;
    }
    
    try {
      const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const data = await response.json();
      
      if (data[0]?.Status === 'Success') {
        setPincodeError('');
        setPincodeValid(true);
        return true;
      } else {
        setPincodeError('Invalid pincode');
        setPincodeValid(false);
        return false;
      }
    } catch (error) {
      console.error('Pincode validation error:', error);
      setPincodeError('Unable to validate pincode');
      setPincodeValid(false);
      return false;
    }
  };

  // Handle pincode change with validation and freight calculation
  const handlePincodeChange = async (pincode: string) => {
    setEditDeliveryPincode(pincode);
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      // Validate pincode
      validatePincode(pincode);
      // Calculate freight automatically
      const productsToUse = editableProducts.length > 0 ? editableProducts : 
        (selectedQuote?.products || []);
      if (productsToUse.length > 0) {
        await calculateFreightFromPincode(pincode, productsToUse);
      }
    } else if (pincode.length > 0) {
      setPincodeError('Pincode must be 6 digits');
      setPincodeValid(false);
      setCalculatedFreightFromPincode(0);
    } else {
      setPincodeError('');
      setPincodeValid(true);
      setCalculatedFreightFromPincode(0);
    }
  };

  // Update product quantity
  const updateProductQuantity = (index: number, newQty: number | string) => {
    const qty = typeof newQty === 'string' ? parseInt(newQty) || 0 : newQty;
    if (qty < 1) return;
    const updatedProducts = [...editableProducts];
    updatedProducts[index] = {
      ...updatedProducts[index],
      quantity: qty
    };
    setEditableProducts(updatedProducts);
  };

  // Update quantity in editedProducts (for Edit Quote modal on approved quotes)
  const updateEditedProductQuantity = (index: number, newQty: string) => {
    const qty = parseInt(newQty) || 0;
    if (qty < 1) return;
    const updated = [...editedProducts];
    updated[index] = { ...updated[index], quantity: qty };
    setEditedProducts(updated);
  };

  // Delete product from list
  const deleteProduct = (index: number) => {
    if (editableProducts.length <= 1) {
      Alert.alert('Error', 'Cannot delete the last item. At least one item is required.');
      return;
    }
    const updatedProducts = editableProducts.filter((_, i) => i !== index);
    setEditableProducts(updatedProducts);
  };

  // Calculate editable subtotal
  const calculateEditableSubtotal = () => {
    return editableProducts.reduce((sum, product) => {
      return sum + (product.unit_price * product.quantity);
    }, 0);
  };

  // Calculate total discount based on mode
  const calculateTotalDiscount = () => {
    const subtotal = calculateEditableSubtotal();
    
    if (!useItemDiscount) {
      // Total discount mode
      const discountPct = parseFloat(totalDiscountPercent) || 0;
      return subtotal * (discountPct / 100);
    } else {
      // Item-wise discount mode
      return editableProducts.reduce((total, product, index) => {
        const itemSubtotal = product.unit_price * product.quantity;
        const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
        return total + (itemSubtotal * (itemDiscountPct / 100));
      }, 0);
    }
  };

  // Get unread count for badge - only count RFQs (customer-generated)
  const unreadCount = quotes.filter(q => 
    q.status === 'pending' && 
    q.quote_number?.startsWith('RFQ/') && 
    !q.read_by_admin
  ).length;

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchQuotes();
  }, []);

  // Edit quote functions
  const openEditQuote = async (quote: Quote) => {
    setEditingQuote(quote);
    setEditedProducts([...quote.products]);
    setUseItemDiscounts(quote.use_item_discounts || false);
    // Calculate current discount percentage from the quote
    const discountPercent = quote.subtotal > 0 
      ? ((quote.total_discount / quote.subtotal) * 100).toFixed(1)
      : '0';
    setEditedDiscount(discountPercent);
    // Initialize freight with existing value
    setEditedFreight((quote.shipping_cost || 0).toString());
    // Initialize packing type - handle custom_X format
    const packingType = quote.packing_type || 'standard';
    if (packingType.startsWith('custom_')) {
      setEditedPackingType('custom');
      setCustomPackingPercent(packingType.split('_')[1] || '0');
    } else {
      setEditedPackingType(packingType);
      setCustomPackingPercent('');
    }
    // Initialize commercial terms from quote or use defaults
    const ct = quote.commercial_terms || {};
    setSelectedPaymentTerms(ct.payment_terms || '100% Advance against pro-forma');
    setSelectedFreightTerms(ct.freight_terms || 'Ex-Works');
    setSelectedColorFinish(ct.color_finish || '1+1 : Red oxide + finish paint black color approx 50-60 micron');
    setSelectedDeliveryTimeline(ct.delivery_timeline || '25-30 working days');
    // Ensure commercial terms options are loaded
    if (!commercialTermsOptions) {
      await fetchCommercialTermsOptions();
    }
  };

  const updateProductItemDiscount = (index: number, newDiscount: string) => {
    const discount = parseFloat(newDiscount) || 0;
    const updated = [...editedProducts];
    updated[index] = { ...updated[index], item_discount_percent: Math.min(100, Math.max(0, discount)) };
    setEditedProducts(updated);
  };

  const applyDiscountToAllItems = () => {
    const discount = parseFloat(bulkDiscountPercent) || 0;
    const clampedDiscount = Math.min(100, Math.max(0, discount));
    const updated = editedProducts.map(p => ({
      ...p,
      item_discount_percent: clampedDiscount
    }));
    setEditedProducts(updated);
  };

  const calculateEditedTotal = () => {
    let subtotal = 0;
    let totalItemDiscount = 0;
    
    // Helper function to get packing percent from editedPackingType
    const getPackingPercent = () => {
      if (editedPackingType === 'standard') return 1;
      if (editedPackingType === 'pallet') return 4;
      if (editedPackingType === 'wooden_box') return 8;
      if (editedPackingType === 'custom') return parseFloat(customPackingPercent) || 0;
      if (editedPackingType.startsWith('custom_')) return parseFloat(editedPackingType.split('_')[1]) || 0;
      return 0;
    };
    
    if (useItemDiscounts) {
      // Calculate with item-level discounts
      editedProducts.forEach(p => {
        const itemDiscountPercent = p.item_discount_percent || 0;
        const lineOriginal = p.unit_price * p.quantity;
        const lineDiscounted = lineOriginal * (1 - itemDiscountPercent / 100);
        subtotal += lineOriginal; // Subtotal is before discounts
        totalItemDiscount += (lineOriginal - lineDiscounted);
      });
      
      const afterDiscount = subtotal - totalItemDiscount;
      const packingPercent = getPackingPercent();
      const newPacking = afterDiscount * packingPercent / 100;
      const freightAmount = parseFloat(editedFreight) || 0;
      const taxableAmount = afterDiscount + newPacking + freightAmount;
      const grandTotal = taxableAmount * 1.18; // Include 18% GST
      return {
        subtotal,
        discountAmount: totalItemDiscount,
        afterDiscount,
        packingCharges: newPacking,
        taxableAmount,
        total: grandTotal // Grand total with GST
      };
    } else {
      // Use total discount percentage
      subtotal = editedProducts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
      const discountAmount = (subtotal * (parseFloat(editedDiscount) || 0)) / 100;
      const afterDiscount = subtotal - discountAmount;
      const packingPercent = getPackingPercent();
      const newPacking = afterDiscount * packingPercent / 100;
      const freightAmount = parseFloat(editedFreight) || 0;
      const taxableAmount = afterDiscount + newPacking + freightAmount;
      const grandTotal = taxableAmount * 1.18; // Include 18% GST
      return {
        subtotal,
        discountAmount,
        afterDiscount,
        packingCharges: newPacking,
        taxableAmount,
        total: grandTotal // Grand total with GST
      };
    }
  };

  // Save all changes and send email (single button for Edit Quote)
  const saveAndMailQuote = async () => {
    if (!editingQuote) return;
    
    setSavingEdit(true);
    try {
      const totals = calculateEditedTotal();
      const freightAmount = parseFloat(editedFreight) || 0;
      
      // Determine packing type string for storage
      const packingTypeToSave = editedPackingType === 'custom' 
        ? `custom_${customPackingPercent}` 
        : editedPackingType;
      
      // Update products with correct item_discount_percent
      const updatedProducts = editedProducts.map(product => {
        if (!useItemDiscounts) {
          // Total discount mode - apply the same discount to all products
          return {
            ...product,
            item_discount_percent: parseFloat(editedDiscount) || 0
          };
        } else {
          // Item-wise discount - keep existing item_discount_percent
          return product;
        }
      });
      
      const updateData: any = {
        products: updatedProducts,
        subtotal: totals.subtotal,
        total_discount: totals.discountAmount,
        use_item_discounts: useItemDiscounts,
        packing_charges: totals.packingCharges,
        packing_type: packingTypeToSave,
        shipping_cost: freightAmount,
        total_price: totals.total,
        commercial_terms: {
          payment_terms: selectedPaymentTerms,
          freight_terms: selectedFreightTerms,
          color_finish: selectedColorFinish,
          delivery_timeline: selectedDeliveryTimeline,
          warranty: commercialTermsOptions?.warranty || "Warranty stands for 12 months from date of invoice considering L10 life.",
          validity: commercialTermsOptions?.validity || "This offer stands valid for 30 days."
        }
      };
      
      // Only include discount_percent if using total discount mode
      if (!useItemDiscounts) {
        updateData.discount_percent = parseFloat(editedDiscount) || 0;
      }
      
      const response = await api.post(`/quotes/${editingQuote.id}/save-and-mail`, updateData);
      
      Alert.alert(
        'Quote Updated & Emailed!',
        `${response.data.revision}\nNew Total: Rs. ${response.data.total_price?.toFixed(2) || totals.total.toFixed(2)}\n\nEmail sent to customer.`
      );
      setEditingQuote(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || `Failed to update ${docLabel.toLowerCase()}`);
    } finally {
      setSavingEdit(false);
    }
  };

  const saveEditedQuote = async () => {
    if (!editingQuote) return;
    
    setSavingEdit(true);
    try {
      const totals = calculateEditedTotal();
      const freightAmount = parseFloat(editedFreight) || 0;
      
      // Determine packing type string for storage
      const packingTypeToSave = editedPackingType === 'custom' 
        ? `custom_${customPackingPercent}` 
        : editedPackingType;
      
      // Update products with correct item_discount_percent
      const updatedProducts = editedProducts.map(product => {
        if (!useItemDiscounts) {
          // Total discount mode - apply the same discount to all products
          return {
            ...product,
            item_discount_percent: parseFloat(editedDiscount) || 0
          };
        } else {
          // Item-wise discount - keep existing item_discount_percent
          return product;
        }
      });
      
      const updateData: any = {
        products: updatedProducts,
        subtotal: totals.subtotal,
        total_discount: totals.discountAmount,
        use_item_discounts: useItemDiscounts,
        packing_charges: totals.packingCharges,
        packing_type: packingTypeToSave,  // Include edited packing type
        shipping_cost: freightAmount,  // Include edited freight
        total_price: totals.total,
        commercial_terms: {
          payment_terms: selectedPaymentTerms,
          freight_terms: selectedFreightTerms,
          color_finish: selectedColorFinish,
          delivery_timeline: selectedDeliveryTimeline,
          warranty: commercialTermsOptions?.warranty || "Warranty stands for 12 months from date of invoice considering L10 life.",
          validity: commercialTermsOptions?.validity || "This offer stands valid for 30 days."
        }
      };
      
      // Only include discount_percent if using total discount mode
      if (!useItemDiscounts) {
        updateData.discount_percent = parseFloat(editedDiscount) || 0;
      }
      
      await api.put(`/quotes/${editingQuote.id}`, updateData);
      Alert.alert('Success', `${docLabel} updated successfully`);
      setEditingQuote(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || `Failed to update ${docLabel.toLowerCase()}`);
    } finally {
      setSavingEdit(false);
    }
  };

  // Save revision and send email (for approved quotes)
  const saveRevisionAndMail = async () => {
    if (!editingQuote) return;
    
    setSavingRevision(true);
    try {
      const response = await api.post(`/quotes/${editingQuote.id}/revise`, {
        discount_percent: parseFloat(editedDiscount) || 0,
        notes: `Revised by admin`
      });
      
      Alert.alert(
        'Quote Revised Successfully!',
        `${response.data.revision}\nNew Total: Rs. ${response.data.new_total_price.toFixed(2)}\n\nEmail sent to customer and admin.`
      );
      setEditingQuote(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create revision');
    } finally {
      setSavingRevision(false);
    }
  };

  // Calculate freight amount - simple calculation based on admin input
  const calculateFreightAmount = () => {
    const quote = approveModalQuote || selectedQuote;
    if (!quote) return 0;
    
    // If custom freight amount is entered, use it directly
    if (useCustomFreight) {
      return parseFloat(customFreightAmount) || 0;
    }
    
    // Calculate freight as percentage of discounted subtotal ONLY
    const percent = parseFloat(freightPercent) || 0;
    if (percent === 0) return 0;
    
    // Get current subtotal from editable products
    const currentSubtotal = editableProducts.length > 0 
      ? editableProducts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0)
      : (quote.subtotal || 0);
    
    // Calculate discount based on admin's entered values
    let currentDiscount = 0;
    if (useItemDiscount) {
      currentDiscount = editableProducts.reduce((total, product, index) => {
        const itemSubtotal = product.unit_price * product.quantity;
        const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
        return total + (itemSubtotal * (itemDiscountPct / 100));
      }, 0);
    } else {
      const discountPct = parseFloat(totalDiscountPercent) || 0;
      currentDiscount = currentSubtotal * (discountPct / 100);
    }
    
    const discountedSubtotal = currentSubtotal - currentDiscount;
    
    // Freight = Discounted Subtotal × freight%
    return discountedSubtotal * (percent / 100);
  };

  // Calculate freight based on pincode and product weight
  const calculateFreightFromPincode = async (pincode: string, products: any[]) => {
    if (!pincode || pincode.length !== 6) {
      setCalculatedFreightFromPincode(0);
      return;
    }
    
    // Calculate total weight from products
    // Weight can be in multiple places: weight_kg, base_weight_kg, specifications.weight_kg, cost_breakdown.total_weight_kg
    let totalWeight = 0;
    
    for (const p of products) {
      let weight = 0;
      
      // Try different sources for weight
      if (p.weight_kg) {
        weight = p.weight_kg;
      } else if (p.weight) {
        weight = p.weight;
      } else if (p.base_weight_kg) {
        weight = p.base_weight_kg;
      } else if (p.specifications?.weight_kg) {
        weight = p.specifications.weight_kg;
      } else if (p.cost_breakdown?.single_roller_weight_kg) {
        weight = p.cost_breakdown.single_roller_weight_kg;
      } else if (p.pricing_details?.single_roller_weight_kg) {
        weight = p.pricing_details.single_roller_weight_kg;
      } else {
        // Try to calculate weight from specifications via API
        const specs = p.specifications || {};
        if (specs.pipe_diameter && specs.pipe_length && specs.shaft_diameter) {
          try {
            const response = await api.post('/calculate-detailed-cost', {
              roller_type: specs.roller_type || p.roller_type || 'carrying',
              pipe_diameter: specs.pipe_diameter,
              pipe_length: specs.pipe_length,
              pipe_type: specs.pipe_type || 'B',
              shaft_diameter: specs.shaft_diameter,
              bearing: specs.bearing || '6205',
              bearing_number: specs.bearing || '6205',
              bearing_make: specs.bearing_make || 'skf',
              housing: specs.housing || 'CI Machined',
              quantity: 1
            });
            
            if (response.data?.cost_breakdown?.single_roller_weight_kg) {
              weight = response.data.cost_breakdown.single_roller_weight_kg;
            }
          } catch (err) {
            console.log('Could not fetch weight for product:', p.product_id);
          }
        }
        
        // Final fallback based on roller type (improved estimates)
        if (weight === 0) {
          const rollerType = specs.roller_type || p.product_name?.toLowerCase() || '';
          if (rollerType.includes('impact')) {
            weight = 15;
          } else if (rollerType.includes('return')) {
            weight = 8;
          } else {
            weight = 12; // Default carrying roller - improved estimate
          }
        }
      }
      
      totalWeight += weight * (p.quantity || 1);
    }
    
    if (totalWeight === 0) {
      setCalculatedFreightFromPincode(0);
      return;
    }
    
    setFreightLoading(true);
    try {
      // Call backend to calculate freight
      const response = await api.post('/calculate-freight', {
        pincode: pincode,
        total_weight_kg: totalWeight
      });
      
      if (response.data && response.data.freight_charges) {
        setCalculatedFreightFromPincode(response.data.freight_charges);
        // Auto-set as custom amount for clarity
        setCustomFreightAmount(response.data.freight_charges.toFixed(2));
        setUseCustomFreight(true);
      }
    } catch (error) {
      console.error('Freight calculation error:', error);
      setCalculatedFreightFromPincode(0);
    } finally {
      setFreightLoading(false);
    }
  };

  // Handle pincode change and calculate freight
  const handleDeliveryPincodeChange = async (pincode: string) => {
    setEditDeliveryPincode(pincode);
    
    // Validate pincode format
    if (pincode.length === 6 && /^\d{6}$/.test(pincode)) {
      // Validate pincode
      validatePincode(pincode);
      
      // Calculate freight - prefer editableProducts (from approval modal) over original quote products
      const productsToUse = editableProducts.length > 0 ? editableProducts : 
        (approveModalQuote?.products || selectedQuote?.products || []);
      
      if (productsToUse.length > 0) {
        await calculateFreightFromPincode(pincode, productsToUse);
      }
    } else {
      setCalculatedFreightFromPincode(0);
    }
  };

  // Approve RFQ with freight
  const confirmApproveRfq = async (quoteOverride?: Quote) => {
    // Use quoteOverride if passed directly, otherwise use state
    const quote = quoteOverride || approveModalQuote || selectedQuote;
    if (!quote) {
      console.error('confirmApproveRfq: No quote available');
      Alert.alert('Error', 'No quote selected for approval.');
      return;
    }
    
    // Check if quote has valid ID
    if (!quote.id) {
      console.error('confirmApproveRfq: Quote has no ID', quote);
      Alert.alert('Error', 'Invalid quote - missing ID.');
      return;
    }
    
    console.log('Approving quote:', quote.id, quote.quote_number);
    
    // Validate pincode before approving
    if (editDeliveryPincode && !pincodeValid) {
      Alert.alert('Error', 'Please enter a valid pincode before approving.');
      return;
    }
    
    setApprovingId(quote.id);
    try {
      // Use editableProducts if available, otherwise fall back to quote's original products
      const productsToUse = editableProducts.length > 0 ? editableProducts : (quote.products || []);
      
      // Calculate updated subtotal from products (original, before discount)
      const updatedSubtotal = productsToUse.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0);
      
      // Calculate discount values FIRST
      // NOTE: When admin enters discount (total or item-wise), system-calculated discount is replaced
      let totalDiscountAmount = 0;
      let updatedProducts = [...productsToUse];
      
      if (useItemDiscount) {
        // Item-wise discount mode - update each product with its discount
        updatedProducts = productsToUse.map((product, index) => {
          const itemDiscountPct = parseFloat(itemDiscounts[index] || '0') || 0;
          const itemSubtotal = product.unit_price * product.quantity;
          const itemDiscountAmount = itemSubtotal * (itemDiscountPct / 100);
          totalDiscountAmount += itemDiscountAmount;
          return {
            ...product,
            item_discount_percent: itemDiscountPct,
            calculated_discount: 0  // Clear system discount - admin discount replaces it
          };
        });
      } else {
        // Total discount mode
        const discountPct = parseFloat(totalDiscountPercent) || 0;
        totalDiscountAmount = updatedSubtotal * (discountPct / 100);
        // Apply the same discount percentage to all items
        updatedProducts = productsToUse.map(product => ({
          ...product,
          item_discount_percent: parseFloat(totalDiscountPercent) || 0,
          calculated_discount: 0  // Clear system discount - admin discount replaces it
        }));
      }
      
      // Calculate discounted subtotal (after discount)
      const discountedSubtotal = updatedSubtotal - totalDiscountAmount;
      
      // Calculate packing charges based on DISCOUNTED subtotal
      let packingPercent = 0;
      if (editPackingType === 'standard') packingPercent = 1;
      else if (editPackingType === 'pallet') packingPercent = 4;
      else if (editPackingType === 'wooden_box') packingPercent = 8;
      else if (editPackingType === 'custom') packingPercent = parseFloat(customPackingPercent) || 0;
      
      const packingCharges = discountedSubtotal * (packingPercent / 100);
      
      // Get freight amount directly from custom input
      const freightAmount = parseFloat(customFreightAmount) || 0;
      
      // Calculate final total price
      const taxableAmount = discountedSubtotal + packingCharges + freightAmount;
      const gst = taxableAmount * 0.18;
      const totalPrice = taxableAmount * 1.18;
      
      // First update the quote with products, freight, packing and discount details
      await api.put(`/quotes/${quote.id}`, {
        products: updatedProducts,
        subtotal: updatedSubtotal,
        total_discount: totalDiscountAmount,
        use_item_discounts: useItemDiscount,
        discount_percent: useItemDiscount ? 0 : (parseFloat(totalDiscountPercent) || 0),
        packing_charges: packingCharges,
        shipping_cost: freightAmount,
        packing_type: editPackingType === 'custom' ? `custom_${customPackingPercent}` : editPackingType,
        delivery_location: editDeliveryPincode,
        total_price: totalPrice,
        freight_details: {
          freight_amount: freightAmount
        },
        commercial_terms: {
          payment_terms: selectedPaymentTerms,
          freight_terms: selectedFreightTerms,
          color_finish: selectedColorFinish,
          delivery_timeline: selectedDeliveryTimeline,
          warranty: commercialTermsOptions?.warranty || "Warranty stands for 12 months from date of invoice considering L10 life.",
          validity: commercialTermsOptions?.validity || "This offer stands valid for 30 days."
        }
      });
      
      // Then approve
      const response = await api.post(`/quotes/${quote.id}/approve`);
      setApprovedQuoteNumber(response.data.new_quote_number || quote.quote_number);
      setShowApprovalSuccess(true);
      setApproveModalQuote(null);
      setSelectedQuote(null);
      fetchQuotes();
      setActiveTab('approved'); // Switch to approved tab
    } catch (error: any) {
      console.error('Approve RFQ error:', error);
      Alert.alert('Error', error.response?.data?.detail || 'Failed to approve RFQ');
    } finally {
      setApprovingId(null);
    }
  };

  // Approve RFQ function - open modal for freight input
  const approveRfq = async (quote: Quote) => {
    console.log('Opening approve modal for:', quote.quote_number);
    // Close the details modal first
    setSelectedQuote(null);
    setApproveModalQuote(quote);
    const existingFreightPercent = quote.freight_details?.freight_percent || 0;
    setFreightPercent(existingFreightPercent.toString());
    setCustomFreightAmount(quote.shipping_cost?.toString() || '0');
    setUseCustomFreight(false);
    // Set packing and delivery from quote
    setEditPackingType(quote.packing_type || 'standard');
    setEditDeliveryPincode(quote.delivery_location || '');
    // Initialize editable products for approval modal
    setEditableProducts([...(quote.products || [])]);
    // Reset freight calculation state
    setCalculatedFreightFromPincode(0);
    setPincodeError('');
    setPincodeValid(true);
    // Initialize discount state
    setUseItemDiscount(quote.use_item_discounts || false);
    setTotalDiscountPercent(quote.discount_percent?.toString() || '0');
    const discounts: {[key: number]: string} = {};
    quote.products?.forEach((p, idx) => {
      discounts[idx] = p.item_discount_percent?.toString() || '0';
    });
    setItemDiscounts(discounts);
    // Initialize commercial terms from quote or use defaults
    const ct = quote.commercial_terms || {};
    setSelectedPaymentTerms(ct.payment_terms || '100% Advance against pro-forma');
    setSelectedFreightTerms(ct.freight_terms || 'Ex-Works');
    setSelectedColorFinish(ct.color_finish || '1+1 : Red oxide + finish paint black color approx 50-60 micron');
    setSelectedDeliveryTimeline(ct.delivery_timeline || '25-30 working days');
    // If there's an existing delivery pincode, auto-calculate freight
    if (quote.delivery_location && quote.delivery_location.length === 6) {
      // Validate and calculate freight after a short delay to let state settle
      setTimeout(async () => {
        await validatePincode(quote.delivery_location!);
        if (quote.products && quote.products.length > 0) {
          await calculateFreightFromPincode(quote.delivery_location!, quote.products);
        }
      }, 100);
    }
  };
  
  // Open reject modal
  const openRejectModal = (quote: Quote) => {
    setRejectingQuote(quote);
    setSelectedRejectReason(null);
    setShowRejectModal(true);
  };
  
  // Confirm reject RFQ
  const confirmRejectRfq = async () => {
    if (!rejectingQuote || !selectedRejectReason) return;
    
    setRejectingId(rejectingQuote.id);
    try {
      await api.post(`/quotes/${rejectingQuote.id}/reject`, {
        reason: selectedRejectReason
      });
      
      Alert.alert('Success', 'RFQ has been rejected and the customer has been notified.');
      setShowRejectModal(false);
      setRejectingQuote(null);
      setSelectedRejectReason(null);
      fetchQuotes();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to reject RFQ');
    } finally {
      setRejectingId(null);
    }
  };

  // Filter quotes based on active tab and search query
  const getFilteredQuotes = () => {
    let filtered = quotes;
    
    // First filter by tab
    if (isCustomer) {
      // Customer tabs: Active (pending RFQs) vs History (approved/rejected)
      switch (activeTab) {
        case 'active':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'pending');
          break;
        case 'history':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'approved' || q.status?.toLowerCase() === 'rejected');
          break;
        default:
          break;
      }
    } else {
      // Admin tabs
      switch (activeTab) {
        case 'pending':
          filtered = filtered.filter(q => q.quote_number?.startsWith('RFQ') && q.status?.toLowerCase() !== 'approved' && q.status?.toLowerCase() !== 'rejected');
          break;
        case 'approved':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'approved');
          break;
        case 'rejected':
          filtered = filtered.filter(q => q.status?.toLowerCase() === 'rejected');
          break;
        default:
          break;
      }
    }
    
    // Then filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(q => {
        // Search by quote number
        if (q.quote_number?.toLowerCase().includes(query)) return true;
        // Search by customer name
        if (q.customer_name?.toLowerCase().includes(query)) return true;
        // Search by company
        if (q.customer_company?.toLowerCase().includes(query)) return true;
        if (q.customer_details?.company?.toLowerCase().includes(query)) return true;
        // Search by email
        if (q.customer_email?.toLowerCase().includes(query)) return true;
        // Search by phone
        if (q.customer_details?.phone?.toLowerCase().includes(query)) return true;
        // Search by GST
        if (q.customer_details?.gst_number?.toLowerCase().includes(query)) return true;
        // Search by city/state
        if (q.customer_details?.city?.toLowerCase().includes(query)) return true;
        if (q.customer_details?.state?.toLowerCase().includes(query)) return true;
        // Search by product names
        if (q.products?.some(p => p.product_name?.toLowerCase().includes(query))) return true;
        // Search by status
        if (q.status?.toLowerCase().includes(query)) return true;
        return false;
      });
    }
    
    // Sort by date - newest first
    filtered.sort((a, b) => {
      const dateA = new Date(a.approved_at || a.created_at || 0).getTime();
      const dateB = new Date(b.approved_at || b.created_at || 0).getTime();
      return dateB - dateA; // Descending order (newest first)
    });
    
    return filtered;
  };

  // Export search results to CSV
  const exportSearchResults = (type: string) => {
    const filteredQuotes = getFilteredQuotes();
    if (filteredQuotes.length === 0) {
      Alert.alert('No Data', 'No results to export');
      return;
    }

    // Create CSV content
    const headers = ['Quote Number', 'Customer Name', 'Company', 'Status', 'Total Price', 'Items', 'Date'];
    const rows = filteredQuotes.map(q => [
      q.quote_number || '',
      q.customer_name || '',
      q.customer_company || q.customer_details?.company || '',
      q.status || 'Pending',
      `Rs. ${(q.total_price || 0).toFixed(2)}`,
      (q.products?.length || 0).toString(),
      q.created_at ? new Date(q.created_at).toLocaleDateString('en-IN') : ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Download CSV
    if (Platform.OS === 'web') {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quotes_export_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      Alert.alert('Success', `Exported ${filteredQuotes.length} quotes to CSV`);
    } else {
      Alert.alert('Export', 'CSV export is available on web. Please use the web version for exports.');
    }
  };

  const pendingRfqCount = quotes.filter(q => q.quote_number?.startsWith('RFQ') && q.status?.toLowerCase() === 'pending').length;

  // Helper to generate PDF HTML using the extracted utility
  const generatePdfHtmlForQuote = (quote: Quote) => {
    return generatePdfHtml(quote, { isCustomer });
  };

  const exportToPdf = async () => {
    if (!selectedQuote) return;
    
    setGeneratingPdf(true);
    try {
      // For all platforms, try to use the backend PDF generation endpoint first
      const token = await AsyncStorage.getItem('token');
      const quoteId = selectedQuote.id || selectedQuote._id;
      
      if (token && quoteId) {
        // Use backend endpoint for PDF generation
        const pdfUrl = `${api.defaults.baseURL}/quotes/${quoteId}/pdf?token=${token}`;
        
        if (Platform.OS === 'web') {
          // For web, open PDF in new tab
          window.open(pdfUrl, '_blank');
        } else {
          // For mobile, download and share
          const filename = `${selectedQuote.quote_number || 'Quote'}_${new Date().toISOString().slice(0, 10)}.pdf`;
          const fileUri = `${FileSystem.cacheDirectory}${filename}`;
          
          const downloadResult = await FileSystem.downloadAsync(pdfUrl, fileUri);
          
          if (downloadResult.status === 200) {
            const isAvailable = await Sharing.isAvailableAsync();
            if (isAvailable) {
              await Sharing.shareAsync(downloadResult.uri, {
                mimeType: 'application/pdf',
                dialogTitle: 'Share PDF',
                UTI: 'com.adobe.pdf',
              });
            } else {
              Alert.alert('Success', 'PDF downloaded successfully');
            }
          } else {
            throw new Error('Failed to download PDF');
          }
        }
      } else {
        // Fallback to client-side generation
        const html = generatePdfHtmlForQuote(selectedQuote);
        
        if (Platform.OS === 'web') {
          // For web, open in new window and trigger print
          const printWindow = window.open('', '_blank');
          if (printWindow) {
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.focus();
            setTimeout(() => {
              printWindow.print();
            }, 500);
          } else {
            Alert.alert('Error', 'Please allow popups to export PDF');
          }
        } else {
          // For mobile, use Print.printAsync which opens native print dialog
          await Print.printAsync({
            html,
          });
        }
      }
    } catch (error: any) {
      console.error('PDF generation error:', error);
      Alert.alert('PDF Error', error.message || 'Failed to generate PDF');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const renderQuote = ({ item }: { item: Quote }) => {
    return (
      <QuoteCard
        quote={item}
        isAdmin={isAdmin}
        isCustomer={isCustomer}
        docLabel={docLabel}
        onPress={openQuoteDetail}
        onConvertToSO={(quote) => {
          setConvertQuote(quote);
          setDeliveryDate('');
          setShowConvertSO(true);
        }}
        formatDate={formatDate}
        getStatusColor={getStatusColor}
        getStatusIcon={getStatusIcon}
      />
    );
  };

  // Show loading until auth is ready
  if (authLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  if (loading && !refreshing) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#960018" />
        <Text style={styles.loadingText}>Loading {docLabel.toLowerCase()}s...</Text>
      </View>
    );
  }

  // If Edit Quote is active, render full screen edit view using Modal
  if (approveModalQuote) {
    return (
      <Modal
        visible={true}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setApproveModalQuote(null)}
      >
        <View style={{ flex: 1, backgroundColor: '#fff' }}>
          <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }}>
            <View style={[styles.modalHeader, { backgroundColor: '#fff' }]}>
              <Text style={styles.modalTitle}>Edit Quote</Text>
              <TouchableOpacity onPress={() => setApproveModalQuote(null)}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>
            <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={{paddingBottom: 120, backgroundColor: '#fff'}}>
          {/* RFQ Info */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>RFQ Details</Text>
            <Text style={styles.approveQuoteNumber}>{approveModalQuote.quote_number}</Text>
            <Text style={styles.approveCustomerName}>{approveModalQuote.customer_name}</Text>
            {approveModalQuote.customer_company && (
              <Text style={styles.approveCompanyName}>{approveModalQuote.customer_company}</Text>
            )}
          </View>

          {/* Products List */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Items Requested ({approveModalQuote.products?.length || 0})</Text>
            {approveModalQuote.products?.map((product, idx) => (
              <View key={idx} style={styles.editProductItem}>
                <View style={styles.editProductHeader}>
                  <Text style={styles.editProductName}>{product.product_name}</Text>
                  <Text style={styles.editProductQty}>Qty: {product.quantity}</Text>
                </View>
                <View style={styles.editProductDetails}>
                  <Text style={styles.editProductPrice}>Unit Price: Rs. {product.unit_price?.toFixed(2)}</Text>
                  <Text style={styles.editProductTotal}>Total: Rs. {(product.unit_price * product.quantity)?.toFixed(2)}</Text>
                </View>
                {product.remarks && (
                  <Text style={styles.editProductRemarks}>Remarks: {product.remarks}</Text>
                )}
              </View>
            ))}
            <View style={[styles.subtotalRow, { backgroundColor: '#fff' }]}>
              <Text style={styles.subtotalLabel}>Subtotal:</Text>
              <Text style={styles.subtotalValue}>Rs. {((approveModalQuote.subtotal || 0) - (approveModalQuote.total_discount || 0)).toFixed(2)}</Text>
            </View>
          </View>

          {/* Packing Type Selection */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Packing Type</Text>
            <View style={[styles.packingOptions, { backgroundColor: '#fff' }]}>
              {[
                { value: 'standard', label: 'Standard (1%)' },
                { value: 'pallet', label: 'Pallet (4%)' },
                { value: 'wooden_box', label: 'Wooden Box (8%)' }
              ].map((option) => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.packingOption,
                    editPackingType === option.value && styles.packingOptionActive
                  ]}
                  onPress={() => setEditPackingType(option.value)}
                >
                  <Ionicons 
                    name={editPackingType === option.value ? 'radio-button-on' : 'radio-button-off'} 
                    size={20} 
                    color={editPackingType === option.value ? '#960018' : '#666'} 
                  />
                  <Text style={[
                    styles.packingOptionText,
                    editPackingType === option.value && styles.packingOptionTextActive
                  ]}>{option.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Freight Section */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Freight Charges</Text>
            
            {/* Delivery Pincode */}
            <View style={[styles.freightInputRow, { backgroundColor: '#fff' }]}>
              <Text style={styles.freightInputLabel}>Delivery Pincode:</Text>
              <TextInput
                style={[styles.freightInput, { flex: 1 }, pincodeError ? { borderColor: '#ef4444' } : {}]}
                value={editDeliveryPincode}
                onChangeText={handleDeliveryPincodeChange}
                keyboardType="numeric"
                placeholder="Enter pincode"
                maxLength={6}
              />
              {freightLoading && (
                <ActivityIndicator size="small" color="#8B0000" style={{ marginLeft: 8 }} />
              )}
            </View>
            {pincodeError ? (
              <Text style={{ color: '#ef4444', fontSize: 12, marginTop: 4, marginLeft: 4 }}>{pincodeError}</Text>
            ) : null}
            {calculatedFreightFromPincode > 0 && !freightLoading && (
              <Text style={{ color: '#059669', fontSize: 12, marginTop: 4, marginLeft: 4 }}>
                Auto-calculated freight: Rs. {calculatedFreightFromPincode.toFixed(2)} (based on weight & distance)
              </Text>
            )}
            
            {/* Freight Input - Custom Amount Only */}
            <View style={styles.freightInputRow}>
              <Text style={styles.freightInputLabel}>Freight Charges:</Text>
              <View style={styles.freightInputWrapper}>
                <Text style={styles.freightInputPrefix}>Rs.</Text>
                <TextInput
                  style={styles.freightInput}
                  value={customFreightAmount}
                  onChangeText={setCustomFreightAmount}
                  keyboardType="numeric"
                  placeholder="0"
                />
              </View>
            </View>
          </View>

          {/* Discount Section */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Discount</Text>
            
            {/* Discount Mode Toggle */}
            <View style={styles.discountModeToggle}>
              <TouchableOpacity
                style={[styles.discountModeButton, !useItemDiscount && styles.discountModeButtonActive]}
                onPress={() => setUseItemDiscount(false)}
              >
                <Text style={[styles.discountModeText, !useItemDiscount && styles.discountModeTextActive]}>Total Discount</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.discountModeButton, useItemDiscount && styles.discountModeButtonActive]}
                onPress={() => setUseItemDiscount(true)}
              >
                <Text style={[styles.discountModeText, useItemDiscount && styles.discountModeTextActive]}>Per-Item Discount</Text>
              </TouchableOpacity>
            </View>
            
            {!useItemDiscount ? (
              /* Total Discount Input */
              <View style={styles.freightInputRow}>
                <Text style={styles.freightInputLabel}>Discount %:</Text>
                <View style={styles.freightInputWrapper}>
                  <TextInput
                    style={styles.freightInput}
                    value={totalDiscountPercent}
                    onChangeText={setTotalDiscountPercent}
                    keyboardType="numeric"
                    placeholder="0"
                  />
                  <Text style={styles.freightInputSuffix}>%</Text>
                </View>
              </View>
            ) : (
              /* Per-Item Discount Inputs */
              <View style={{ marginTop: 8 }}>
                {(editableProducts.length > 0 ? editableProducts : approveModalQuote?.products || []).map((product, idx) => (
                  <View key={idx} style={styles.itemDiscountRow}>
                    <Text style={styles.itemDiscountName} numberOfLines={1}>
                      {product.product_name || `Item ${idx + 1}`}
                    </Text>
                    <View style={styles.freightInputWrapper}>
                      <TextInput
                        style={[styles.freightInput, { width: 60 }]}
                        value={itemDiscounts[idx] || '0'}
                        onChangeText={(val) => setItemDiscounts(prev => ({ ...prev, [idx]: val }))}
                        keyboardType="numeric"
                        placeholder="0"
                      />
                      <Text style={styles.freightInputSuffix}>%</Text>
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>

          {/* Commercial Terms Section */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Commercial Terms</Text>
            
            {commercialTermsOptions ? (
              <>
                {/* Payment Terms Dropdown */}
                <View style={styles.dropdownRow}>
                  <Text style={styles.dropdownLabel}>Payment Terms:</Text>
                  <View style={styles.dropdownContainer}>
                    <select
                      value={selectedPaymentTerms}
                      onChange={(e: any) => setSelectedPaymentTerms(e.target.value)}
                      style={{
                        width: '100%',
                        padding: 12,
                        fontSize: 14,
                        borderRadius: 8,
                        border: '1px solid #ddd',
                        backgroundColor: '#fff',
                        cursor: 'pointer'
                      }}
                    >
                      {commercialTermsOptions.payment_terms?.map((term: string, idx: number) => (
                        <option key={idx} value={term}>{term}</option>
                      ))}
                    </select>
                  </View>
                </View>
                
                {/* Freight Terms Dropdown */}
                <View style={styles.dropdownRow}>
                  <Text style={styles.dropdownLabel}>Freight Terms:</Text>
                  <View style={styles.dropdownContainer}>
                    <select
                      value={selectedFreightTerms}
                      onChange={(e: any) => setSelectedFreightTerms(e.target.value)}
                      style={{
                        width: '100%',
                        padding: 12,
                        fontSize: 14,
                        borderRadius: 8,
                        border: '1px solid #ddd',
                        backgroundColor: '#fff',
                        cursor: 'pointer'
                      }}
                    >
                      {commercialTermsOptions.freight_terms?.map((term: string, idx: number) => (
                        <option key={idx} value={term}>{term}</option>
                      ))}
                    </select>
                  </View>
                </View>
                
                {/* Color/Finish Dropdown */}
                <View style={styles.dropdownRow}>
                  <Text style={styles.dropdownLabel}>Color/Finish:</Text>
                  <View style={styles.dropdownContainer}>
                    <select
                      value={selectedColorFinish}
                      onChange={(e: any) => setSelectedColorFinish(e.target.value)}
                      style={{
                        width: '100%',
                        padding: 12,
                        fontSize: 14,
                        borderRadius: 8,
                        border: '1px solid #ddd',
                        backgroundColor: '#fff',
                        cursor: 'pointer'
                      }}
                    >
                      {commercialTermsOptions.color_finish?.map((term: string, idx: number) => (
                        <option key={idx} value={term}>{term}</option>
                      ))}
                    </select>
                  </View>
                </View>
                
                {/* Delivery Timeline Dropdown */}
                <View style={styles.dropdownRow}>
                  <Text style={styles.dropdownLabel}>Delivery:</Text>
                  <View style={styles.dropdownContainer}>
                    <select
                      value={selectedDeliveryTimeline}
                      onChange={(e: any) => setSelectedDeliveryTimeline(e.target.value)}
                      style={{
                        width: '100%',
                        padding: 12,
                        fontSize: 14,
                        borderRadius: 8,
                        border: '1px solid #ddd',
                        backgroundColor: '#fff',
                        cursor: 'pointer'
                      }}
                    >
                      {commercialTermsOptions.delivery_timeline?.map((term: string, idx: number) => (
                        <option key={idx} value={term}>{term}</option>
                      ))}
                    </select>
                  </View>
                </View>
                
                {/* Fixed Terms Display */}
                <View style={[styles.dropdownRow, { marginTop: 16 }]}>
                  <Text style={[styles.dropdownLabel, { fontWeight: '600' }]}>Warranty:</Text>
                  <Text style={styles.fixedTermText}>{commercialTermsOptions.warranty}</Text>
                </View>
                <View style={styles.dropdownRow}>
                  <Text style={[styles.dropdownLabel, { fontWeight: '600' }]}>Validity:</Text>
                  <Text style={styles.fixedTermText}>{commercialTermsOptions.validity}</Text>
                </View>
              </>
            ) : (
              <Text style={{ color: '#999', fontStyle: 'italic' }}>Loading...</Text>
            )}
          </View>

          {/* Summary Section - Real-time Calculation */}
          <View style={[styles.detailSection, { backgroundColor: '#fff' }]}>
            <Text style={styles.sectionTitle}>Summary</Text>
            
            {/* Subtotal */}
            <View style={styles.pricingRow}>
              <Text style={styles.pricingLabel}>Subtotal</Text>
              <Text style={styles.pricingValue}>Rs. {calculateApprovalTotal().subtotal.toFixed(2)}</Text>
            </View>
            
            {/* Discount */}
            {calculateApprovalTotal().discountAmount > 0 && (
              <View style={styles.pricingRow}>
                <Text style={[styles.pricingLabel, { color: '#059669' }]}>
                  Discount {!useItemDiscount ? `(${totalDiscountPercent || 0}%)` : '(Per-Item)'}
                </Text>
                <Text style={[styles.pricingValue, { color: '#059669' }]}>
                  - Rs. {calculateApprovalTotal().discountAmount.toFixed(2)}
                </Text>
              </View>
            )}
            
            {/* Packing Charges */}
            <View style={styles.pricingRow}>
              <Text style={styles.pricingLabel}>
                Packing Charges ({editPackingType === 'standard' ? '1' : editPackingType === 'pallet' ? '4' : editPackingType === 'wooden_box' ? '8' : customPackingPercent || '0'}%)
              </Text>
              <Text style={styles.pricingValue}>Rs. {calculateApprovalTotal().packingCharges.toFixed(2)}</Text>
            </View>
            
            {/* Freight */}
            <View style={styles.pricingRow}>
              <Text style={styles.pricingLabel}>Freight Charges</Text>
              <Text style={styles.pricingValue}>Rs. {calculateApprovalTotal().freightAmount.toFixed(2)}</Text>
            </View>
            
            {/* Taxable Amount */}
            <View style={styles.pricingRow}>
              <Text style={styles.pricingLabel}>Taxable Amount</Text>
              <Text style={styles.pricingValue}>Rs. {calculateApprovalTotal().taxableAmount.toFixed(2)}</Text>
            </View>
            
            {/* GST */}
            <View style={styles.pricingRow}>
              <Text style={styles.pricingLabel}>CGST @ 9%</Text>
              <Text style={styles.pricingValue}>Rs. {(calculateApprovalTotal().taxableAmount * 0.09).toFixed(2)}</Text>
            </View>
            <View style={styles.pricingRow}>
              <Text style={styles.pricingLabel}>SGST @ 9%</Text>
              <Text style={styles.pricingValue}>Rs. {(calculateApprovalTotal().taxableAmount * 0.09).toFixed(2)}</Text>
            </View>
            
            {/* Grand Total */}
            <View style={[styles.pricingRow, styles.totalRow]}>
              <Text style={styles.totalLabel}>GRAND TOTAL</Text>
              <Text style={styles.totalValue}>Rs. {calculateApprovalTotal().total.toFixed(2)}</Text>
            </View>
          </View>

          {/* Action Buttons */}
          <View style={[styles.approveRejectButtons, { backgroundColor: '#fff' }]}>
            {/* Approve Button */}
            <TouchableOpacity 
              style={styles.approveConfirmButton}
              onPress={confirmApproveRfq}
              disabled={approvingId === approveModalQuote.id}
            >
              {approvingId === approveModalQuote.id ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={24} color="#fff" />
                  <Text style={styles.approveConfirmButtonText}>Approve</Text>
                </>
              )}
            </TouchableOpacity>
            
            {/* Reject Button */}
            <TouchableOpacity 
              style={styles.rejectButton}
              onPress={() => {
                const quoteToReject = approveModalQuote;
                setApproveModalQuote(null);
                if (quoteToReject) {
                  openRejectModal(quoteToReject);
                }
              }}
            >
              <Ionicons name="close-circle" size={24} color="#fff" />
              <Text style={styles.rejectButtonText}>Reject</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
          </SafeAreaView>
        </View>
      </Modal>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Sales</Text>
        <View style={styles.headerActions}>
          {viewMode === 'quotes' && (
            <ExportButtons
              endpoint="/quotes/export/excel"
              pdfEndpoint="/quotes/export/pdf"
              queryParams={{ status: activeTab === 'all' ? '' : activeTab }}
              filenamePrefix="Quotes"
              compact={true}
              showPdf={true}
              showExcel={true}
            />
          )}
          <TouchableOpacity onPress={() => { onRefresh(); if (viewMode === 'orders') fetchOrders(); if (viewMode === 'workorders') fetchWorkOrders(); }} style={styles.refreshButton}>
            <Ionicons name="refresh" size={24} color="#C5964A" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Quotes / Orders Toggle */}
      <View style={styles.modeToggleContainer}>
        <View style={styles.modeToggle}>
          <TouchableOpacity
            style={[styles.modeBtn, viewMode === 'quotes' && styles.modeBtnActive]}
            onPress={() => setViewMode('quotes')}
          >
            <Ionicons name="document-text-outline" size={14} color={viewMode === 'quotes' ? '#C5964A' : '#94A3B8'} />
            <Text style={[styles.modeBtnText, viewMode === 'quotes' && styles.modeBtnTextActive]}>
              {docLabel}s
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.modeBtn, viewMode === 'orders' && styles.modeBtnActive]}
            onPress={() => { setViewMode('orders'); if (orders.length === 0) fetchOrders(); }}
          >
            <Ionicons name="cube-outline" size={14} color={viewMode === 'orders' ? '#C5964A' : '#94A3B8'} />
            <Text style={[styles.modeBtnText, viewMode === 'orders' && styles.modeBtnTextActive]}>Orders</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ORDERS VIEW with SO/WO sub-toggle */}
      {viewMode === 'orders' ? (
        <OrdersAndWOView
          orders={orders}
          ordersLoading={ordersLoading}
          fetchOrders={fetchOrders}
          workOrders={workOrders}
          woLoading={woLoading}
          fetchWorkOrders={fetchWorkOrders}
          isAdmin={isAdmin}
        />
      ) : (
      <>
      {/* Search Bar - Admin Only */}
      {isAdmin && (
        <View style={styles.searchContainer}>
          <View style={styles.searchInputWrapper}>
            <Ionicons name="search-outline" size={20} color="#94A3B8" style={styles.searchIcon} />
            <TextInput
              style={styles.searchInput}
              placeholder="Search by name, quote #, company, GST..."
              placeholderTextColor="#94A3B8"
              value={searchQuery}
              onChangeText={setSearchQuery}
              autoCapitalize="none"
              autoCorrect={false}
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')} style={styles.searchClearBtn}>
                <Ionicons name="close-circle" size={20} color="#94A3B8" />
              </TouchableOpacity>
            )}
          </View>
          {searchQuery.length > 0 && (
            <View style={styles.searchResultsRow}>
              <Text style={styles.searchResultCount}>
                {getFilteredQuotes().length} result{getFilteredQuotes().length !== 1 ? 's' : ''} found
              </Text>
              {getFilteredQuotes().length > 0 && (
                <TouchableOpacity 
                  style={styles.exportResultsBtn}
                  onPress={() => exportSearchResults('quotes')}
                >
                  <Ionicons name="download-outline" size={16} color="#960018" />
                  <Text style={styles.exportResultsBtnText}>Export</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>
      )}

      {/* Admin Filter Tabs */}
      {isAdmin && (
        <View style={styles.filterTabs}>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'all' && styles.filterTabActive]}
            onPress={() => setActiveTab('all')}
          >
            <Text style={[styles.filterTabText, activeTab === 'all' && styles.filterTabTextActive]}>All</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'pending' && styles.filterTabActive]}
            onPress={() => setActiveTab('pending')}
          >
            <View style={styles.tabWithBadge}>
              <Text style={[styles.filterTabText, activeTab === 'pending' && styles.filterTabTextActive]}>
                RFQ {pendingRfqCount > 0 && `(${pendingRfqCount})`}
              </Text>
              {/* Unread badge */}
              {unreadCount > 0 && (
                <View style={styles.unreadBadge}>
                  <Text style={styles.unreadBadgeText}>{unreadCount > 99 ? '99+' : unreadCount}</Text>
                </View>
              )}
            </View>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'approved' && styles.filterTabActive]}
            onPress={() => setActiveTab('approved')}
          >
            <Text style={[styles.filterTabText, activeTab === 'approved' && styles.filterTabTextActive]}>Approved</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'rejected' && styles.filterTabActive]}
            onPress={() => setActiveTab('rejected')}
          >
            <Text style={[styles.filterTabText, activeTab === 'rejected' && styles.filterTabTextActive]}>Rejected</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Customer Filter Tabs */}
      {isCustomer && (
        <View style={styles.filterTabs}>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'all' && styles.filterTabActive]}
            onPress={() => setActiveTab('all')}
          >
            <Text style={[styles.filterTabText, activeTab === 'all' && styles.filterTabTextActive]}>All</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'active' && styles.filterTabActive]}
            onPress={() => setActiveTab('active')}
          >
            <Text style={[styles.filterTabText, activeTab === 'active' && styles.filterTabTextActive]}>Active RFQs</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterTab, activeTab === 'history' && styles.filterTabActive]}
            onPress={() => setActiveTab('history')}
          >
            <Text style={[styles.filterTabText, activeTab === 'history' && styles.filterTabTextActive]}>History</Text>
          </TouchableOpacity>
        </View>
      )}

      <FlatList
        data={getFilteredQuotes()}
        renderItem={renderQuote}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#960018" />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>No {docLabel.toLowerCase()}s yet</Text>
            <Text style={styles.emptySubtext}>
              Go to Calculator tab to create your first {docLabel.toLowerCase()}
            </Text>
          </View>
        }
      />

      {/* End of Quotes View */}
      </>
      )}

      {/* Quote Detail Modal - Using extracted component */}
      <QuoteDetailModal
        visible={!!selectedQuote && !approveModalQuote}
        quote={selectedQuote}
        isAdmin={isAdmin}
        isCustomer={isCustomer}
        docLabel={docLabel}
        onClose={() => setSelectedQuote(null)}
        editableProducts={editableProducts}
        useItemDiscount={useItemDiscount}
        setUseItemDiscount={setUseItemDiscount}
        totalDiscountPercent={totalDiscountPercent}
        setTotalDiscountPercent={setTotalDiscountPercent}
        itemDiscounts={itemDiscounts}
        setItemDiscounts={setItemDiscounts}
        editPackingType={editPackingType}
        setEditPackingType={setEditPackingType}
        customPackingPercent={customPackingPercent}
        setCustomPackingPercent={setCustomPackingPercent}
        editDeliveryPincode={editDeliveryPincode}
        customFreightAmount={customFreightAmount}
        setCustomFreightAmount={setCustomFreightAmount}
        pincodeValid={pincodeValid}
        pincodeError={pincodeError}
        freightLoading={freightLoading}
        commercialTermsOptions={commercialTermsOptions}
        selectedPaymentTerms={selectedPaymentTerms}
        setSelectedPaymentTerms={setSelectedPaymentTerms}
        selectedFreightTerms={selectedFreightTerms}
        setSelectedFreightTerms={setSelectedFreightTerms}
        selectedColorFinish={selectedColorFinish}
        setSelectedColorFinish={setSelectedColorFinish}
        selectedDeliveryTimeline={selectedDeliveryTimeline}
        setSelectedDeliveryTimeline={setSelectedDeliveryTimeline}
        onPincodeChange={handlePincodeChange}
        onUpdateProductQuantity={updateProductQuantity}
        onDeleteProduct={deleteProduct}
        onApprove={(quote) => confirmApproveRfq(quote)}
        onReject={openRejectModal}
        onEdit={openEditQuote}
        onViewHistory={fetchRevisionHistory}
        onExportPdf={exportToPdf}
        onDownloadAttachment={downloadAttachment}
        onDownloadAllAsZip={downloadAllAsZip}
        approvingId={approvingId}
        generatingPdf={generatingPdf}
        loadingHistory={loadingHistory}
        getStatusColor={getStatusColor}
        getStatusIcon={getStatusIcon}
        formatDate={formatDate}
        calculateTotalDiscount={calculateTotalDiscount}
        calculateApprovalTotal={calculateApprovalTotal}
      />

      {/* Reject Reason Modal - Using extracted component */}
      <RejectReasonModal
        visible={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        quote={rejectingQuote}
        selectedReason={selectedRejectReason}
        setSelectedReason={setSelectedRejectReason}
        onConfirmReject={confirmRejectRfq}
        isRejecting={rejectingId === rejectingQuote?.id}
      />

      {/* Approval Success Modal - Using extracted component */}
      <ApprovalSuccessModal
        visible={showApprovalSuccess}
        onClose={() => setShowApprovalSuccess(false)}
        quoteNumber={approvedQuoteNumber}
        onViewApproved={() => {
          setShowApprovalSuccess(false);
          setActiveTab('approved');
        }}
      />


      {/* Edit Quote Modal - Using extracted component */}
      <EditQuoteModal
        visible={!!editingQuote}
        quote={editingQuote}
        docLabel={docLabel}
        onClose={() => setEditingQuote(null)}
        editedProducts={editedProducts}
        useItemDiscounts={useItemDiscounts}
        setUseItemDiscounts={setUseItemDiscounts}
        bulkDiscountPercent={bulkDiscountPercent}
        setBulkDiscountPercent={setBulkDiscountPercent}
        editedDiscount={editedDiscount}
        setEditedDiscount={setEditedDiscount}
        editedFreight={editedFreight}
        setEditedFreight={setEditedFreight}
        editedPackingType={editedPackingType}
        setEditedPackingType={setEditedPackingType}
        customPackingPercent={customPackingPercent}
        setCustomPackingPercent={setCustomPackingPercent}
        commercialTermsOptions={commercialTermsOptions}
        selectedPaymentTerms={selectedPaymentTerms}
        setSelectedPaymentTerms={setSelectedPaymentTerms}
        selectedFreightTerms={selectedFreightTerms}
        setSelectedFreightTerms={setSelectedFreightTerms}
        selectedColorFinish={selectedColorFinish}
        setSelectedColorFinish={setSelectedColorFinish}
        selectedDeliveryTimeline={selectedDeliveryTimeline}
        setSelectedDeliveryTimeline={setSelectedDeliveryTimeline}
        onUpdateProductQuantity={updateEditedProductQuantity}
        onUpdateProductItemDiscount={updateProductItemDiscount}
        onApplyDiscountToAllItems={applyDiscountToAllItems}
        onSaveAndMail={saveAndMailQuote}
        calculateEditedTotal={calculateEditedTotal}
        savingEdit={savingEdit}
      />

      {/* Revision History Modal - Using extracted component */}
      <RevisionHistoryModal
        visible={showRevisionHistory}
        onClose={() => setShowRevisionHistory(false)}
        history={revisionHistory}
        formatDate={formatRevisionDate}
      />

      {/* Convert to SO Modal with Delivery Date */}
      <Modal visible={showConvertSO} animationType="slide" transparent>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
          <View style={{ backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 22 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <Text style={{ fontSize: 18, fontWeight: '700', color: '#0F172A' }}>Convert to Sales Order</Text>
              <TouchableOpacity onPress={() => setShowConvertSO(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
            </View>
            {convertQuote && <Text style={{ fontSize: 14, color: '#C5964A', fontWeight: '600', marginBottom: 16 }}>{convertQuote.quote_number} — {convertQuote.customer_name}</Text>}
            <Text style={{ fontSize: 12, fontWeight: '600', color: '#C5964A', letterSpacing: 0.5, marginBottom: 6 }}>Delivery Date *</Text>
            {Platform.OS === 'web' ? (
              <input
                type="date"
                value={deliveryDate}
                onChange={(e: any) => setDeliveryDate(e.target.value)}
                style={{ backgroundColor: 'rgba(241,245,249,0.8)', border: '1px solid rgba(226,232,240,0.5)', borderRadius: 12, padding: '12px 14px', fontSize: 15, color: '#0F172A', width: '100%', fontFamily: 'inherit' } as any}
              />
            ) : (
              <TextInput
                style={{ backgroundColor: 'rgba(241,245,249,0.8)', borderWidth: 1, borderColor: 'rgba(226,232,240,0.5)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#0F172A' }}
                value={deliveryDate}
                onChangeText={setDeliveryDate}
                placeholder="DD-MM-YYYY"
              />
            )}
            <Pressable
              style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#C5964A', borderRadius: 14, paddingVertical: 15, marginTop: 18 }}
              onPress={async () => {
                if (!deliveryDate) { Alert.alert('Error', 'Please enter delivery date'); return; }
                try {
                  const quoteId = convertQuote?.id || convertQuote?._id;
                  const res = await api.post(`/orders/from-quote/${quoteId}`, { delivery_date: deliveryDate });
                  Alert.alert('Success', res.data.message);
                  setShowConvertSO(false);
                  fetchQuotes();
                } catch (e: any) {
                  Alert.alert('Error', e.response?.data?.detail || 'Failed to convert');
                }
              }}
            >
              <Ionicons name="cube" size={18} color="#fff" />
              <Text style={{ color: '#fff', fontSize: 15, fontWeight: '700' }}>Create Sales Order</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F0F4F8',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F0F4F8',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#64748B',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 56,
    paddingBottom: 20,
    paddingHorizontal: 20,
    backgroundColor: '#0F172A',
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
  modeToggleContainer: {
    paddingHorizontal: 14,
    paddingTop: 14,
  },
  modeToggle: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.6)',
    borderRadius: 10,
    padding: 3,
  },
  modeBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  modeBtnActive: {
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  modeBtnText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#94A3B8',
  },
  modeBtnTextActive: {
    color: '#C5964A',
    fontWeight: '700',
  },
  refreshButton: {
    padding: 8,
  },
  listContainer: {
    padding: 16,
    paddingBottom: 100,
  },
  quoteCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  quoteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  quoteInfo: {
    flex: 1,
  },
  quoteId: {
    fontSize: 16,
    fontWeight: '700',
    color: '#960018',
  },
  quoteIdRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  rfqRefInCard: {
    fontSize: 11,
    color: '#0066cc',
    fontWeight: '500',
  },
  unreadDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#EF4444',
  },
  unreadQuoteCard: {
    borderLeftWidth: 4,
    borderLeftColor: '#EF4444',
  },
  unreadQuoteId: {
    fontWeight: '800',
  },
  quoteDate: {
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
  quoteFooter: {
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
    fontWeight: '600',
    marginTop: 2,
  },
  totalPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContainer: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    width: '100%',
    maxHeight: '95%',
    minHeight: '85%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 20,
  },
  fullScreenEditContainer: {
    flex: 1,
    backgroundColor: '#fff',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 99999,
  },
  editQuoteModalContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 20,
    backgroundColor: '#1a1f36',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  rfqReference: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 2,
    fontWeight: '500',
  },
  modalScroll: {
    padding: 16,
  },
  detailSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 12,
  },
  statusBadgeLarge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 8,
  },
  statusTextLarge: {
    fontSize: 14,
    fontWeight: '700',
  },
  productCard: {
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  productName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
  },
  productDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  productQty: {
    fontSize: 14,
    color: '#666',
  },
  productPrice: {
    fontSize: 15,
    fontWeight: '600',
    color: '#960018',
  },
  specsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
    gap: 8,
  },
  specText: {
    fontSize: 12,
    color: '#666',
    backgroundColor: '#E0E0E0',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  remarkContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 10,
    padding: 10,
    backgroundColor: '#FEF3C7',
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#F59E0B',
  },
  remarkText: {
    flex: 1,
    fontSize: 13,
    color: '#92400E',
    lineHeight: 18,
  },
  pricingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  pricingLabel: {
    fontSize: 14,
    color: '#666',
  },
  pricingValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  pricingLabelGreen: {
    fontSize: 14,
    color: '#4CAF50',
  },
  pricingValueGreen: {
    fontSize: 14,
    fontWeight: '500',
    color: '#4CAF50',
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    marginTop: 8,
    paddingTop: 12,
  },
  totalLabel2: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
  },
  totalValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  deliveryText: {
    fontSize: 14,
    color: '#333',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  infoLabel: {
    fontSize: 14,
    color: '#64748B',
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
  },
  notesText: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
  },
  dateText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
  },
  exportButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 16,
    gap: 6,
    flex: 1,
    minWidth: 75,
    borderWidth: 1.5,
    borderColor: '#960018',
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  exportButtonText: {
    color: '#960018',
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'center',
  },
  // Detail Actions Row - Modern Card-Style Buttons
  detailActionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 24,
    marginBottom: 30,
    paddingHorizontal: 4,
  },
  editQuoteButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 16,
    gap: 6,
    flex: 1,
    minWidth: 80,
    borderWidth: 1.5,
    borderColor: '#4CAF50',
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  editQuoteButtonText: {
    color: '#4CAF50',
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'center',
  },
  // Edit Quote Modal Styles
  editProductRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  editProductInfo: {
    flex: 1,
  },
  editProductName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  editProductPrice: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  qtyInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  qtyLabel: {
    fontSize: 14,
    color: '#666',
  },
  qtyInput: {
    width: 70,
    backgroundColor: '#F5F5F5',
    borderWidth: 1,
    borderColor: '#DDD',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    textAlign: 'center',
  },
  discountInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  discountInput: {
    width: 100,
    backgroundColor: '#F5F5F5',
    borderWidth: 1,
    borderColor: '#4CAF50',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 18,
    textAlign: 'center',
  },
  discountPercent: {
    fontSize: 18,
    fontWeight: '600',
    color: '#4CAF50',
  },
  saveEditButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 20,
    marginBottom: 30,
    gap: 10,
  },
  saveEditButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  // Filter Tabs
  filterTabs: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 12,
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 4,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  filterTab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  filterTabActive: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  filterTabText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#64748B',
  },
  filterTabTextActive: {
    color: '#960018',
    fontWeight: '600',
  },
  tabWithBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  unreadBadge: {
    backgroundColor: '#EF4444',
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  unreadBadgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  // Approve Button - RED (before approval)
  approveButtonRed: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#C41E3A',
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  // Approved Badge - GREEN (after approval)
  approvedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  approveButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  // Save Revision Button - Blue
  saveRevisionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2196F3',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 12,
    gap: 8,
  },
  saveAndMailButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 16,
    gap: 8,
  },
  revisionLabel: {
    fontSize: 14,
    color: '#FF9500',
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 12,
  },
  // Attachments Section Styles
  attachmentsSection: {
    marginTop: 20,
    padding: 16,
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  attachmentsSectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1E293B',
    marginBottom: 12,
  },
  productAttachments: {
    marginBottom: 12,
  },
  productAttachmentLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 8,
  },
  attachmentDownloadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginBottom: 8,
    gap: 8,
  },
  attachmentDownloadText: {
    flex: 1,
    fontSize: 14,
    color: '#334155',
  },
  downloadAllZipBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#960018',
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 12,
    gap: 10,
  },
  downloadAllZipText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  pendingPriceMessage: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    padding: 16,
    borderRadius: 12,
    gap: 12,
  },
  pendingPriceText: {
    flex: 1,
    fontSize: 14,
    color: '#92400E',
    lineHeight: 20,
  },
  // Approval Success Modal Styles
  successModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  successModalContent: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 30,
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 10,
  },
  successIconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#E8F5E9',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4CAF50',
    marginBottom: 10,
    textAlign: 'center',
  },
  successMessage: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
    textAlign: 'center',
  },
  successQuoteNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
    marginBottom: 15,
    textAlign: 'center',
  },
  successSubtext: {
    fontSize: 14,
    color: '#999',
    marginBottom: 25,
    textAlign: 'center',
  },
  successButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    paddingHorizontal: 30,
    borderRadius: 10,
    width: '100%',
    marginBottom: 12,
  },
  successButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    textAlign: 'center',
  },
  successCloseButton: {
    paddingVertical: 10,
  },
  successCloseText: {
    color: '#666',
    fontSize: 14,
    fontWeight: '600',
  },
  // Search Bar Styles
  searchContainer: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  searchInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  searchIcon: {
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 15,
    color: '#0F172A',
  },
  searchClearBtn: {
    padding: 4,
  },
  searchResultCount: {
    marginTop: 8,
    fontSize: 13,
    color: '#64748B',
    textAlign: 'center',
  },
  searchResultsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  exportResultsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF5F5',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 4,
    borderWidth: 1,
    borderColor: '#960018',
  },
  exportResultsBtnText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#960018',
  },
  // Discount mode toggle styles
  discountModeToggle: {
    flexDirection: 'row',
    backgroundColor: '#F1F5F9',
    borderRadius: 12,
    padding: 4,
    gap: 4,
  },
  modeButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    gap: 6,
  },
  modeButtonActive: {
    backgroundColor: '#960018',
  },
  modeButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  modeButtonTextActive: {
    color: '#fff',
  },
  // Edit product card styles
  editProductCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  editProductHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  editProductInputs: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  inputGroup: {
    flex: 1,
    minWidth: 70,
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#64748B',
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  smallInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    fontWeight: '600',
    color: '#0F172A',
    textAlign: 'center',
  },
  calculatedValue: {
    fontSize: 13,
    fontWeight: '500',
    color: '#475569',
    paddingVertical: 8,
  },
  calculatedValueBold: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
    paddingVertical: 8,
  },
  // Bulk discount styles
  bulkDiscountSection: {
    backgroundColor: '#FFF5F5',
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#960018',
  },
  bulkDiscountLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#960018',
    marginBottom: 8,
  },
  bulkDiscountRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  bulkDiscountInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    width: 70,
    textAlign: 'center',
  },
  bulkDiscountPercent: {
    fontSize: 16,
    fontWeight: '600',
    color: '#960018',
  },
  bulkApplyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#960018',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
    marginLeft: 'auto',
  },
  bulkApplyButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#fff',
  },
  // Approve Modal Styles
  approveQuoteNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
    marginBottom: 4,
  },
  approveCustomerName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginBottom: 4,
  },
  approveSubtotal: {
    fontSize: 14,
    color: '#666',
  },
  freightInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 16,
    marginBottom: 12,
  },
  freightInputLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  freightInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  freightInput: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    fontWeight: '600',
    color: '#0F172A',
    width: 100,
    textAlign: 'center',
  },
  freightInputSuffix: {
    fontSize: 18,
    fontWeight: '600',
    color: '#960018',
  },
  freightInputPrefix: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
    marginRight: 4,
  },
  calculatedFreightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F1F5F9',
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
  },
  calculatedFreightLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  calculatedFreightValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  approveConfirmButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 16,
    gap: 6,
    flex: 1,
    minWidth: 75,
    borderWidth: 1.5,
    borderColor: '#22C55E',
    shadowColor: '#22C55E',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  approveConfirmButtonText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#22C55E',
    textAlign: 'center',
  },
  // New styles for Edit RFQ modal
  approveCompanyName: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  editProductItem: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#960018',
  },
  editProductHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  editProductName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  editProductQty: {
    fontSize: 14,
    fontWeight: '600',
    color: '#960018',
  },
  editProductDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  editProductPrice: {
    fontSize: 13,
    color: '#666',
  },
  editProductTotal: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  editProductRemarks: {
    fontSize: 12,
    color: '#888',
    fontStyle: 'italic',
    marginTop: 4,
  },
  subtotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  subtotalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  subtotalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#960018',
  },
  packingOptions: {
    gap: 8,
  },
  packingOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    gap: 10,
  },
  packingOptionActive: {
    backgroundColor: '#fff5f5',
    borderColor: '#960018',
  },
  packingOptionText: {
    fontSize: 14,
    color: '#666',
  },
  packingOptionTextActive: {
    color: '#960018',
    fontWeight: '600',
  },
  approveRejectButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20,
    marginBottom: 20,
  },
  rejectButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 16,
    gap: 6,
    flex: 1,
    minWidth: 75,
    borderWidth: 1.5,
    borderColor: '#EF4444',
    shadowColor: '#EF4444',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  rejectButtonText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#EF4444',
    textAlign: 'center',
  },
  // Reject Modal styles
  rejectModalSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
    textAlign: 'center',
  },
  rejectReasonOptions: {
    gap: 12,
  },
  rejectReasonOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    gap: 12,
  },
  rejectReasonOptionActive: {
    backgroundColor: '#fff5f5',
    borderColor: '#960018',
  },
  rejectReasonText: {
    fontSize: 14,
    color: '#333',
    flex: 1,
  },
  rejectReasonTextActive: {
    color: '#960018',
    fontWeight: '600',
  },
  confirmRejectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DC3545',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    marginTop: 24,
    marginBottom: 20,
  },
  confirmRejectButtonDisabled: {
    backgroundColor: '#ccc',
  },
  confirmRejectButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  // Rejected badge style
  rejectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DC3545',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  // Field label and editable input styles
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  editableInput: {
    backgroundColor: '#f8f9fa',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  inputError: {
    borderColor: '#DC3545',
    borderWidth: 2,
  },
  errorText: {
    color: '#DC3545',
    fontSize: 12,
    marginTop: 4,
  },
  customPackingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    gap: 12,
  },
  customPackingLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  // Editable product styles
  editableProductCard: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#960018',
  },
  editableProductHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  deleteProductButton: {
    padding: 4,
  },
  editableProductRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  qtyEditContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  qtyLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  qtyButton: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#e0e0e0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  qtyInput: {
    width: 50,
    height: 32,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    textAlign: 'center',
    fontSize: 14,
    backgroundColor: '#fff',
  },
  // Discount section styles
  itemDiscountContainer: {
    marginTop: 12,
    gap: 10,
  },
  itemDiscountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    padding: 10,
    borderRadius: 8,
  },
  itemDiscountName: {
    flex: 1,
    fontSize: 14,
    color: '#333',
    marginRight: 12,
  },
  // Revision History styles
  historyButton: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 16,
    gap: 6,
    flex: 1,
    minWidth: 75,
    borderWidth: 1.5,
    borderColor: '#64748B',
    shadowColor: '#64748B',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  historyButtonText: {
    color: '#64748B',
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'center',
  },
  revisionEntry: {
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  revisionHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  revisionTimeline: {
    alignItems: 'center',
    width: 20,
  },
  revisionDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#ddd',
    borderWidth: 2,
    borderColor: '#fff',
  },
  revisionDotActive: {
    backgroundColor: '#960018',
  },
  revisionLine: {
    width: 2,
    flex: 1,
    backgroundColor: '#ddd',
    marginTop: 4,
    minHeight: 40,
  },
  revisionDate: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  revisionUser: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  revisionActionBadge: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  revisionActionText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1565C0',
  },
  revisionChanges: {
    marginTop: 12,
    marginLeft: 32,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
  },
  revisionChangeRow: {
    marginBottom: 8,
  },
  revisionChangeLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    marginBottom: 4,
  },
  revisionChangeValues: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  revisionOldValue: {
    fontSize: 13,
    color: '#C62828',
    textDecorationLine: 'line-through',
  },
  revisionNewValue: {
    fontSize: 13,
    color: '#2E7D32',
    fontWeight: '500',
  },
  revisionSummary: {
    marginTop: 8,
    marginLeft: 32,
    fontSize: 13,
    color: '#666',
    fontStyle: 'italic',
  },
  closeHistoryButton: {
    backgroundColor: '#960018',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 16,
    marginHorizontal: 16,
    marginBottom: 8,
  },
  closeHistoryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  // Commercial Terms Styles
  commercialTermRow: {
    marginBottom: 12,
  },
  commercialTermLabel: {
    fontSize: 13,
    color: '#333',
    marginBottom: 6,
    fontWeight: '500',
  },
  commercialTermDropdown: {
    flexDirection: 'row',
  },
  commercialTermOption: {
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginRight: 8,
    minWidth: 100,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  commercialTermOptionActive: {
    backgroundColor: '#960018',
    borderColor: '#960018',
  },
  commercialTermOptionText: {
    fontSize: 12,
    color: '#333',
    textAlign: 'center',
  },
  commercialTermOptionTextActive: {
    color: '#fff',
    fontWeight: '500',
  },
  commercialTermFixed: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
    fontStyle: 'italic',
    flex: 1,
  },
  // Dropdown styles for Commercial Terms
  dropdownRow: {
    marginBottom: 16,
  },
  dropdownLabel: {
    fontSize: 14,
    color: '#333',
    marginBottom: 8,
    fontWeight: '500',
  },
  dropdownContainer: {
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  fixedTermText: {
    fontSize: 13,
    color: '#666',
    fontStyle: 'italic',
    marginTop: 4,
  },
});
