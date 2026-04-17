import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, ActivityIndicator, TouchableOpacity, Alert, TextInput, Modal, FlatList, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { ExportButtons } from '../../components/shared/ExportButtons';

type Tab = 'dashboard' | 'stock' | 'po' | 'suppliers' | 'alerts';

export default function StoreScreen() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [tab, setTab] = useState<Tab>('dashboard');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboard, setDashboard] = useState<any>(null);
  const [stockItems, setStockItems] = useState<any[]>([]);
  const [pos, setPos] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  // Modals
  const [showAddItem, setShowAddItem] = useState(false);
  const [showAddPO, setShowAddPO] = useState(false);
  const [showAddSupplier, setShowAddSupplier] = useState(false);
  const [showQC, setShowQC] = useState(false);
  const [showIssue, setShowIssue] = useState(false);
  const [selectedPO, setSelectedPO] = useState<any>(null);
  // Form state
  const [newItem, setNewItem] = useState({ name: '', category: 'pipe', unit_purchase: 'meters', unit_bom: 'kg', reorder_level: '' });
  const [newSupplier, setNewSupplier] = useState({ name: '', contact_person: '', phone: '', gst_number: '', city: '', payment_terms: '' });
  const [newPO, setNewPO] = useState({ supplier_id: '', items: [{ stock_item_id: '', qty: '', rate: '' }] });
  const [qcData, setQcData] = useState({ accepted_qty: '', rejected_qty: '', reason: '' });
  const [qcItemIndex, setQcItemIndex] = useState(0);
  const [issueItems, setIssueItems] = useState<any[]>([]);
  const [issueWOId, setIssueWOId] = useState('');
  const [workOrders, setWorkOrders] = useState<any[]>([]);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [dashRes, itemsRes, posRes, suppRes, alertRes] = await Promise.all([
        api.get('/store/dashboard'), api.get('/store/items'),
        api.get('/store/purchase-orders'), api.get('/suppliers'),
        api.get('/store/alerts'),
      ]);
      setDashboard(dashRes.data);
      setStockItems(itemsRes.data.items || []);
      setPos(posRes.data.purchase_orders || []);
      setSuppliers(suppRes.data.suppliers || []);
      setAlerts(alertRes.data.alerts || []);
    } catch (e) { console.log('Store fetch error', e); }
    finally { setLoading(false); }
  };

  const onRefresh = async () => { setRefreshing(true); await fetchAll(); setRefreshing(false); };

  const createStockItem = async () => {
    if (!newItem.name) { Alert.alert('Error', 'Name required'); return; }
    try {
      await api.post('/store/items', { ...newItem, reorder_level: parseFloat(newItem.reorder_level) || 0, current_stock: 0 });
      setShowAddItem(false); setNewItem({ name: '', category: 'pipe', unit_purchase: 'meters', unit_bom: 'kg', reorder_level: '' });
      fetchAll(); Alert.alert('Success', 'Stock item created');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const createSupplier = async () => {
    if (!newSupplier.name) { Alert.alert('Error', 'Name required'); return; }
    try {
      await api.post('/suppliers', newSupplier);
      setShowAddSupplier(false); setNewSupplier({ name: '', contact_person: '', phone: '', gst_number: '', city: '', payment_terms: '' });
      fetchAll(); Alert.alert('Success', 'Supplier created');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const createPO = async () => {
    if (!newPO.supplier_id || !newPO.items[0]?.stock_item_id) { Alert.alert('Error', 'Select supplier and item'); return; }
    try {
      const items = newPO.items.map(i => ({ stock_item_id: i.stock_item_id, qty: parseFloat(i.qty) || 0, rate: parseFloat(i.rate) || 0 }));
      await api.post('/store/purchase-orders', { supplier_id: newPO.supplier_id, items });
      setShowAddPO(false); setNewPO({ supplier_id: '', items: [{ stock_item_id: '', qty: '', rate: '' }] });
      fetchAll(); Alert.alert('Success', 'Purchase Order created');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const processQC = async (status: string) => {
    if (!selectedPO) return;
    try {
      await api.post('/store/qc', { po_id: selectedPO.id, item_index: qcItemIndex, status, accepted_qty: parseFloat(qcData.accepted_qty) || 0, rejected_qty: parseFloat(qcData.rejected_qty) || 0, reason: qcData.reason });
      setShowQC(false); setQcData({ accepted_qty: '', rejected_qty: '', reason: '' });
      fetchAll(); Alert.alert('Success', `QC ${status}`);
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const issueStock = async () => {
    if (!issueWOId || issueItems.length === 0) { Alert.alert('Error', 'Select WO and items'); return; }
    try {
      await api.post('/store/issue', { wo_id: issueWOId, items: issueItems.filter(i => i.qty > 0).map(i => ({ stock_item_id: i.stock_item_id, qty: parseFloat(i.qty) })) });
      setShowIssue(false); fetchAll(); Alert.alert('Success', 'Stock issued');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  if (!isAdmin) return <View style={s.center}><Ionicons name="lock-closed" size={48} color="#94A3B8" /><Text style={s.centerText}>Admin access required</Text></View>;
  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#C5964A" /></View>;

  return (
    <View style={s.container}>
      <View style={s.header}>
        <View><Text style={s.headerTitle}>Store</Text><Text style={s.headerSub}>Inventory & Purchase Management</Text></View>
        <TouchableOpacity onPress={onRefresh}><Ionicons name="refresh" size={22} color="#C5964A" /></TouchableOpacity>
      </View>

      {/* Tab Bar */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxHeight: 44, marginHorizontal: 14, marginTop: 12 }}>
        {([['dashboard','grid-outline','Dashboard'],['stock','layers-outline','Stock'],['po','cart-outline','POs'],['suppliers','business-outline','Suppliers'],['alerts','alert-circle-outline','Alerts']] as const).map(([key, icon, label]) => (
          <TouchableOpacity key={key} style={[s.tabBtn, tab === key && s.tabBtnActive]} onPress={() => setTab(key as Tab)}>
            <Ionicons name={icon as any} size={15} color={tab === key ? '#C5964A' : '#94A3B8'} />
            <Text style={[s.tabText, tab === key && s.tabTextActive]}>{label}{key === 'alerts' && alerts.length > 0 ? ` (${alerts.length})` : ''}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 14 }} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#C5964A']} />}>

        {/* DASHBOARD */}
        {tab === 'dashboard' && dashboard && (
          <>
            <View style={s.statsRow}>
              <View style={[s.statCard, { borderLeftColor: '#3B82F6' }]}><Text style={s.statNum}>{dashboard.total_items}</Text><Text style={s.statLabel}>Items</Text></View>
              <View style={[s.statCard, { borderLeftColor: '#C5964A' }]}><Text style={s.statNum}>{dashboard.total_pos}</Text><Text style={s.statLabel}>POs</Text></View>
              <View style={[s.statCard, { borderLeftColor: '#F59E0B' }]}><Text style={s.statNum}>{dashboard.pending_pos}</Text><Text style={s.statLabel}>Pending</Text></View>
              <View style={[s.statCard, { borderLeftColor: '#EF4444' }]}><Text style={s.statNum}>{dashboard.low_stock_alerts}</Text><Text style={s.statLabel}>Low Stock</Text></View>
            </View>
            <Text style={s.sectionTitle}>Recent Transactions</Text>
            {(dashboard.recent_transactions || []).map((t: any, i: number) => (
              <View key={i} style={s.txnRow}>
                <Ionicons name={t.type === 'in' ? 'arrow-down-circle' : 'arrow-up-circle'} size={18} color={t.type === 'in' ? '#10B981' : '#EF4444'} />
                <View style={{ flex: 1, marginLeft: 8 }}>
                  <Text style={s.txnName}>{t.stock_item_name}</Text>
                  <Text style={s.txnRef}>{t.reference} | {t.at?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2})/, '$3-$2-$1')}</Text>
                </View>
                <Text style={[s.txnQty, { color: t.type === 'in' ? '#10B981' : '#EF4444' }]}>{t.type === 'in' ? '+' : '-'}{t.qty}</Text>
              </View>
            ))}
          </>
        )}

        {/* STOCK */}
        {tab === 'stock' && (
          <>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Text style={s.sectionTitle}>Stock Items ({stockItems.length})</Text>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <ExportButtons endpoint="/store/export/stock" filenamePrefix="Stock" compact showExcel showPdf={false} />
                <Pressable style={s.actionBtn} onPress={() => setShowAddItem(true)}><Ionicons name="add" size={16} color="#C5964A" /><Text style={s.actionText}>Add Item</Text></Pressable>
                <Pressable style={s.actionBtn} onPress={async () => { try { const res = await api.get('/work-orders'); setWorkOrders(res.data.work_orders || []); setIssueItems(stockItems.map(i => ({ stock_item_id: i.id, name: i.name, qty: '' }))); setShowIssue(true); } catch {} }}><Ionicons name="arrow-up-circle-outline" size={16} color="#8B5CF6" /><Text style={[s.actionText, { color: '#8B5CF6' }]}>Issue</Text></Pressable>
              </View>
            </View>
            {stockItems.map((item: any) => (
              <View key={item.id} style={s.card}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <View style={{ flex: 1 }}><Text style={s.cardTitle}>{item.name}</Text><Text style={s.cardMeta}>{item.category} | {item.unit_purchase}</Text></View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Text style={[s.stockQty, item.current_stock <= (item.reorder_level || 0) && item.reorder_level > 0 ? { color: '#EF4444' } : {}]}>{item.current_stock} {item.unit_purchase}</Text>
                    {item.reorder_level > 0 && <Text style={s.reorderText}>Reorder: {item.reorder_level}</Text>}
                  </View>
                </View>
              </View>
            ))}
          </>
        )}

        {/* PURCHASE ORDERS */}
        {tab === 'po' && (
          <>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Text style={s.sectionTitle}>Purchase Orders ({pos.length})</Text>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <ExportButtons endpoint="/store/export/purchase-orders" filenamePrefix="POs" compact showExcel showPdf={false} />
                <Pressable style={s.actionBtn} onPress={() => setShowAddPO(true)}><Ionicons name="add" size={16} color="#C5964A" /><Text style={s.actionText}>New PO</Text></Pressable>
              </View>
            </View>
            {pos.map((po: any) => (
              <TouchableOpacity key={po.id} style={s.card} onPress={() => { setSelectedPO(po); setQcItemIndex(0); setShowQC(true); }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <View><Text style={s.cardTitle}>{po.po_number}</Text><Text style={s.cardMeta}>{po.supplier_name} | {po.created_at?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2})/, '$3-$2-$1')}</Text></View>
                  <View style={[s.statusBadge, { backgroundColor: po.status === 'received' ? '#D1FAE5' : po.status === 'ordered' ? '#DBEAFE' : '#FEF3C7' }]}>
                    <Text style={[s.statusText, { color: po.status === 'received' ? '#065F46' : po.status === 'ordered' ? '#1E40AF' : '#92400E' }]}>{po.status}</Text>
                  </View>
                </View>
                <View style={{ marginTop: 8 }}>
                  {(po.items || []).map((item: any, i: number) => (
                    <Text key={i} style={s.poItem}>{item.stock_item_name}: {item.qty_ordered} {item.unit} @ Rs.{item.rate} = Rs.{item.amount} | QC: {item.qc_status}</Text>
                  ))}
                </View>
                <Text style={s.poTotal}>Total: Rs.{po.total_amount?.toLocaleString()}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        {/* SUPPLIERS */}
        {tab === 'suppliers' && (
          <>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Text style={s.sectionTitle}>Suppliers ({suppliers.length})</Text>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <ExportButtons endpoint="/store/export/suppliers" filenamePrefix="Suppliers" compact showExcel showPdf={false} />
                <Pressable style={s.actionBtn} onPress={() => setShowAddSupplier(true)}><Ionicons name="add" size={16} color="#C5964A" /><Text style={s.actionText}>Add</Text></Pressable>
              </View>
            </View>
            {suppliers.map((sup: any) => (
              <View key={sup.id} style={s.card}>
                <Text style={s.cardTitle}>{sup.name}</Text>
                <Text style={s.cardMeta}>{sup.contact_person} | {sup.phone} | {sup.city}</Text>
                {sup.gst_number && <Text style={s.cardMeta}>GST: {sup.gst_number}</Text>}
                {sup.payment_terms && <Text style={s.cardMeta}>Terms: {sup.payment_terms}</Text>}
              </View>
            ))}
          </>
        )}

        {/* ALERTS */}
        {tab === 'alerts' && (
          <>
            <Text style={s.sectionTitle}>Low Stock Alerts ({alerts.length})</Text>
            {alerts.length === 0 ? <View style={s.emptyState}><Ionicons name="checkmark-circle" size={48} color="#10B981" /><Text style={s.emptyText}>All stock levels OK</Text></View> :
            alerts.map((a: any) => (
              <View key={a.id} style={[s.card, { borderLeftWidth: 3, borderLeftColor: '#EF4444' }]}>
                <Text style={s.cardTitle}>{a.name}</Text>
                <View style={{ flexDirection: 'row', gap: 16, marginTop: 4 }}>
                  <View><Text style={s.alertLabel}>Current</Text><Text style={[s.alertValue, { color: '#EF4444' }]}>{a.current_stock} {a.unit}</Text></View>
                  <View><Text style={s.alertLabel}>Reorder Level</Text><Text style={s.alertValue}>{a.reorder_level} {a.unit}</Text></View>
                  <View><Text style={s.alertLabel}>Deficit</Text><Text style={[s.alertValue, { color: '#EF4444', fontWeight: '800' }]}>{a.deficit} {a.unit}</Text></View>
                </View>
              </View>
            ))}
          </>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* Add Stock Item Modal */}
      <Modal visible={showAddItem} animationType="slide" transparent>
        <View style={s.modalOverlay}><View style={s.modal}>
          <View style={s.modalHead}><Text style={s.modalTitle}>Add Stock Item</Text><TouchableOpacity onPress={() => setShowAddItem(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          <Text style={s.label}>Name *</Text>
          <TextInput style={s.input} value={newItem.name} onChangeText={v => setNewItem({ ...newItem, name: v })} placeholder="Pipe 114.3mm x 4.5mm" />
          <Text style={s.label}>Category</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
            {['pipe','shaft','bearing','housing','seal','circlip','end_plate','hub','rubber_ring','grease','paint','other'].map(c => (
              <Pressable key={c} style={[s.chip, newItem.category === c && s.chipActive]} onPress={() => setNewItem({ ...newItem, category: c })}>
                <Text style={[s.chipText, newItem.category === c && s.chipTextActive]}>{c}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ flex: 1 }}><Text style={s.label}>Purchase Unit</Text>
              <ScrollView horizontal><View style={{ flexDirection: 'row', gap: 4 }}>
                {['meters','kg','nos','sqm','litres'].map(u => (<Pressable key={u} style={[s.chip, newItem.unit_purchase === u && s.chipActive]} onPress={() => setNewItem({ ...newItem, unit_purchase: u })}><Text style={[s.chipText, newItem.unit_purchase === u && s.chipTextActive]}>{u}</Text></Pressable>))}
              </View></ScrollView>
            </View>
          </View>
          <Text style={s.label}>Reorder Level</Text>
          <TextInput style={s.input} value={newItem.reorder_level} onChangeText={v => setNewItem({ ...newItem, reorder_level: v })} placeholder="50" keyboardType="numeric" />
          <Pressable style={s.saveBtn} onPress={createStockItem}><Ionicons name="add-circle" size={18} color="#fff" /><Text style={s.saveBtnText}>Create Item</Text></Pressable>
        </View></View>
      </Modal>

      {/* Add Supplier Modal */}
      <Modal visible={showAddSupplier} animationType="slide" transparent>
        <View style={s.modalOverlay}><View style={s.modal}>
          <View style={s.modalHead}><Text style={s.modalTitle}>Add Supplier</Text><TouchableOpacity onPress={() => setShowAddSupplier(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          <Text style={s.label}>Name *</Text><TextInput style={s.input} value={newSupplier.name} onChangeText={v => setNewSupplier({ ...newSupplier, name: v })} placeholder="Supplier name" />
          <Text style={s.label}>Contact Person</Text><TextInput style={s.input} value={newSupplier.contact_person} onChangeText={v => setNewSupplier({ ...newSupplier, contact_person: v })} placeholder="Contact" />
          <Text style={s.label}>Phone</Text><TextInput style={s.input} value={newSupplier.phone} onChangeText={v => setNewSupplier({ ...newSupplier, phone: v })} placeholder="Phone" keyboardType="phone-pad" />
          <Text style={s.label}>GST Number</Text><TextInput style={s.input} value={newSupplier.gst_number} onChangeText={v => setNewSupplier({ ...newSupplier, gst_number: v })} placeholder="GST" />
          <Text style={s.label}>City</Text><TextInput style={s.input} value={newSupplier.city} onChangeText={v => setNewSupplier({ ...newSupplier, city: v })} placeholder="City" />
          <Text style={s.label}>Payment Terms</Text><TextInput style={s.input} value={newSupplier.payment_terms} onChangeText={v => setNewSupplier({ ...newSupplier, payment_terms: v })} placeholder="30 days" />
          <Pressable style={s.saveBtn} onPress={createSupplier}><Ionicons name="add-circle" size={18} color="#fff" /><Text style={s.saveBtnText}>Create Supplier</Text></Pressable>
        </View></View>
      </Modal>

      {/* Create PO Modal */}
      <Modal visible={showAddPO} animationType="slide" transparent>
        <View style={s.modalOverlay}><View style={s.modal}>
          <View style={s.modalHead}><Text style={s.modalTitle}>New Purchase Order</Text><TouchableOpacity onPress={() => setShowAddPO(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          <Text style={s.label}>Supplier *</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
            {suppliers.map(sup => (<Pressable key={sup.id} style={[s.chip, newPO.supplier_id === sup.id && s.chipActive]} onPress={() => setNewPO({ ...newPO, supplier_id: sup.id })}><Text style={[s.chipText, newPO.supplier_id === sup.id && s.chipTextActive]}>{sup.name}</Text></Pressable>))}
          </ScrollView>
          <Text style={s.label}>Item *</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
            {stockItems.map(item => (<Pressable key={item.id} style={[s.chip, newPO.items[0]?.stock_item_id === item.id && s.chipActive]} onPress={() => { const items = [...newPO.items]; items[0].stock_item_id = item.id; setNewPO({ ...newPO, items }); }}><Text style={[s.chipText, newPO.items[0]?.stock_item_id === item.id && s.chipTextActive]}>{item.name}</Text></Pressable>))}
          </ScrollView>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ flex: 1 }}><Text style={s.label}>Qty</Text><TextInput style={s.input} value={newPO.items[0]?.qty} onChangeText={v => { const items = [...newPO.items]; items[0].qty = v; setNewPO({ ...newPO, items }); }} placeholder="100" keyboardType="numeric" /></View>
            <View style={{ flex: 1 }}><Text style={s.label}>Rate (Rs.)</Text><TextInput style={s.input} value={newPO.items[0]?.rate} onChangeText={v => { const items = [...newPO.items]; items[0].rate = v; setNewPO({ ...newPO, items }); }} placeholder="75" keyboardType="numeric" /></View>
          </View>
          <Pressable style={s.saveBtn} onPress={createPO}><Ionicons name="cart" size={18} color="#fff" /><Text style={s.saveBtnText}>Create PO</Text></Pressable>
        </View></View>
      </Modal>

      {/* QC Modal */}
      <Modal visible={showQC} animationType="slide" transparent>
        <View style={s.modalOverlay}><View style={s.modal}>
          <View style={s.modalHead}><Text style={s.modalTitle}>QC — {selectedPO?.po_number}</Text><TouchableOpacity onPress={() => setShowQC(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          {selectedPO && (selectedPO.items || []).map((item: any, i: number) => (
            <View key={i} style={{ backgroundColor: 'rgba(241,245,249,0.7)', borderRadius: 10, padding: 10, marginBottom: 8 }}>
              <Text style={{ fontSize: 13, fontWeight: '600' }}>{item.stock_item_name}: {item.qty_ordered} {item.unit}</Text>
              <Text style={{ fontSize: 11, color: '#94A3B8' }}>QC: {item.qc_status} | Accepted: {item.qty_accepted} | Rejected: {item.qty_rejected}</Text>
              {item.qc_status === 'pending' && (
                <Pressable style={[s.actionBtn, { marginTop: 6 }]} onPress={() => { setQcItemIndex(i); }}><Text style={s.actionText}>Select for QC</Text></Pressable>
              )}
            </View>
          ))}
          <Text style={s.label}>Accepted Qty</Text><TextInput style={s.input} value={qcData.accepted_qty} onChangeText={v => setQcData({ ...qcData, accepted_qty: v })} keyboardType="numeric" placeholder="95" />
          <Text style={s.label}>Rejected Qty</Text><TextInput style={s.input} value={qcData.rejected_qty} onChangeText={v => setQcData({ ...qcData, rejected_qty: v })} keyboardType="numeric" placeholder="5" />
          <Text style={s.label}>Reason (if rejected)</Text><TextInput style={s.input} value={qcData.reason} onChangeText={v => setQcData({ ...qcData, reason: v })} placeholder="Damaged" />
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 12 }}>
            <Pressable style={[s.saveBtn, { flex: 1, backgroundColor: '#10B981' }]} onPress={() => processQC('passed')}><Text style={s.saveBtnText}>Pass</Text></Pressable>
            <Pressable style={[s.saveBtn, { flex: 1, backgroundColor: '#F59E0B' }]} onPress={() => processQC('partial')}><Text style={s.saveBtnText}>Partial</Text></Pressable>
            <Pressable style={[s.saveBtn, { flex: 1, backgroundColor: '#EF4444' }]} onPress={() => processQC('failed')}><Text style={s.saveBtnText}>Fail</Text></Pressable>
          </View>
        </View></View>
      </Modal>

      {/* Issue Stock Modal */}
      <Modal visible={showIssue} animationType="slide" transparent>
        <View style={s.modalOverlay}><View style={[s.modal, { maxHeight: '85%' }]}>
          <View style={s.modalHead}><Text style={s.modalTitle}>Issue Stock</Text><TouchableOpacity onPress={() => setShowIssue(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          <Text style={s.label}>Work Order</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
            {workOrders.map(wo => (<Pressable key={wo.id} style={[s.chip, issueWOId === wo.id && s.chipActive]} onPress={() => setIssueWOId(wo.id)}><Text style={[s.chipText, issueWOId === wo.id && s.chipTextActive]}>{wo.wo_number}</Text></Pressable>))}
          </ScrollView>
          <Text style={s.label}>Items & Qty</Text>
          <ScrollView style={{ maxHeight: 250 }}>
            {issueItems.map((item: any, i: number) => (
              <View key={i} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <Text style={{ flex: 2, fontSize: 12 }}>{item.name}</Text>
                <TextInput style={[s.input, { flex: 1, marginBottom: 0 }]} value={item.qty} onChangeText={v => { const arr = [...issueItems]; arr[i].qty = v; setIssueItems(arr); }} placeholder="0" keyboardType="numeric" />
              </View>
            ))}
          </ScrollView>
          <Pressable style={[s.saveBtn, { backgroundColor: '#8B5CF6' }]} onPress={issueStock}><Ionicons name="arrow-up-circle" size={18} color="#fff" /><Text style={s.saveBtnText}>Issue Stock</Text></Pressable>
        </View></View>
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F0F4F8' },
  centerText: { marginTop: 12, fontSize: 15, color: '#94A3B8' },
  header: { backgroundColor: '#0F172A', paddingTop: 56, paddingBottom: 22, paddingHorizontal: 20, borderBottomLeftRadius: 24, borderBottomRightRadius: 24, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#FFFFFF' },
  headerSub: { fontSize: 13, color: '#C5964A', marginTop: 3, fontWeight: '500' },
  tabBtn: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, marginRight: 6, backgroundColor: 'rgba(255,255,255,0.5)' },
  tabBtnActive: { backgroundColor: '#fff', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 },
  tabText: { fontSize: 12, fontWeight: '500', color: '#94A3B8' },
  tabTextActive: { color: '#C5964A', fontWeight: '700' },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#0F172A', marginBottom: 10 },
  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  statCard: { flex: 1, backgroundColor: 'rgba(255,255,255,0.78)', borderRadius: 12, padding: 12, borderLeftWidth: 3 },
  statNum: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  statLabel: { fontSize: 10, color: '#94A3B8', fontWeight: '600' },
  card: { backgroundColor: 'rgba(255,255,255,0.82)', borderRadius: 14, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.35)', shadowColor: '#0F172A', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 10, elevation: 2 },
  cardTitle: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  cardMeta: { fontSize: 11, color: '#64748B', marginTop: 2 },
  stockQty: { fontSize: 18, fontWeight: '800', color: '#10B981' },
  reorderText: { fontSize: 10, color: '#94A3B8' },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  statusText: { fontSize: 11, fontWeight: '700' },
  poItem: { fontSize: 11, color: '#475569', marginTop: 2 },
  poTotal: { fontSize: 13, fontWeight: '700', color: '#960018', marginTop: 6 },
  txnRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(226,232,240,0.4)' },
  txnName: { fontSize: 13, fontWeight: '600', color: '#0F172A' },
  txnRef: { fontSize: 10, color: '#94A3B8' },
  txnQty: { fontSize: 15, fontWeight: '700' },
  emptyState: { alignItems: 'center', paddingVertical: 40 },
  emptyText: { fontSize: 14, color: '#94A3B8', marginTop: 8 },
  alertLabel: { fontSize: 10, color: '#94A3B8' },
  alertValue: { fontSize: 14, fontWeight: '700', color: '#0F172A' },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#C5964A', backgroundColor: 'rgba(197,150,74,0.08)' },
  actionText: { fontSize: 12, fontWeight: '600', color: '#C5964A' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 22, maxHeight: '80%' },
  modalHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  label: { fontSize: 11, fontWeight: '600', color: '#C5964A', letterSpacing: 0.5, marginBottom: 4, marginTop: 10 },
  input: { backgroundColor: 'rgba(241,245,249,0.8)', borderWidth: 1, borderColor: 'rgba(226,232,240,0.5)', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: '#0F172A', marginBottom: 4 },
  chip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#F8FAFC', marginRight: 4 },
  chipActive: { backgroundColor: '#960018', borderColor: '#960018' },
  chipText: { fontSize: 11, fontWeight: '600', color: '#64748B' },
  chipTextActive: { color: '#fff' },
  saveBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#960018', borderRadius: 12, paddingVertical: 14, marginTop: 14 },
  saveBtnText: { fontSize: 14, fontWeight: '700', color: '#fff' },
});
