import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, RefreshControl, ActivityIndicator,
  TouchableOpacity, Alert, TextInput, Modal, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import { confirmAction } from '../../components/shared/confirm';
import { ExportButtons } from '../../components/shared/ExportButtons';
import { SearchBar } from '../../components/shared/SearchBar';

const STAGES = ['new', 'contacted', 'quoted', 'negotiation', 'won', 'lost'];
const STAGE_LABELS: Record<string, string> = { new: 'New', contacted: 'Contacted', quoted: 'Quoted', negotiation: 'Negotiation', won: 'Won', lost: 'Lost' };
const STAGE_COLORS: Record<string, string> = { new: '#3B82F6', contacted: '#8B5CF6', quoted: '#C5964A', negotiation: '#F59E0B', won: '#10B981', lost: '#EF4444' };
const SOURCES = ['phone', 'email', 'walk_in', 'referral', 'website', 'other'];
const SOURCE_LABELS: Record<string, string> = { phone: 'Phone', email: 'Email', walk_in: 'Walk-in', referral: 'Referral', website: 'Website', other: 'Other' };
const FU_TYPES = ['call', 'email', 'meeting', 'other'];

interface Lead { id: string; name: string; company?: string; email?: string; phone?: string; stage: string; source: string; estimated_value?: number; notes?: string; product_interest?: string; has_overdue_followup?: boolean; created_at: string; }
interface Summary { total_leads: number; active_leads: number; won: number; lost: number; overdue_followups: number; today_followups: number; pipeline_value: number; conversion_rate: number; stage_counts: Record<string, number>; recent_activities: any[]; }

export default function CRMScreen() {
  const { user } = useAuth();
  const [tab, setTab] = useState<'pipeline' | 'followups' | 'activity' | 'analytics'>('pipeline');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [followups, setFollowups] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [revenueTrend, setRevenueTrend] = useState<any[]>([]);
  const [orderStats, setOrderStats] = useState<any>(null);
  const [woStats, setWoStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAddLead, setShowAddLead] = useState(false);
  const [showAddFollowup, setShowAddFollowup] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [stageFilter, setStageFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  // Add lead form
  const [newLead, setNewLead] = useState({ name: '', company: '', email: '', phone: '', source: 'phone', product_interest: 'roller', estimated_value: '', notes: '' });
  // Add followup form
  const [newFU, setNewFU] = useState({ due_date: '', note: '', follow_up_type: 'call' });

  const isAdmin = user?.role === 'admin';

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [sumRes, leadsRes, fuRes, actRes] = await Promise.all([
        api.get('/crm/summary'), api.get('/crm/leads'),
        api.get('/crm/followups'), api.get('/crm/activities?limit=30'),
      ]);
      setSummary(sumRes.data);
      setLeads(leadsRes.data.leads || []);
      setFollowups(fuRes.data.followups || []);
      setActivities(actRes.data.activities || []);
      // Fetch analytics lazily
      if (tab === 'analytics' || !analytics) {
        const [anaRes, trendRes, ordRes, woRes] = await Promise.all([
          api.get('/analytics/dashboard'), api.get('/analytics/revenue-trend?months=6'),
          api.get('/orders/summary/stats'), api.get('/work-orders/summary/stats'),
        ]);
        setAnalytics(anaRes.data);
        setRevenueTrend(trendRes.data.trends || []);
        setOrderStats(ordRes.data);
        setWoStats(woRes.data);
      }
    } catch (e) { console.log('CRM fetch error', e); }
    finally { setLoading(false); }
  };

  const onRefresh = async () => { setRefreshing(true); await fetchAll(); setRefreshing(false); };

  const createLead = async () => {
    if (!newLead.name.trim()) { Alert.alert('Error', 'Lead name is required'); return; }
    if (!(await confirmAction('Create new Lead?', `${newLead.name} will be added to the CRM pipeline.`))) return;
    try {
      await api.post('/crm/leads', { ...newLead, estimated_value: newLead.estimated_value ? parseFloat(newLead.estimated_value) : null });
      setShowAddLead(false);
      setNewLead({ name: '', company: '', email: '', phone: '', source: 'phone', product_interest: 'roller', estimated_value: '', notes: '' });
      fetchAll();
      Alert.alert('Success', 'Lead created');
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const updateStage = async (leadId: string, stage: string) => {
    if (!(await confirmAction('Move lead to this stage?', `Change stage to "${STAGE_LABELS[stage] || stage}".`))) return;
    try {
      await api.put(`/crm/leads/${leadId}`, { stage });
      fetchAll();
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const createFollowup = async () => {
    if (!selectedLead || !newFU.due_date || !newFU.note) { Alert.alert('Error', 'Fill all fields'); return; }
    if (!(await confirmAction('Schedule follow-up?', `A ${newFU.follow_up_type} follow-up for ${selectedLead.name} on ${newFU.due_date}.`))) return;
    try {
      await api.post('/crm/followups', { lead_id: selectedLead.id, ...newFU });
      setShowAddFollowup(false);
      setNewFU({ due_date: '', note: '', follow_up_type: 'call' });
      fetchAll();
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const completeFollowup = async (fuId: string) => {
    if (!(await confirmAction('Mark follow-up complete?'))) return;
    try { await api.put(`/crm/followups/${fuId}/complete`); fetchAll(); }
    catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed'); }
  };

  const filteredLeads = (() => {
    let arr = stageFilter ? leads.filter(l => l.stage === stageFilter) : leads;
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      arr = arr.filter(l =>
        (l.name || '').toLowerCase().includes(q) ||
        (l.company || '').toLowerCase().includes(q) ||
        (l.email || '').toLowerCase().includes(q) ||
        (l.phone || '').includes(searchQuery.trim()) ||
        (l.product_interest || '').toLowerCase().includes(q) ||
        (l.source || '').toLowerCase().includes(q)
      );
    }
    return arr;
  })();

  if (!isAdmin) return <View style={s.center}><Ionicons name="lock-closed" size={48} color="#94A3B8" /><Text style={s.centerText}>Admin access required</Text></View>;
  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#C5964A" /><Text style={s.centerText}>Loading CRM...</Text></View>;

  return (
    <View style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <View>
          <Text style={s.headerTitle}>CRM</Text>
          <Text style={s.headerSub}>Lead Management & Pipeline</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <ExportButtons
            endpoint="/crm/leads/export/excel"
            pdfEndpoint="/crm/leads/export/pdf"
            filenamePrefix="CRM_Leads"
            compact={true}
            showPdf={true}
            showExcel={true}
          />
          <TouchableOpacity style={s.addBtn} onPress={() => setShowAddLead(true)} data-testid="add-lead-btn">
            <Ionicons name="add" size={22} color="#0F172A" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={s.scroll} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#C5964A']} />}>
        <SearchBar
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search leads by name, company, phone, email, product..."
          resultCount={searchQuery ? filteredLeads.length : null}
          testID="dashboard-search"
        />
        {/* Summary Cards */}
        {summary && (
          <View style={s.summaryRow}>
            <View style={[s.summaryCard, { borderLeftColor: '#C5964A' }]}>
              <Text style={s.summaryNum}>{summary.active_leads}</Text>
              <Text style={s.summaryLabel}>Active</Text>
            </View>
            <View style={[s.summaryCard, { borderLeftColor: '#10B981' }]}>
              <Text style={s.summaryNum}>{summary.won}</Text>
              <Text style={s.summaryLabel}>Won</Text>
            </View>
            <View style={[s.summaryCard, { borderLeftColor: '#EF4444' }]}>
              <Text style={s.summaryNum}>{summary.overdue_followups}</Text>
              <Text style={s.summaryLabel}>Overdue</Text>
            </View>
            <View style={[s.summaryCard, { borderLeftColor: '#3B82F6' }]}>
              <Text style={s.summaryNum}>{summary.conversion_rate}%</Text>
              <Text style={s.summaryLabel}>Conv.</Text>
            </View>
          </View>
        )}

        {/* Tab Bar */}
        <View style={s.tabBar}>
          {(['pipeline', 'followups', 'activity', 'analytics'] as const).map(t => (
            <TouchableOpacity key={t} style={[s.tab, tab === t && s.tabActive]} onPress={() => { setTab(t); if (t === 'analytics' && !analytics) fetchAll(); }}>
              <Ionicons name={t === 'pipeline' ? 'funnel-outline' : t === 'followups' ? 'alarm-outline' : t === 'activity' ? 'time-outline' : 'bar-chart-outline'} size={16} color={tab === t ? '#C5964A' : '#94A3B8'} />
              <Text style={[s.tabText, tab === t && s.tabTextActive]}>{t === 'pipeline' ? 'Pipeline' : t === 'followups' ? 'Follow-ups' : t === 'activity' ? 'Activity' : 'Analytics'}</Text>
              {t === 'followups' && summary && summary.overdue_followups > 0 && (
                <View style={s.badge}><Text style={s.badgeText}>{summary.overdue_followups}</Text></View>
              )}
            </TouchableOpacity>
          ))}
        </View>

        {/* Pipeline Tab */}
        {tab === 'pipeline' && (
          <View style={s.section}>
            {/* Stage Filter */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.stageFilterRow}>
              <TouchableOpacity style={[s.stageChip, !stageFilter && s.stageChipActive]} onPress={() => setStageFilter(null)}>
                <Text style={[s.stageChipText, !stageFilter && s.stageChipTextActive]}>All ({leads.length})</Text>
              </TouchableOpacity>
              {STAGES.filter(st => st !== 'won' && st !== 'lost').map(st => (
                <TouchableOpacity key={st} style={[s.stageChip, stageFilter === st && { backgroundColor: STAGE_COLORS[st] + '20', borderColor: STAGE_COLORS[st] }]} onPress={() => setStageFilter(stageFilter === st ? null : st)}>
                  <View style={[s.stageDot, { backgroundColor: STAGE_COLORS[st] }]} />
                  <Text style={[s.stageChipText, stageFilter === st && { color: STAGE_COLORS[st] }]}>{STAGE_LABELS[st]} ({summary?.stage_counts[st] || 0})</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            {/* Lead Cards */}
            {filteredLeads.length === 0 ? (
              <View style={s.empty}><Ionicons name="people-outline" size={40} color="#CBD5E1" /><Text style={s.emptyText}>No leads yet</Text></View>
            ) : filteredLeads.map(lead => (
              <TouchableOpacity key={lead.id} style={s.leadCard} onPress={() => { setSelectedLead(lead); setShowAddFollowup(true); }}>
                <View style={s.leadHeader}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.leadName}>{lead.name}</Text>
                    {lead.company && <Text style={s.leadCompany}>{lead.company}</Text>}
                  </View>
                  <View style={[s.leadStageBadge, { backgroundColor: STAGE_COLORS[lead.stage] + '18' }]}>
                    <Text style={[s.leadStageText, { color: STAGE_COLORS[lead.stage] }]}>{STAGE_LABELS[lead.stage]}</Text>
                  </View>
                </View>
                <View style={s.leadMeta}>
                  {lead.phone && <View style={s.metaItem}><Ionicons name="call-outline" size={13} color="#94A3B8" /><Text style={s.metaText}>{lead.phone}</Text></View>}
                  {lead.estimated_value && <View style={s.metaItem}><Ionicons name="cash-outline" size={13} color="#C5964A" /><Text style={[s.metaText, { color: '#C5964A' }]}>Rs.{lead.estimated_value.toLocaleString()}</Text></View>}
                  {lead.has_overdue_followup && <View style={s.metaItem}><Ionicons name="alert-circle" size={13} color="#EF4444" /><Text style={[s.metaText, { color: '#EF4444' }]}>Overdue</Text></View>}
                </View>
                {/* Quick stage buttons */}
                <View style={s.quickStages}>
                  {STAGES.filter(st => st !== lead.stage).slice(0, 4).map(st => (
                    <TouchableOpacity key={st} style={[s.quickStageBtn, { borderColor: STAGE_COLORS[st] }]} onPress={() => updateStage(lead.id, st)}>
                      <Text style={[s.quickStageText, { color: STAGE_COLORS[st] }]}>{STAGE_LABELS[st]}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Follow-ups Tab */}
        {tab === 'followups' && (
          <View style={s.section}>
            {followups.length === 0 ? (
              <View style={s.empty}><Ionicons name="alarm-outline" size={40} color="#CBD5E1" /><Text style={s.emptyText}>No pending follow-ups</Text></View>
            ) : followups.map(fu => {
              const isOverdue = fu.due_date < new Date().toISOString();
              return (
                <View key={fu.id} style={[s.fuCard, isOverdue && s.fuCardOverdue]}>
                  <View style={s.fuHeader}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.fuLead}>{fu.lead?.name || 'Unknown'}</Text>
                      <Text style={s.fuNote}>{fu.note}</Text>
                    </View>
                    <TouchableOpacity style={s.fuCompleteBtn} onPress={() => completeFollowup(fu.id)}>
                      <Ionicons name="checkmark-circle" size={28} color="#10B981" />
                    </TouchableOpacity>
                  </View>
                  <View style={s.fuMeta}>
                    <Ionicons name={fu.follow_up_type === 'call' ? 'call' : fu.follow_up_type === 'email' ? 'mail' : 'calendar'} size={13} color="#94A3B8" />
                    <Text style={[s.fuDate, isOverdue && { color: '#EF4444', fontWeight: '600' }]}>
                      {isOverdue ? 'OVERDUE' : ''} {fu.due_date?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2})/, '$3-$2-$1')}
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* Activity Tab */}
        {tab === 'activity' && (
          <View style={s.section}>
            {activities.length === 0 ? (
              <View style={s.empty}><Ionicons name="time-outline" size={40} color="#CBD5E1" /><Text style={s.emptyText}>No activities yet</Text></View>
            ) : activities.map((act, i) => (
              <View key={act.id || i} style={s.actCard}>
                <View style={[s.actDot, { backgroundColor: act.activity_type === 'status_change' ? '#C5964A' : act.activity_type === 'lead_created' ? '#3B82F6' : '#94A3B8' }]} />
                <View style={{ flex: 1 }}>
                  <Text style={s.actDesc}>{act.description}</Text>
                  <Text style={s.actTime}>{act.created_by_name || act.created_by} · {act.created_at?.split('T')[0]?.replace(/(\d{4})-(\d{2})-(\d{2})/, '$3-$2-$1')}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Analytics Tab */}
        {tab === 'analytics' && (
          <View style={s.section}>
            {!analytics ? <ActivityIndicator size="large" color="#C5964A" /> : (
              <>
                {/* Revenue Stats */}
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Revenue</Text>
                <View style={s.summaryRow}>
                  <View style={[s.summaryCard, { borderLeftColor: '#10B981' }]}>
                    <Text style={s.summaryNum}>Rs.{(analytics.summary?.total_revenue / 100000).toFixed(1)}L</Text>
                    <Text style={s.summaryLabel}>Total</Text>
                  </View>
                  <View style={[s.summaryCard, { borderLeftColor: '#C5964A' }]}>
                    <Text style={s.summaryNum}>Rs.{(analytics.summary?.monthly_revenue / 100000).toFixed(1)}L</Text>
                    <Text style={s.summaryLabel}>This Month</Text>
                  </View>
                  <View style={[s.summaryCard, { borderLeftColor: '#3B82F6' }]}>
                    <Text style={s.summaryNum}>{analytics.summary?.conversion_rate}%</Text>
                    <Text style={s.summaryLabel}>Conv. Rate</Text>
                  </View>
                </View>

                {/* Revenue Trend */}
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginTop: 14, marginBottom: 8 }}>Revenue Trend (6 Months)</Text>
                <View style={{ backgroundColor: 'rgba(255,255,255,0.78)', borderRadius: 14, padding: 14, marginBottom: 14 }}>
                  {revenueTrend.map((m: any, i: number) => {
                    const maxRev = Math.max(...revenueTrend.map((t: any) => t.revenue || 1));
                    const barWidth = maxRev > 0 ? Math.max((m.revenue / maxRev) * 100, 2) : 2;
                    return (
                      <View key={i} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
                        <Text style={{ width: 40, fontSize: 11, color: '#64748B' }}>{m.month}</Text>
                        <View style={{ flex: 1, height: 18, backgroundColor: '#F1F5F9', borderRadius: 4, overflow: 'hidden' }}>
                          <View style={{ width: `${barWidth}%`, height: '100%', backgroundColor: m.revenue > 0 ? '#C5964A' : '#E2E8F0', borderRadius: 4 }} />
                        </View>
                        <Text style={{ width: 70, fontSize: 10, color: '#0F172A', fontWeight: '600', textAlign: 'right' }}>{m.revenue > 0 ? `Rs.${(m.revenue / 1000).toFixed(0)}K` : '-'}</Text>
                      </View>
                    );
                  })}
                </View>

                {/* Order Pipeline */}
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Order Pipeline</Text>
                {orderStats && (
                  <View style={{ backgroundColor: 'rgba(255,255,255,0.78)', borderRadius: 14, padding: 14, marginBottom: 14 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text style={{ fontSize: 13, color: '#64748B' }}>Total Orders</Text>
                      <Text style={{ fontSize: 16, fontWeight: '800', color: '#0F172A' }}>{orderStats.total_orders}</Text>
                    </View>
                    {Object.entries(orderStats.by_stage || {}).map(([stage, data]: [string, any]) => (
                      <View key={stage} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: 'rgba(226,232,240,0.4)' }}>
                        <Text style={{ fontSize: 12, color: '#475569', textTransform: 'capitalize' }}>{stage.replace('_', ' ')}</Text>
                        <View style={{ flexDirection: 'row', gap: 12 }}>
                          <Text style={{ fontSize: 12, fontWeight: '600' }}>{data.count} orders</Text>
                          <Text style={{ fontSize: 12, color: '#C5964A', fontWeight: '600' }}>Rs.{(data.value / 1000).toFixed(0)}K</Text>
                        </View>
                      </View>
                    ))}
                    {/* Payment Status */}
                    <Text style={{ fontSize: 11, fontWeight: '700', color: '#0F172A', marginTop: 10, marginBottom: 4 }}>Payment Status</Text>
                    {Object.entries(orderStats.by_payment || {}).map(([status, data]: [string, any]) => (
                      <View key={status} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 }}>
                        <Text style={{ fontSize: 12, color: status === 'unpaid' ? '#EF4444' : status === 'partial' ? '#F59E0B' : '#10B981', fontWeight: '600', textTransform: 'capitalize' }}>{status}</Text>
                        <Text style={{ fontSize: 12, fontWeight: '600' }}>{data.count} | Rs.{(data.outstanding / 1000).toFixed(0)}K due</Text>
                      </View>
                    ))}
                  </View>
                )}

                {/* Production Stats */}
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Production (Work Orders)</Text>
                {woStats && (
                  <View style={{ backgroundColor: 'rgba(255,255,255,0.78)', borderRadius: 14, padding: 14, marginBottom: 14 }}>
                    <Text style={{ fontSize: 18, fontWeight: '800', color: '#0F172A', marginBottom: 8 }}>{woStats.total} Total WOs</Text>
                    {Object.entries(woStats.by_stage || {}).map(([stage, count]: [string, any]) => (
                      <View key={stage} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 }}>
                        <Text style={{ fontSize: 12, color: '#475569', textTransform: 'capitalize' }}>{stage.replace('_', ' ')}</Text>
                        <Text style={{ fontSize: 14, fontWeight: '700', color: '#0F172A' }}>{count}</Text>
                      </View>
                    ))}
                  </View>
                )}

                {/* Quick Stats */}
                <Text style={{ fontSize: 12, fontWeight: '700', color: '#C5964A', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Overview</Text>
                <View style={{ backgroundColor: 'rgba(255,255,255,0.78)', borderRadius: 14, padding: 14 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}><Text style={{ fontSize: 12, color: '#64748B' }}>Total Quotes</Text><Text style={{ fontSize: 14, fontWeight: '700' }}>{analytics.summary?.total_quotes}</Text></View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}><Text style={{ fontSize: 12, color: '#64748B' }}>Approved</Text><Text style={{ fontSize: 14, fontWeight: '700', color: '#10B981' }}>{analytics.summary?.approved_quotes}</Text></View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}><Text style={{ fontSize: 12, color: '#64748B' }}>Pending RFQs</Text><Text style={{ fontSize: 14, fontWeight: '700', color: '#F59E0B' }}>{analytics.summary?.pending_rfqs}</Text></View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}><Text style={{ fontSize: 12, color: '#64748B' }}>Customers</Text><Text style={{ fontSize: 14, fontWeight: '700' }}>{analytics.summary?.total_customers}</Text></View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 }}><Text style={{ fontSize: 12, color: '#64748B' }}>Avg Quote Value</Text><Text style={{ fontSize: 14, fontWeight: '700', color: '#C5964A' }}>Rs.{analytics.summary?.avg_quote_value?.toLocaleString()}</Text></View>
                </View>
              </>
            )}
          </View>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* Add Lead Modal */}
      <Modal visible={showAddLead} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modal}>
            <View style={s.modalHeader}>
              <Text style={s.modalTitle}>New Lead</Text>
              <TouchableOpacity onPress={() => setShowAddLead(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
            </View>
            <ScrollView style={s.modalScroll}>
              <Text style={s.fieldLabel}>Name *</Text>
              <TextInput style={s.fieldInput} value={newLead.name} onChangeText={v => setNewLead({ ...newLead, name: v })} placeholder="Lead name" />
              <Text style={s.fieldLabel}>Company</Text>
              <TextInput style={s.fieldInput} value={newLead.company} onChangeText={v => setNewLead({ ...newLead, company: v })} placeholder="Company name" />
              <Text style={s.fieldLabel}>Email</Text>
              <TextInput style={s.fieldInput} value={newLead.email} onChangeText={v => setNewLead({ ...newLead, email: v })} placeholder="Email" keyboardType="email-address" />
              <Text style={s.fieldLabel}>Phone</Text>
              <TextInput style={s.fieldInput} value={newLead.phone} onChangeText={v => setNewLead({ ...newLead, phone: v })} placeholder="Phone" keyboardType="phone-pad" />
              <Text style={s.fieldLabel}>Source</Text>
              <View style={s.chipRow}>{SOURCES.map(src => (
                <TouchableOpacity key={src} style={[s.srcChip, newLead.source === src && s.srcChipActive]} onPress={() => setNewLead({ ...newLead, source: src })}>
                  <Text style={[s.srcChipText, newLead.source === src && s.srcChipTextActive]}>{SOURCE_LABELS[src]}</Text>
                </TouchableOpacity>
              ))}</View>
              <Text style={s.fieldLabel}>Estimated Value (Rs.)</Text>
              <TextInput style={s.fieldInput} value={newLead.estimated_value} onChangeText={v => setNewLead({ ...newLead, estimated_value: v })} placeholder="50000" keyboardType="numeric" />
              <Text style={s.fieldLabel}>Notes</Text>
              <TextInput style={[s.fieldInput, { height: 70, textAlignVertical: 'top' }]} value={newLead.notes} onChangeText={v => setNewLead({ ...newLead, notes: v })} placeholder="Notes..." multiline />
            </ScrollView>
            <TouchableOpacity style={s.modalBtn} onPress={createLead}><Ionicons name="add-circle" size={20} color="#fff" /><Text style={s.modalBtnText}>Create Lead</Text></TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Add Follow-up Modal */}
      <Modal visible={showAddFollowup} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modal}>
            <View style={s.modalHeader}>
              <Text style={s.modalTitle}>Follow-up: {selectedLead?.name}</Text>
              <TouchableOpacity onPress={() => setShowAddFollowup(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
            </View>
            <Text style={s.fieldLabel}>Type</Text>
            <View style={s.chipRow}>{FU_TYPES.map(t => (
              <TouchableOpacity key={t} style={[s.srcChip, newFU.follow_up_type === t && s.srcChipActive]} onPress={() => setNewFU({ ...newFU, follow_up_type: t })}>
                <Text style={[s.srcChipText, newFU.follow_up_type === t && s.srcChipTextActive]}>{t.charAt(0).toUpperCase() + t.slice(1)}</Text>
              </TouchableOpacity>
            ))}</View>
            <Text style={s.fieldLabel}>Due Date (DD-MM-YYYY)</Text>
            <TextInput style={s.fieldInput} value={newFU.due_date} onChangeText={v => setNewFU({ ...newFU, due_date: v })} placeholder="15-05-2026" />
            <Text style={s.fieldLabel}>Note</Text>
            <TextInput style={[s.fieldInput, { height: 70, textAlignVertical: 'top' }]} value={newFU.note} onChangeText={v => setNewFU({ ...newFU, note: v })} placeholder="Follow-up details..." multiline />
            <TouchableOpacity style={s.modalBtn} onPress={createFollowup}><Ionicons name="alarm" size={20} color="#fff" /><Text style={s.modalBtnText}>Schedule Follow-up</Text></TouchableOpacity>
          </View>
        </View>
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
  addBtn: { width: 38, height: 38, borderRadius: 19, backgroundColor: '#C5964A', justifyContent: 'center', alignItems: 'center' },
  scroll: { flex: 1 },
  summaryRow: { flexDirection: 'row', paddingHorizontal: 14, paddingTop: 16, gap: 8 },
  summaryCard: { flex: 1, backgroundColor: 'rgba(255,255,255,0.78)', borderRadius: 14, padding: 14, borderLeftWidth: 3, shadowColor: '#0F172A', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.04, shadowRadius: 10, elevation: 2 },
  summaryNum: { fontSize: 22, fontWeight: '800', color: '#0F172A' },
  summaryLabel: { fontSize: 11, color: '#94A3B8', fontWeight: '600', marginTop: 2 },
  tabBar: { flexDirection: 'row', marginHorizontal: 14, marginTop: 16, backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: 12, padding: 3 },
  tab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, paddingVertical: 10, borderRadius: 10 },
  tabActive: { backgroundColor: '#fff', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 },
  tabText: { fontSize: 13, fontWeight: '500', color: '#94A3B8' },
  tabTextActive: { color: '#C5964A', fontWeight: '700' },
  badge: { backgroundColor: '#EF4444', borderRadius: 8, minWidth: 16, height: 16, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 4 },
  badgeText: { color: '#fff', fontSize: 10, fontWeight: '700' },
  section: { padding: 14 },
  stageFilterRow: { marginBottom: 12 },
  stageChip: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 20, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: 'rgba(255,255,255,0.7)', marginRight: 8 },
  stageChipActive: { backgroundColor: '#C5964A', borderColor: '#C5964A' },
  stageChipText: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  stageChipTextActive: { color: '#fff' },
  stageDot: { width: 7, height: 7, borderRadius: 4 },
  empty: { alignItems: 'center', paddingVertical: 40 },
  emptyText: { fontSize: 14, color: '#94A3B8', marginTop: 8 },
  leadCard: { backgroundColor: 'rgba(255,255,255,0.82)', borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.35)', shadowColor: '#0F172A', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.04, shadowRadius: 12, elevation: 2 },
  leadHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  leadName: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
  leadCompany: { fontSize: 13, color: '#64748B', marginTop: 2 },
  leadStageBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  leadStageText: { fontSize: 11, fontWeight: '700' },
  leadMeta: { flexDirection: 'row', gap: 14, marginTop: 10, flexWrap: 'wrap' },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { fontSize: 12, color: '#64748B' },
  quickStages: { flexDirection: 'row', gap: 6, marginTop: 12, flexWrap: 'wrap' },
  quickStageBtn: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 6, borderWidth: 1 },
  quickStageText: { fontSize: 11, fontWeight: '600' },
  fuCard: { backgroundColor: 'rgba(255,255,255,0.82)', borderRadius: 14, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.3)' },
  fuCardOverdue: { borderLeftWidth: 3, borderLeftColor: '#EF4444' },
  fuHeader: { flexDirection: 'row', alignItems: 'center' },
  fuLead: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  fuNote: { fontSize: 13, color: '#64748B', marginTop: 3 },
  fuCompleteBtn: { padding: 4 },
  fuMeta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  fuDate: { fontSize: 12, color: '#94A3B8', fontWeight: '500' },
  actCard: { flexDirection: 'row', alignItems: 'flex-start', gap: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(226,232,240,0.4)' },
  actDot: { width: 10, height: 10, borderRadius: 5, marginTop: 4 },
  actDesc: { fontSize: 14, color: '#0F172A', fontWeight: '500' },
  actTime: { fontSize: 11, color: '#94A3B8', marginTop: 3 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 22, maxHeight: '85%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  modalScroll: { maxHeight: 400 },
  fieldLabel: { fontSize: 12, fontWeight: '600', color: '#C5964A', letterSpacing: 0.5, marginBottom: 6, marginTop: 14 },
  fieldInput: { backgroundColor: 'rgba(241,245,249,0.8)', borderWidth: 1, borderColor: 'rgba(226,232,240,0.5)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#0F172A' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  srcChip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 8, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#F8FAFC' },
  srcChipActive: { backgroundColor: '#960018', borderColor: '#960018' },
  srcChipText: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  srcChipTextActive: { color: '#fff' },
  modalBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#960018', borderRadius: 14, paddingVertical: 15, marginTop: 18, shadowColor: '#960018', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 10, elevation: 4 },
  modalBtnText: { fontSize: 15, fontWeight: '700', color: '#fff' },
});
