import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, ActivityIndicator, TouchableOpacity, Alert, TextInput, Modal, FlatList, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { confirmAction } from '../../components/shared/confirm';
import { ExportButtons } from '../../components/shared/ExportButtons';
import { SearchBar } from '../../components/shared/SearchBar';

type Tab = 'dashboard' | 'stock' | 'po' | 'suppliers' | 'alerts' | 'shortages';

export default function StoreScreen() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [tab, setTab] = useState<Tab>('dashboard');
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [dashboard, setDashboard] = useState<any>(null);
  const [stockItems, setStockItems] = useState<any[]>([]);
  const [pos, setPos] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [woShortages, setWoShortages] = useState<any[]>([]);
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
  const [newPO, setNewPO] = useState<{ supplier_id: string; expected_delivery: string; notes: string; interstate: boolean; linked_wo_ids: string[]; items: { stock_item_id: string; qty: string; rate: string; gst_rate: string }[] }>({ supplier_id: '', expected_delivery: '', notes: '', interstate: false, linked_wo_ids: [], items: [{ stock_item_id: '', qty: '', rate: '', gst_rate: '18' }] });
  const [woShortageRows, setWoShortageRows] = useState<any[]>([]);
  const [shortageView, setShortageView] = useState<'consolidated' | 'by_wo'>('consolidated');
  const [qcData, setQcData] = useState({ accepted_qty: '', rejected_qty: '', reason: '' });
  const [qcItemIndex, setQcItemIndex] = useState(0);
  const [issueItems, setIssueItems] = useState<any[]>([]);
  const [issueWOId, setIssueWOId] = useState('');
  const [workOrders, setWorkOrders] = useState<any[]>([]);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [dashRes, itemsRes, posRes, suppRes, alertRes, shortRes, byWoRes] = await Promise.all([
        api.get('/store/dashboard'), api.get('/store/items'),
        api.get('/store/purchase-orders'), api.get('/suppliers'),
        api.get('/store/alerts'), api.get('/wo-shortages'),
        api.get('/wo-shortages/by-wo'),
      ]);
      setDashboard(dashRes.data);
      setStockItems(itemsRes.data.items || []);
      setPos(posRes.data.purchase_orders || []);
      setSuppliers(suppRes.data.suppliers || []);
      setAlerts(alertRes.data.alerts || []);
      setWoShortageRows(byWoRes.data.rows || []);
      setWoShortages(shortRes.data.shortages || []);
    } catch (e) { console.log('Store fetch error', e); }
    finally { setLoading(false); }
  };

  const onRefresh = async () => { setRefreshing(true); await fetchAll(); setRefreshing(false); };

  const createStockItem = async () => {
    if (!newItem.name) { Alert.alert('Error', 'Name required'); return; }
    // Auto-generate bom_match_key from category + name
    let matchKey = newItem.category + ':';
    const name = newItem.name;
    // Extract numbers from name for key (e.g., "Pipe 114.3mm x 4.5mm" → "pipe:114.3:4.5")
    const nums = name.match(/[\d.]+/g);
    if (nums) matchKey += nums.join(':');
    else matchKey += name.toLowerCase().replace(/\s+/g, '_');
    
    try {
      if (!(await confirmAction('Create stock item?', `${newItem.name} will be added to the inventory master.`))) return;
      await api.post('/store/items', { ...newItem, reorder_level: parseFloat(newItem.reorder_level) || 0, current_stock: 0, bom_match_key: matchKey });
      setShowAddItem(false); setNewItem({ name: '', category: 'pipe', unit_purchase: 'meters', unit_bom: 'kg', reorder_level: '' });
      fetchAll(); Alert.alert('Success', `Stock item created\nMatch Key: ${matchKey}`);
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const createSupplier = async () => {
    if (!newSupplier.name) { Alert.alert('Error', 'Name required'); return; }
    try {
      if (!(await confirmAction('Create supplier?', `${newSupplier.name} will be added to the supplier list.`))) return;
      await api.post('/suppliers', newSupplier);
      setShowAddSupplier(false); setNewSupplier({ name: '', contact_person: '', phone: '', gst_number: '', city: '', payment_terms: '' });
      fetchAll(); Alert.alert('Success', 'Supplier created');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const resetNewPO = () => setNewPO({ supplier_id: '', expected_delivery: '', notes: '', interstate: false, linked_wo_ids: [], items: [{ stock_item_id: '', qty: '', rate: '', gst_rate: '18' }] });

  const createPO = async () => {
    const validItems = newPO.items.filter(i => i.stock_item_id && parseFloat(i.qty) > 0);
    if (!newPO.supplier_id) { Alert.alert('Error', 'Select a supplier'); return; }
    if (validItems.length === 0) { Alert.alert('Error', 'Add at least one item with qty > 0'); return; }
    try {
      const items = validItems.map(i => ({
        stock_item_id: i.stock_item_id,
        qty: parseFloat(i.qty) || 0,
        rate: parseFloat(i.rate) || 0,
        gst_rate: parseFloat(i.gst_rate) || 0,
      }));
      if (!(await confirmAction('Create Purchase Order?', `A new PO will be raised with ${items.length} line(s).`))) return;
      await api.post('/store/purchase-orders', {
        supplier_id: newPO.supplier_id,
        items,
        notes: newPO.notes || null,
        expected_delivery: newPO.expected_delivery || null,
        interstate: newPO.interstate,
        linked_wo_ids: newPO.linked_wo_ids,
      });
      setShowAddPO(false); resetNewPO();
      fetchAll(); Alert.alert('Success', 'Purchase Order created');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const openPOFromShortage = (short: any) => {
    // Prefill one line with this shortage
    const shortQty = Math.max(short.shortage || 0, 0);
    setNewPO({
      supplier_id: '',
      expected_delivery: '',
      notes: `Raised to cover shortage on ${Array.isArray(short.wo_numbers) ? short.wo_numbers.join(', ') : short.wo_number || ''}`,
      interstate: false,
      linked_wo_ids: [],
      items: [{ stock_item_id: short.stock_item_id || '', qty: String(shortQty), rate: '', gst_rate: '18' }],
    });
    setShowAddPO(true);
  };

  const openPOFromWO = (row: any) => {
    // Prefill every shortage item of this WO
    const lines = (row.shortages || []).map((s: any) => ({
      stock_item_id: s.stock_item_id || '',
      qty: String(Math.max(s.shortage || 0, 0)),
      rate: '',
      gst_rate: '18',
    }));
    setNewPO({
      supplier_id: '',
      expected_delivery: '',
      notes: `Raised to cover shortages on ${row.wo_number}`,
      interstate: false,
      linked_wo_ids: row.wo_id ? [row.wo_id] : [],
      items: lines.length > 0 ? lines : [{ stock_item_id: '', qty: '', rate: '', gst_rate: '18' }],
    });
    setShowAddPO(true);
  };

  const addPOLine = () => setNewPO(p => ({ ...p, items: [...p.items, { stock_item_id: '', qty: '', rate: '', gst_rate: '18' }] }));
  const removePOLine = (idx: number) => setNewPO(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) }));
  const updatePOLine = (idx: number, field: string, value: string) => setNewPO(p => ({ ...p, items: p.items.map((it, i) => i === idx ? { ...it, [field]: value } : it) }));

  const processQC = async (status: string) => {
    if (!selectedPO) return;
    try {
      if (!(await confirmAction(`Mark QC as ${status.toUpperCase()}?`, `Accepted: ${qcData.accepted_qty || 0}, Rejected: ${qcData.rejected_qty || 0}. This updates the PO inwards and stock levels.`))) return;
      await api.post('/store/qc', { po_id: selectedPO.id, item_index: qcItemIndex, status, accepted_qty: parseFloat(qcData.accepted_qty) || 0, rejected_qty: parseFloat(qcData.rejected_qty) || 0, reason: qcData.reason });
      setShowQC(false); setQcData({ accepted_qty: '', rejected_qty: '', reason: '' });
      fetchAll(); Alert.alert('Success', `QC ${status}`);
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const [issueRecent, setIssueRecent] = useState<any[]>([]);

  const openIssueModal = async () => {
    try {
      const res = await api.get('/work-orders');
      setWorkOrders(res.data.work_orders || []);
      // Start empty; filled when user picks a WO
      setIssueItems([]);
      setIssueWOId('');
      setIssueRecent([]);
      setShowIssue(true);
    } catch {}
  };

  const loadIssuePlan = async (woId: string) => {
    setIssueWOId(woId);
    if (!woId) { setIssueItems([]); setIssueRecent([]); return; }
    try {
      const res = await api.get(`/work-orders/${woId}/issue-plan`);
      const plan = res.data.plan || [];
      setIssueRecent(res.data.recent_issues || []);
      // Pre-fill qty = remaining_qty (what's still pending to issue). User can edit before submit.
      const rows = plan.map((p: any) => ({
        stock_item_id: p.stock_item_id,
        name: p.stock_item_name || `${p.component} — ${p.description}`,
        bom_match_key: p.bom_match_key,
        component: p.component,
        required_qty: p.required_qty,
        already_issued_qty: p.already_issued_qty,
        remaining_qty: p.remaining_qty,
        current_stock: p.current_stock,
        unit: p.unit,
        in_register: p.in_register,
        qty: p.remaining_qty > 0 ? String(p.remaining_qty) : '',
      }));
      // Items with no stock_item match can't be issued — include for visibility but disable
      setIssueItems(rows);
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to load WO BOM');
      setIssueItems([]);
    }
  };

  const issueStock = async () => {
    if (!issueWOId) { Alert.alert('Error', 'Select a Work Order first'); return; }
    const toIssue = issueItems.filter((i: any) => i.stock_item_id && parseFloat(i.qty || '0') > 0);
    if (toIssue.length === 0) { Alert.alert('Error', 'Enter at least one qty'); return; }
    const shorts = toIssue.filter((i: any) => parseFloat(i.qty) > (i.current_stock || 0));
    if (shorts.length > 0) {
      Alert.alert('Insufficient stock', shorts.map((s: any) => `${s.name}: need ${s.qty}, have ${s.current_stock}`).join('\n'));
      return;
    }
    try {
      if (!(await confirmAction('Issue material to Work Order?', `${toIssue.length} line(s) will be deducted from current stock.`))) return;
      await api.post('/store/issue', { wo_id: issueWOId, items: toIssue.map((i: any) => ({ stock_item_id: i.stock_item_id, qty: parseFloat(i.qty) })) });
      setShowIssue(false); fetchAll(); Alert.alert('Success', 'Stock issued');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  if (!isAdmin) return <View style={s.center}><Ionicons name="lock-closed" size={48} color="#94A3B8" /><Text style={s.centerText}>Admin access required</Text></View>;
  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#C5964A" /></View>;

  // Filter helpers
  const q = searchQuery.trim().toLowerCase();
  const matches = (...fields: any[]) => !q || fields.some((v) => String(v ?? '').toLowerCase().includes(q));
  const filteredStock = stockItems.filter((it: any) => matches(it.name, it.category, it.bom_match_key, it.unit_purchase));
  const filteredPos = pos.filter((p: any) => matches(p.po_number, p.supplier_name, p.status));
  const filteredSuppliers = suppliers.filter((sup: any) => matches(sup.name, sup.gstin, sup.contact_phone, sup.contact_email));
  const filteredShortages = woShortages.filter((sh: any) => matches(sh.wo_number, sh.item_name, sh.bom_match_key));
  const filteredAlerts = alerts.filter((a: any) => matches(a.stock_item_name, a.type, a.message));

  return (
    <View style={s.container}>
      <View style={s.header}>
        <View><Text style={s.headerTitle}>Store</Text><Text style={s.headerSub}>Inventory & Purchase Management</Text></View>
        <TouchableOpacity onPress={onRefresh}><Ionicons name="refresh" size={22} color="#C5964A" /></TouchableOpacity>
      </View>

      <SearchBar
        value={searchQuery}
        onChangeText={setSearchQuery}
        placeholder="Search items, POs, suppliers by name, SKU, category..."
        testID="store-search"
      />

      {/* Tab Bar */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxHeight: 44, marginHorizontal: 14, marginTop: 12 }}>
        {([['dashboard','grid-outline','Dashboard'],['stock','layers-outline','Stock'],['po','cart-outline','POs'],['suppliers','business-outline','Suppliers'],['shortages','warning-outline','Shortages'],['alerts','alert-circle-outline','Alerts']] as const).map(([key, icon, label]) => (
          <TouchableOpacity key={key} style={[s.tabBtn, tab === key && s.tabBtnActive]} onPress={() => setTab(key as Tab)}>
            <Ionicons name={icon as any} size={15} color={tab === key ? '#C5964A' : '#94A3B8'} />
            <Text style={[s.tabText, tab === key && s.tabTextActive]}>{label}{key === 'alerts' && alerts.length > 0 ? ` (${alerts.length})` : ''}{key === 'shortages' && woShortages.length > 0 ? ` (${woShortages.length})` : ''}</Text>
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
              <Text style={s.sectionTitle}>Stock Items ({filteredStock.length}{q ? `/${stockItems.length}` : ''})</Text>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <ExportButtons endpoint="/store/export/stock" pdfEndpoint="/store/export/stock/pdf" filenamePrefix="Stock" compact showExcel showPdf />
                <Pressable style={s.actionBtn} onPress={() => setShowAddItem(true)}><Ionicons name="add" size={16} color="#C5964A" /><Text style={s.actionText}>Add Item</Text></Pressable>
                <Pressable style={s.actionBtn} onPress={openIssueModal} data-testid="issue-stock-btn"><Ionicons name="arrow-up-circle-outline" size={16} color="#8B5CF6" /><Text style={[s.actionText, { color: '#8B5CF6' }]}>Issue</Text></Pressable>
              </View>
            </View>
            {filteredStock.map((item: any) => (
              <View key={item.id} style={s.card}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <View style={{ flex: 1 }}><Text style={s.cardTitle}>{item.name}</Text><Text style={s.cardMeta}>{item.category} | {item.unit_purchase}{item.bom_match_key ? ` | Key: ${item.bom_match_key}` : ''}</Text></View>
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
                <ExportButtons endpoint="/store/export/purchase-orders" pdfEndpoint="/store/export/purchase-orders/pdf" filenamePrefix="POs" compact showExcel showPdf />
                <Pressable style={s.actionBtn} onPress={() => setShowAddPO(true)}><Ionicons name="add" size={16} color="#C5964A" /><Text style={s.actionText}>New PO</Text></Pressable>
              </View>
            </View>
            {filteredPos.map((po: any) => (
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
                <ExportButtons endpoint="/store/export/suppliers" pdfEndpoint="/store/export/suppliers/pdf" filenamePrefix="Suppliers" compact showExcel showPdf />
                <Pressable style={s.actionBtn} onPress={() => setShowAddSupplier(true)}><Ionicons name="add" size={16} color="#C5964A" /><Text style={s.actionText}>Add</Text></Pressable>
              </View>
            </View>
            {filteredSuppliers.map((sup: any) => (
              <View key={sup.id} style={s.card}>
                <Text style={s.cardTitle}>{sup.name}</Text>
                <Text style={s.cardMeta}>{sup.contact_person} | {sup.phone} | {sup.city}</Text>
                {sup.gst_number && <Text style={s.cardMeta}>GST: {sup.gst_number}</Text>}
                {sup.payment_terms && <Text style={s.cardMeta}>Terms: {sup.payment_terms}</Text>}
              </View>
            ))}
          </>
        )}

        {/* SHORTAGES — WO BOM vs Stock */}
        {tab === 'shortages' && (
          <>
            {/* Sub-toggle: Consolidated vs By-WO */}
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
              <Pressable onPress={() => setShortageView('consolidated')} style={[s.chip, shortageView === 'consolidated' && s.chipActive]} testID="shortage-consolidated-tab">
                <Text style={[s.chipText, shortageView === 'consolidated' && s.chipTextActive]}>Consolidated ({woShortages.length})</Text>
              </Pressable>
              <Pressable onPress={() => setShortageView('by_wo')} style={[s.chip, shortageView === 'by_wo' && s.chipActive]} testID="shortage-by-wo-tab">
                <Text style={[s.chipText, shortageView === 'by_wo' && s.chipTextActive]}>By Work Order ({woShortageRows.length})</Text>
              </Pressable>
            </View>

            {shortageView === 'consolidated' ? (
              woShortages.length === 0 ? <View style={s.emptyState}><Ionicons name="checkmark-circle" size={48} color="#10B981" /><Text style={s.emptyText}>No shortages — all WO materials available</Text></View> :
              filteredShortages.map((sh: any, i: number) => (
                <View key={i} style={[s.card, { borderLeftWidth: 3, borderLeftColor: sh.stock_item_id ? '#F59E0B' : '#EF4444' }]} testID={`shortage-row-${i}`}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.cardTitle}>{sh.component}</Text>
                      <Text style={s.cardMeta}>{sh.description}</Text>
                      {!sh.stock_item_id && <Text style={{ fontSize: 10, color: '#EF4444', fontWeight: '700', marginTop: 2 }}>NOT IN STOCK REGISTER</Text>}
                      {sh.stock_item_id && <Text style={{ fontSize: 10, color: '#64748B', marginTop: 2 }}>Stock: {sh.stock_item_name}</Text>}
                    </View>
                    {sh.stock_item_id && (
                      <TouchableOpacity onPress={() => openPOFromShortage(sh)} style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#C5964A', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10 }} testID={`create-po-shortage-${i}`}>
                        <Ionicons name="cart" size={14} color="#fff" />
                        <Text style={{ fontSize: 11, color: '#fff', fontWeight: '700' }}>Raise PO</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                  <View style={{ flexDirection: 'row', gap: 16, marginTop: 8 }}>
                    <View><Text style={s.alertLabel}>Required</Text><Text style={s.alertValue}>{sh.required} {sh.unit}</Text></View>
                    <View><Text style={s.alertLabel}>Available</Text><Text style={[s.alertValue, { color: '#10B981' }]}>{sh.available} {sh.unit}</Text></View>
                    <View><Text style={s.alertLabel}>Shortage</Text><Text style={[s.alertValue, { color: '#EF4444', fontWeight: '800' }]}>{sh.shortage} {sh.unit}</Text></View>
                  </View>
                  <Text style={{ fontSize: 10, color: '#94A3B8', marginTop: 6 }}>WOs: {(sh.wo_numbers || []).filter((v: string, i: number, a: string[]) => a.indexOf(v) === i).join(', ')}</Text>
                </View>
              ))
            ) : (
              woShortageRows.length === 0 ? <View style={s.emptyState}><Ionicons name="checkmark-circle" size={48} color="#10B981" /><Text style={s.emptyText}>No pending WOs with shortages</Text></View> :
              woShortageRows.filter((r: any) => matches(r.wo_number, r.customer_name, r.so_number)).map((row: any) => (
                <View key={row.wo_id} style={[s.card, { borderLeftWidth: 3, borderLeftColor: '#F59E0B' }]} testID={`shortage-wo-row-${row.wo_number}`}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.cardTitle}>{row.wo_number}</Text>
                      <Text style={s.cardMeta}>{row.customer_name} · SO {row.so_number} · {row.shortage_count} item(s) short</Text>
                      {row.delivery_date && <Text style={{ fontSize: 10, color: '#EF4444', marginTop: 2 }}>Delivery: {row.delivery_date}</Text>}
                    </View>
                    <TouchableOpacity onPress={() => openPOFromWO(row)} style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#0F172A', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10 }} testID={`create-po-wo-${row.wo_number}`}>
                      <Ionicons name="cart" size={14} color="#fff" />
                      <Text style={{ fontSize: 11, color: '#fff', fontWeight: '700' }}>Create PO ({row.shortage_count})</Text>
                    </TouchableOpacity>
                  </View>
                  <View style={{ marginTop: 10, paddingLeft: 6, borderLeftWidth: 2, borderLeftColor: '#E2E8F0' }}>
                    {(row.shortages || []).slice(0, 8).map((sh: any, i: number) => (
                      <View key={i} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}>
                        <Text style={{ fontSize: 11, color: '#334155', flex: 2 }}>{sh.stock_item_name || sh.component} {sh.description ? `(${sh.description})` : ''}</Text>
                        <Text style={{ fontSize: 11, color: '#EF4444', fontWeight: '700', flex: 1, textAlign: 'right' }}>{sh.shortage} {sh.unit}</Text>
                      </View>
                    ))}
                    {(row.shortages || []).length > 8 && (<Text style={{ fontSize: 10, color: '#94A3B8', marginTop: 4 }}>+{row.shortages.length - 8} more</Text>)}
                  </View>
                </View>
              ))
            )}
          </>
        )}

        {/* ALERTS */}
        {tab === 'alerts' && (
          <>
            <Text style={s.sectionTitle}>Low Stock Alerts ({alerts.length})</Text>
            {alerts.length === 0 ? <View style={s.emptyState}><Ionicons name="checkmark-circle" size={48} color="#10B981" /><Text style={s.emptyText}>All stock levels OK</Text></View> :
            filteredAlerts.map((a: any) => (
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
        <View style={s.modalOverlay}><View style={[s.modal, { maxHeight: '92%' }]}>
          <View style={s.modalHead}><Text style={s.modalTitle}>New Purchase Order</Text><TouchableOpacity onPress={() => setShowAddPO(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          <ScrollView style={{ maxHeight: 620 }} showsVerticalScrollIndicator={false}>
            <Text style={s.label}>Supplier *</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
              {suppliers.map(sup => (<Pressable key={sup.id} style={[s.chip, newPO.supplier_id === sup.id && s.chipActive]} onPress={() => setNewPO({ ...newPO, supplier_id: sup.id })}><Text style={[s.chipText, newPO.supplier_id === sup.id && s.chipTextActive]}>{sup.name}</Text></Pressable>))}
            </ScrollView>

            <View style={{ flexDirection: 'row', gap: 8 }}>
              <View style={{ flex: 1 }}>
                <Text style={s.label}>Expected Delivery</Text>
                <TextInput style={s.input} value={newPO.expected_delivery} onChangeText={v => setNewPO({ ...newPO, expected_delivery: v })} placeholder="YYYY-MM-DD" testID="po-expected-delivery" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={s.label}>GST Scheme</Text>
                <View style={{ flexDirection: 'row', gap: 6, marginTop: 4 }}>
                  <Pressable style={[s.chip, !newPO.interstate && s.chipActive]} onPress={() => setNewPO({ ...newPO, interstate: false })} testID="po-cgst-sgst">
                    <Text style={[s.chipText, !newPO.interstate && s.chipTextActive]}>CGST+SGST</Text>
                  </Pressable>
                  <Pressable style={[s.chip, newPO.interstate && s.chipActive]} onPress={() => setNewPO({ ...newPO, interstate: true })} testID="po-igst">
                    <Text style={[s.chipText, newPO.interstate && s.chipTextActive]}>IGST</Text>
                  </Pressable>
                </View>
              </View>
            </View>

            {newPO.linked_wo_ids && newPO.linked_wo_ids.length > 0 && (
              <View style={{ backgroundColor: '#EEF2FF', borderRadius: 8, padding: 8, marginTop: 8 }}>
                <Text style={{ fontSize: 11, color: '#4338CA', fontWeight: '700' }}>🔗 Linked to WO(s): {newPO.linked_wo_ids.length}</Text>
              </View>
            )}

            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, marginBottom: 4 }}>
              <Text style={[s.label, { marginBottom: 0 }]}>Line Items *</Text>
              <Pressable onPress={addPOLine} style={{ flexDirection: 'row', gap: 4, alignItems: 'center', backgroundColor: '#C5964A', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8 }} testID="po-add-line">
                <Ionicons name="add" size={14} color="#fff" />
                <Text style={{ fontSize: 11, color: '#fff', fontWeight: '700' }}>Add Line</Text>
              </Pressable>
            </View>

            {newPO.items.map((line, idx) => {
              const qty = parseFloat(line.qty) || 0;
              const rate = parseFloat(line.rate) || 0;
              const gst = parseFloat(line.gst_rate) || 0;
              const amount = qty * rate;
              const gstAmt = amount * gst / 100;
              const lineTotal = amount + gstAmt;
              return (
                <View key={idx} style={{ backgroundColor: '#F8FAFC', borderRadius: 10, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#E2E8F0' }} testID={`po-line-${idx}`}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <Text style={{ fontSize: 11, fontWeight: '700', color: '#64748B' }}>Line {idx + 1}</Text>
                    {newPO.items.length > 1 && (
                      <Pressable onPress={() => removePOLine(idx)} testID={`po-remove-line-${idx}`}>
                        <Ionicons name="trash-outline" size={16} color="#EF4444" />
                      </Pressable>
                    )}
                  </View>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 6 }}>
                    {stockItems.map(item => (<Pressable key={item.id} style={[s.chip, line.stock_item_id === item.id && s.chipActive]} onPress={() => updatePOLine(idx, 'stock_item_id', item.id)}><Text style={[s.chipText, line.stock_item_id === item.id && s.chipTextActive]}>{item.name}</Text></Pressable>))}
                  </ScrollView>
                  <View style={{ flexDirection: 'row', gap: 6 }}>
                    <View style={{ flex: 1 }}><Text style={s.label}>Qty</Text><TextInput style={s.input} value={line.qty} onChangeText={v => updatePOLine(idx, 'qty', v)} placeholder="100" keyboardType="numeric" testID={`po-qty-${idx}`} /></View>
                    <View style={{ flex: 1 }}><Text style={s.label}>Rate (Rs.)</Text><TextInput style={s.input} value={line.rate} onChangeText={v => updatePOLine(idx, 'rate', v)} placeholder="75" keyboardType="numeric" testID={`po-rate-${idx}`} /></View>
                    <View style={{ width: 80 }}><Text style={s.label}>GST %</Text><TextInput style={s.input} value={line.gst_rate} onChangeText={v => updatePOLine(idx, 'gst_rate', v)} placeholder="18" keyboardType="numeric" testID={`po-gst-${idx}`} /></View>
                  </View>
                  <View style={{ flexDirection: 'row', gap: 4, marginTop: 4 }}>
                    {['5', '12', '18', '28'].map(g => (
                      <Pressable key={g} style={[s.chip, line.gst_rate === g && s.chipActive, { paddingHorizontal: 8, paddingVertical: 3 }]} onPress={() => updatePOLine(idx, 'gst_rate', g)}>
                        <Text style={[s.chipText, line.gst_rate === g && s.chipTextActive, { fontSize: 10 }]}>{g}%</Text>
                      </Pressable>
                    ))}
                  </View>
                  {amount > 0 && (
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 8, paddingTop: 6, borderTopWidth: 1, borderTopColor: '#E2E8F0' }}>
                      <Text style={{ fontSize: 10, color: '#64748B' }}>Base: <Text style={{ color: '#0F172A', fontWeight: '700' }}>Rs.{amount.toFixed(2)}</Text></Text>
                      <Text style={{ fontSize: 10, color: '#64748B' }}>GST: <Text style={{ color: '#0F172A', fontWeight: '700' }}>Rs.{gstAmt.toFixed(2)}</Text></Text>
                      <Text style={{ fontSize: 11, color: '#C5964A', fontWeight: '800' }}>Rs.{lineTotal.toFixed(2)}</Text>
                    </View>
                  )}
                </View>
              );
            })}

            {/* Totals */}
            {(() => {
              const sub = newPO.items.reduce((t, i) => t + (parseFloat(i.qty) || 0) * (parseFloat(i.rate) || 0), 0);
              const gstT = newPO.items.reduce((t, i) => t + ((parseFloat(i.qty) || 0) * (parseFloat(i.rate) || 0) * (parseFloat(i.gst_rate) || 0) / 100), 0);
              return (
                <View style={{ backgroundColor: '#0F172A', borderRadius: 10, padding: 12, marginTop: 4 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text style={{ fontSize: 11, color: '#94A3B8' }}>Subtotal</Text>
                    <Text style={{ fontSize: 12, color: '#fff', fontWeight: '700' }}>Rs.{sub.toFixed(2)}</Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text style={{ fontSize: 11, color: '#94A3B8' }}>{newPO.interstate ? 'IGST' : 'CGST + SGST'}</Text>
                    <Text style={{ fontSize: 12, color: '#fff', fontWeight: '700' }}>Rs.{gstT.toFixed(2)}</Text>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingTop: 6, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.1)' }}>
                    <Text style={{ fontSize: 13, color: '#C5964A', fontWeight: '700' }}>GRAND TOTAL</Text>
                    <Text style={{ fontSize: 15, color: '#C5964A', fontWeight: '800' }}>Rs.{(sub + gstT).toFixed(2)}</Text>
                  </View>
                </View>
              );
            })()}

            <Text style={[s.label, { marginTop: 10 }]}>Notes</Text>
            <TextInput style={[s.input, { minHeight: 60 }]} value={newPO.notes} onChangeText={v => setNewPO({ ...newPO, notes: v })} placeholder="Any terms, delivery instructions, references..." multiline testID="po-notes" />
          </ScrollView>
          <Pressable style={s.saveBtn} onPress={createPO} testID="po-submit"><Ionicons name="cart" size={18} color="#fff" /><Text style={s.saveBtnText}>Create Purchase Order</Text></Pressable>
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
        <View style={s.modalOverlay}><View style={[s.modal, { maxHeight: '88%' }]}>
          <View style={s.modalHead}><Text style={s.modalTitle}>Issue Stock to Work Order</Text><TouchableOpacity onPress={() => setShowIssue(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity></View>
          <Text style={s.label}>Select Work Order</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 10 }}>
            {workOrders.map(wo => (<Pressable key={wo.id} style={[s.chip, issueWOId === wo.id && s.chipActive]} onPress={() => loadIssuePlan(wo.id)} data-testid={`issue-wo-chip-${wo.wo_number}`}><Text style={[s.chipText, issueWOId === wo.id && s.chipTextActive]}>{wo.wo_number}</Text></Pressable>))}
          </ScrollView>
          {issueWOId ? (
            <>
              {issueRecent.length > 0 && (
                <View style={{ backgroundColor: 'rgba(15,118,110,0.06)', borderRadius: 10, padding: 10, marginBottom: 10, borderLeftWidth: 3, borderLeftColor: '#0F766E' }}>
                  <Text style={{ fontSize: 10, fontWeight: '700', color: '#0F766E', letterSpacing: 0.5, marginBottom: 6, textTransform: 'uppercase' }}>Recent Issues ({issueRecent.length})</Text>
                  {issueRecent.map((r: any, idx: number) => (
                    <View key={idx} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 3 }}>
                      <Text style={{ flex: 2, fontSize: 11, color: '#0F172A' }} numberOfLines={1}>{r.stock_item_name}</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#8B5CF6', fontWeight: '700', textAlign: 'center' }}>-{r.qty} {r.unit}</Text>
                      <Text style={{ flex: 1, fontSize: 10, color: '#64748B', textAlign: 'right' }} numberOfLines={1}>{r.by ? r.by.split('@')[0] : ''} • {r.timestamp ? String(r.timestamp).split('T')[0] : ''}</Text>
                    </View>
                  ))}
                </View>
              )}
              <View style={{ backgroundColor: 'rgba(139,92,246,0.08)', borderRadius: 8, padding: 10, marginBottom: 8 }}>
                <Text style={{ fontSize: 11, color: '#64748B' }}>BOM-based issue plan. Qty is pre-filled with remaining-to-issue — edit freely for urgent / partial issues.</Text>
              </View>
              <Text style={s.label}>BOM Lines</Text>
              <ScrollView style={{ maxHeight: 340 }}>
                {issueItems.length === 0 && (<Text style={{ fontSize: 12, color: '#94A3B8', textAlign: 'center', padding: 20 }}>No BOM lines found for this WO</Text>)}
                {issueItems.map((item: any, i: number) => {
                  const locked = !item.in_register;
                  const overStock = parseFloat(item.qty || '0') > (item.current_stock || 0);
                  return (
                    <View key={i} style={{ backgroundColor: locked ? 'rgba(226,232,240,0.5)' : '#FFFFFF', borderRadius: 10, padding: 10, marginBottom: 8, borderWidth: 1, borderColor: overStock ? '#EF4444' : locked ? '#CBD5E1' : '#E2E8F0' }}>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <View style={{ flex: 1 }}>
                          <Text style={{ fontSize: 12, fontWeight: '700', color: locked ? '#94A3B8' : '#0F172A' }}>{item.component}</Text>
                          <Text style={{ fontSize: 11, color: '#64748B' }} numberOfLines={2}>{item.name}</Text>
                          {!locked && (
                            <View style={{ flexDirection: 'row', gap: 10, marginTop: 4 }}>
                              <Text style={{ fontSize: 10, color: '#0F766E', fontWeight: '600' }}>Req: {item.required_qty} {item.unit}</Text>
                              <Text style={{ fontSize: 10, color: '#8B5CF6', fontWeight: '600' }}>Issued: {item.already_issued_qty}</Text>
                              <Text style={{ fontSize: 10, color: '#C5964A', fontWeight: '600' }}>Pending: {item.remaining_qty}</Text>
                              <Text style={{ fontSize: 10, color: (item.current_stock || 0) >= item.remaining_qty ? '#10B981' : '#EF4444', fontWeight: '700' }}>Stock: {item.current_stock}</Text>
                            </View>
                          )}
                          {locked && <Text style={{ fontSize: 10, color: '#EF4444', fontWeight: '600', marginTop: 4 }}>⚠ Not in stock register — add item to Store first</Text>}
                        </View>
                        <TextInput
                          style={[s.input, { width: 80, marginBottom: 0, textAlign: 'center', backgroundColor: locked ? '#F1F5F9' : '#fff', color: overStock ? '#EF4444' : '#0F172A' }]}
                          editable={!locked}
                          value={item.qty}
                          onChangeText={v => { const arr = [...issueItems]; arr[i].qty = v; setIssueItems(arr); }}
                          placeholder="0"
                          keyboardType="numeric"
                          data-testid={`issue-qty-${i}`}
                        />
                      </View>
                    </View>
                  );
                })}
              </ScrollView>
            </>
          ) : (
            <Text style={{ fontSize: 12, color: '#94A3B8', textAlign: 'center', padding: 40 }}>Select a Work Order above to load its BOM</Text>
          )}
          <Pressable style={[s.saveBtn, { backgroundColor: '#8B5CF6', opacity: issueWOId ? 1 : 0.4 }]} onPress={issueStock} disabled={!issueWOId} data-testid="issue-stock-submit"><Ionicons name="arrow-up-circle" size={18} color="#fff" /><Text style={s.saveBtnText}>Issue Stock</Text></Pressable>
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
