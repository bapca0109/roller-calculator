import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, Modal, TouchableOpacity, ScrollView, TextInput, Alert, ActivityIndicator, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { confirmAction } from '../shared/confirm';

const API_BASE = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api`;
const makeApi = async () => {
  const token = await AsyncStorage.getItem('token');
  return axios.create({
    baseURL: API_BASE,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
};

type PipeRecord = {
  item_index: number;
  product_name: string;
  required_dia: any;
  required_length: any;
  required_thickness: any;
  quantity: number;
  sample_qty: string;
  samples: any[];
};

type ShaftRecord = {
  item_index: number;
  product_name: string;
  required_dia: any;
  required_length: any;
  required_width: any;
  required_dim: any;
  slot_type: string;
  slot_meta: any;
  quantity: number;
  sample_qty: string;
  samples: any[];
};

interface UsePipeQCResult {
  open: (subId: string, subWoNumber: string) => Promise<void>;
  render: () => React.ReactElement;
}

export function usePipeQC(onSaved?: () => void): UsePipeQCResult {
  const [visible, setVisible] = useState(false);
  const [sub, setSub] = useState<any>(null);
  const [records, setRecords] = useState<PipeRecord[]>([]);
  const [saving, setSaving] = useState(false);

  const open = useCallback(async (subId: string, subWoNumber: string) => {
    try {
      const api = await makeApi();
      const res = await api.get(`/sub-work-orders/${subId}/wip-qc`);
      const existing = res.data.wip_qc?.items || [];
      const recs: PipeRecord[] = (res.data.items || []).map((it: any, idx: number) => {
        const prev = existing.find((e: any) => e.item_index === idx);
        return {
          item_index: idx,
          product_name: it.product_name,
          required_dia: it.pipe_diameter,
          required_length: it.pipe_length,
          required_thickness: it.pipe_thickness,
          quantity: it.quantity,
          sample_qty: prev?.sample_qty ? String(prev.sample_qty) : '',
          samples: prev?.samples || [],
        };
      });
      setSub({ id: subId, sub_wo_number: subWoNumber });
      setRecords(recs);
      setVisible(true);
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to load Pipe QC');
    }
  }, []);

  const updateSampleQty = (idx: number, qtyStr: string) => {
    const n = parseInt(qtyStr.replace(/[^0-9]/g, '') || '0');
    const arr = [...records];
    arr[idx].sample_qty = qtyStr.replace(/[^0-9]/g, '');
    const current = arr[idx].samples || [];
    if (n > current.length) {
      for (let s = current.length; s < n; s++) current.push({ sample_no: s + 1, pipe_dia_ok: null, pipe_dia_remarks: '', pipe_length_measured: '', pipe_length_remarks: '', pipe_thickness_measured: '', pipe_thickness_remarks: '' });
    } else current.length = n;
    arr[idx].samples = current;
    setRecords(arr);
  };
  const setField = (i: number, si: number, f: string, v: any) => {
    const arr = [...records];
    arr[i].samples[si] = { ...arr[i].samples[si], [f]: v };
    setRecords(arr);
  };
  const inLen = (v: any, r: number) => { const n = parseFloat(v); if (isNaN(n) || !r) return null; return Math.abs(n - r) <= 1; };
  const inThk = (v: any, r: number) => { const n = parseFloat(v); if (isNaN(n) || !r) return null; return Math.abs(n - r) <= r * 0.1; };

  const submit = async () => {
    if (!sub) return;
    const payload = records.filter(r => parseInt(r.sample_qty || '0') > 0).map(r => ({
      item_index: r.item_index,
      sample_qty: parseInt(r.sample_qty),
      samples: r.samples.map((s: any, i: number) => ({
        sample_no: i + 1,
        pipe_dia_ok: s.pipe_dia_ok === null ? false : !!s.pipe_dia_ok,
        pipe_dia_remarks: s.pipe_dia_remarks || null,
        pipe_length_measured: s.pipe_length_measured !== '' ? parseFloat(s.pipe_length_measured) : null,
        pipe_length_remarks: s.pipe_length_remarks || null,
        pipe_thickness_measured: s.pipe_thickness_measured !== '' ? parseFloat(s.pipe_thickness_measured) : null,
        pipe_thickness_remarks: s.pipe_thickness_remarks || null,
      })),
    }));
    if (payload.length === 0) { Alert.alert('Error', 'Enter sample qty for at least one item'); return; }
    if (!(await confirmAction('Save Pipe WIP QC?', `QC results will be stored against ${sub.sub_wo_number}.`))) return;
    try {
      setSaving(true);
      const api = await makeApi();
      const res = await api.post(`/sub-work-orders/${sub.id}/wip-qc`, { items: payload });
      Alert.alert('Success', res.data.message);
      setVisible(false);
      onSaved && onSaved();
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed');
    } finally { setSaving(false); }
  };

  const render = () => (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={m.overlay}>
        <View style={m.modal}>
          <View style={m.head}>
            <View>
              <Text style={m.title}>Pipe WIP QC</Text>
              {sub && <Text style={[m.sub, { color: '#8B5CF6' }]}>{sub.sub_wo_number}</Text>}
            </View>
            <TouchableOpacity onPress={() => setVisible(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
          </View>
          <ScrollView style={{ maxHeight: 600 }}>
            {records.map((rec, idx) => {
              const n = parseInt(rec.sample_qty || '0');
              return (
                <View key={idx} style={m.itemBlock}>
                  <Text style={m.itemTitle}>Item {idx + 1}: {rec.product_name}</Text>
                  <View style={m.metaRow}>
                    <Text style={m.metaLabel}>Req Dia: <Text style={m.metaVal}>{rec.required_dia} mm</Text></Text>
                    <Text style={m.metaLabel}>Req Length: <Text style={m.metaVal}>{rec.required_length} mm</Text> (±1)</Text>
                    <Text style={m.metaLabel}>Req Thk: <Text style={m.metaVal}>{rec.required_thickness} mm</Text> (±10%)</Text>
                    <Text style={m.metaLabel}>Qty: <Text style={m.metaVal}>{rec.quantity}</Text></Text>
                  </View>
                  <View style={m.qtyRow}>
                    <Text style={[m.qtyLabel, { color: '#8B5CF6' }]}>Sample Qty:</Text>
                    <TextInput data-testid={`pqc-sample-qty-${idx}`} style={m.qtyInput} value={rec.sample_qty} onChangeText={(v) => updateSampleQty(idx, v)} keyboardType="numeric" placeholder="0" />
                    <Text style={m.qtySub}>(out of {rec.quantity})</Text>
                  </View>
                  {n > 0 && rec.samples.slice(0, n).map((s: any, si: number) => {
                    const lenOk = inLen(s.pipe_length_measured, rec.required_length);
                    const thkOk = inThk(s.pipe_thickness_measured, rec.required_thickness);
                    return (
                      <View key={si} style={[m.sampleCard, { borderLeftColor: '#8B5CF6' }]}>
                        <Text style={m.sampleTitle}>Sample {si + 1}</Text>
                        <View style={{ marginBottom: 8 }}>
                          <Text style={m.fieldLabel}>Pipe Dia = {rec.required_dia} mm — match?</Text>
                          <View style={{ flexDirection: 'row', gap: 6 }}>
                            <Pressable onPress={() => setField(idx, si, 'pipe_dia_ok', true)} style={[m.chip, s.pipe_dia_ok === true && m.chipOk]}><Text style={[m.chipText, s.pipe_dia_ok === true && m.chipOkText]}>Yes</Text></Pressable>
                            <Pressable onPress={() => setField(idx, si, 'pipe_dia_ok', false)} style={[m.chip, s.pipe_dia_ok === false && m.chipBad]}><Text style={[m.chipText, s.pipe_dia_ok === false && m.chipBadText]}>No</Text></Pressable>
                          </View>
                          {s.pipe_dia_ok === false && (<TextInput style={m.remark} placeholder="Reason" value={s.pipe_dia_remarks} onChangeText={(v) => setField(idx, si, 'pipe_dia_remarks', v)} />)}
                        </View>
                        <View style={{ marginBottom: 8 }}>
                          <Text style={m.fieldLabel}>Pipe Length = {rec.required_length} mm (±1)</Text>
                          <TextInput style={[m.num, lenOk === true && m.numOk, lenOk === false && m.numBad]} placeholder={`e.g. ${rec.required_length}`} value={String(s.pipe_length_measured ?? '')} onChangeText={(v) => setField(idx, si, 'pipe_length_measured', v)} keyboardType="numeric" />
                          {lenOk === false && (<TextInput style={m.remark} placeholder="Reason" value={s.pipe_length_remarks} onChangeText={(v) => setField(idx, si, 'pipe_length_remarks', v)} />)}
                        </View>
                        <View>
                          <Text style={m.fieldLabel}>Pipe Thk = {rec.required_thickness} mm (±10%)</Text>
                          <TextInput style={[m.num, thkOk === true && m.numOk, thkOk === false && m.numBad]} placeholder={`e.g. ${rec.required_thickness}`} value={String(s.pipe_thickness_measured ?? '')} onChangeText={(v) => setField(idx, si, 'pipe_thickness_measured', v)} keyboardType="numeric" />
                          {thkOk === false && (<TextInput style={m.remark} placeholder="Reason" value={s.pipe_thickness_remarks} onChangeText={(v) => setField(idx, si, 'pipe_thickness_remarks', v)} />)}
                        </View>
                      </View>
                    );
                  })}
                </View>
              );
            })}
          </ScrollView>
          <TouchableOpacity style={[m.saveBtn, { backgroundColor: '#8B5CF6', opacity: saving ? 0.6 : 1 }]} onPress={submit}>
            {saving ? <ActivityIndicator color="#fff" /> : <><Ionicons name="clipboard" size={18} color="#fff" /><Text style={m.saveText}>Save Pipe WIP QC</Text></>}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  return { open, render };
}

interface UseShaftQCResult {
  open: (subId: string, subWoNumber: string) => Promise<void>;
  render: () => React.ReactElement;
}

export function useShaftQC(onSaved?: () => void): UseShaftQCResult {
  const [visible, setVisible] = useState(false);
  const [sub, setSub] = useState<any>(null);
  const [records, setRecords] = useState<ShaftRecord[]>([]);
  const [saving, setSaving] = useState(false);

  const open = useCallback(async (subId: string, subWoNumber: string) => {
    try {
      const api = await makeApi();
      const res = await api.get(`/sub-work-orders/${subId}/wip-qc`);
      const existing = res.data.wip_qc?.items || [];
      const recs: ShaftRecord[] = (res.data.items || []).map((it: any, idx: number) => {
        const prev = existing.find((e: any) => e.item_index === idx);
        const slot = it.shaft_slot_details || {};
        return {
          item_index: idx,
          product_name: it.product_name,
          required_dia: it.shaft_diameter,
          required_length: it.shaft_length,
          required_width: slot.width,
          required_dim: slot.dimension,
          slot_type: slot.slot_type,
          slot_meta: it.slot_meta || { kind: null, third_label: null, third_required: null, third_tol: null },
          quantity: it.quantity,
          sample_qty: prev?.sample_qty ? String(prev.sample_qty) : '',
          samples: prev?.samples || [],
        };
      });
      setSub({ id: subId, sub_wo_number: subWoNumber });
      setRecords(recs);
      setVisible(true);
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to load Shaft QC');
    }
  }, []);

  const updateSampleQty = (idx: number, qtyStr: string) => {
    const n = parseInt(qtyStr.replace(/[^0-9]/g, '') || '0');
    const arr = [...records];
    arr[idx].sample_qty = qtyStr.replace(/[^0-9]/g, '');
    const current = arr[idx].samples || [];
    if (n > current.length) {
      for (let s = current.length; s < n; s++) current.push({ sample_no: s + 1, shaft_dia_ok: null, shaft_dia_remarks: '', shaft_length_measured: '', shaft_length_remarks: '', slot_width_measured: '', slot_width_remarks: '', slot_dimension_measured: '', slot_dimension_remarks: '', slot_third_measured: '', slot_third_remarks: '' });
    } else current.length = n;
    arr[idx].samples = current;
    setRecords(arr);
  };
  const setField = (i: number, si: number, f: string, v: any) => {
    const arr = [...records];
    arr[i].samples[si] = { ...arr[i].samples[si], [f]: v };
    setRecords(arr);
  };
  const inLen = (v: any, r: number) => { const n = parseFloat(v); if (isNaN(n) || !r) return null; return Math.abs(n - r) <= 1; };
  const inW = (v: any, r: number) => { const n = parseFloat(v); if (isNaN(n) || !r) return null; return n <= r && n >= r - 0.2; };
  const inD = (v: any, r: number) => { const n = parseFloat(v); if (isNaN(n) || !r) return null; return Math.abs(n - r) <= 0.5; };
  const inT = (v: any, r: number, tol: number) => { const n = parseFloat(v); if (isNaN(n) || !r) return null; return Math.abs(n - r) <= tol; };

  const submit = async () => {
    if (!sub) return;
    const payload = records.filter(r => parseInt(r.sample_qty || '0') > 0).map(r => ({
      item_index: r.item_index,
      sample_qty: parseInt(r.sample_qty),
      samples: r.samples.map((s: any, i: number) => ({
        sample_no: i + 1,
        shaft_dia_ok: s.shaft_dia_ok === null ? false : !!s.shaft_dia_ok,
        shaft_dia_remarks: s.shaft_dia_remarks || null,
        shaft_length_measured: s.shaft_length_measured !== '' ? parseFloat(s.shaft_length_measured) : null,
        shaft_length_remarks: s.shaft_length_remarks || null,
        slot_width_measured: s.slot_width_measured !== '' ? parseFloat(s.slot_width_measured) : null,
        slot_width_remarks: s.slot_width_remarks || null,
        slot_dimension_measured: s.slot_dimension_measured !== '' ? parseFloat(s.slot_dimension_measured) : null,
        slot_dimension_remarks: s.slot_dimension_remarks || null,
        slot_third_measured: s.slot_third_measured !== '' ? parseFloat(s.slot_third_measured) : null,
        slot_third_remarks: s.slot_third_remarks || null,
      })),
    }));
    if (payload.length === 0) { Alert.alert('Error', 'Enter sample qty for at least one item'); return; }
    if (!(await confirmAction('Save Shaft WIP QC?', `QC results will be stored against ${sub.sub_wo_number}.`))) return;
    try {
      setSaving(true);
      const api = await makeApi();
      const res = await api.post(`/sub-work-orders/${sub.id}/wip-qc`, { items: payload });
      Alert.alert('Success', res.data.message);
      setVisible(false);
      onSaved && onSaved();
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed');
    } finally { setSaving(false); }
  };

  const render = () => (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={m.overlay}>
        <View style={m.modal}>
          <View style={m.head}>
            <View>
              <Text style={m.title}>Shaft WIP QC</Text>
              {sub && <Text style={[m.sub, { color: '#0891B2' }]}>{sub.sub_wo_number}</Text>}
            </View>
            <TouchableOpacity onPress={() => setVisible(false)}><Ionicons name="close" size={24} color="#64748B" /></TouchableOpacity>
          </View>
          <ScrollView style={{ maxHeight: 600 }}>
            {records.map((rec, idx) => {
              const n = parseInt(rec.sample_qty || '0');
              const meta = rec.slot_meta || {};
              const showT = !!meta.third_label && meta.third_required != null;
              const tTol = meta.third_tol || 0.5;
              return (
                <View key={idx} style={m.itemBlock}>
                  <Text style={m.itemTitle}>Item {idx + 1}: {rec.product_name}</Text>
                  <View style={m.metaRow}>
                    <Text style={m.metaLabel}>Req Dia: <Text style={m.metaVal}>{rec.required_dia} mm</Text></Text>
                    <Text style={m.metaLabel}>Req Length: <Text style={m.metaVal}>{rec.required_length} mm</Text> (±1)</Text>
                    {rec.slot_type ? (<Text style={m.metaLabel}>End: <Text style={m.metaVal}>{rec.required_width}×{rec.required_dim}{showT ? `×${meta.third_required}` : ''} {rec.slot_type}</Text></Text>) : null}
                    <Text style={m.metaLabel}>Qty: <Text style={m.metaVal}>{rec.quantity}</Text></Text>
                  </View>
                  <View style={m.qtyRow}>
                    <Text style={[m.qtyLabel, { color: '#0891B2' }]}>Sample Qty:</Text>
                    <TextInput data-testid={`sqc-sample-qty-${idx}`} style={m.qtyInput} value={rec.sample_qty} onChangeText={(v) => updateSampleQty(idx, v)} keyboardType="numeric" placeholder="0" />
                    <Text style={m.qtySub}>(out of {rec.quantity})</Text>
                  </View>
                  {n > 0 && rec.samples.slice(0, n).map((s: any, si: number) => {
                    const lenOk = inLen(s.shaft_length_measured, rec.required_length);
                    const wOk = inW(s.slot_width_measured, rec.required_width);
                    const dOk = inD(s.slot_dimension_measured, rec.required_dim);
                    const tOk = showT ? inT(s.slot_third_measured, meta.third_required, tTol) : null;
                    return (
                      <View key={si} style={[m.sampleCard, { borderLeftColor: '#0891B2' }]}>
                        <Text style={m.sampleTitle}>Sample {si + 1}</Text>
                        <View style={{ marginBottom: 8 }}>
                          <Text style={m.fieldLabel}>Shaft Dia = {rec.required_dia} mm — match?</Text>
                          <View style={{ flexDirection: 'row', gap: 6 }}>
                            <Pressable onPress={() => setField(idx, si, 'shaft_dia_ok', true)} style={[m.chip, s.shaft_dia_ok === true && m.chipOk]}><Text style={[m.chipText, s.shaft_dia_ok === true && m.chipOkText]}>Yes</Text></Pressable>
                            <Pressable onPress={() => setField(idx, si, 'shaft_dia_ok', false)} style={[m.chip, s.shaft_dia_ok === false && m.chipBad]}><Text style={[m.chipText, s.shaft_dia_ok === false && m.chipBadText]}>No</Text></Pressable>
                          </View>
                          {s.shaft_dia_ok === false && (<TextInput style={m.remark} placeholder="Reason" value={s.shaft_dia_remarks} onChangeText={(v) => setField(idx, si, 'shaft_dia_remarks', v)} />)}
                        </View>
                        <View style={{ marginBottom: 8 }}>
                          <Text style={m.fieldLabel}>Shaft Length = {rec.required_length} mm (±1)</Text>
                          <TextInput style={[m.num, lenOk === true && m.numOk, lenOk === false && m.numBad]} placeholder={`e.g. ${rec.required_length}`} value={String(s.shaft_length_measured ?? '')} onChangeText={(v) => setField(idx, si, 'shaft_length_measured', v)} keyboardType="numeric" />
                          {lenOk === false && (<TextInput style={m.remark} placeholder="Reason" value={s.shaft_length_remarks} onChangeText={(v) => setField(idx, si, 'shaft_length_remarks', v)} />)}
                        </View>
                        {rec.required_width ? (
                          <>
                            <Text style={[m.sectionLabel, { color: '#0891B2' }]}>End Slot ({rec.slot_type})</Text>
                            <View style={{ marginBottom: 8 }}>
                              <Text style={m.fieldLabel}>Width = {rec.required_width} mm (-0.2 / +0)</Text>
                              <TextInput style={[m.num, wOk === true && m.numOk, wOk === false && m.numBad]} value={String(s.slot_width_measured ?? '')} onChangeText={(v) => setField(idx, si, 'slot_width_measured', v)} keyboardType="numeric" />
                              {wOk === false && (<TextInput style={m.remark} placeholder="Reason" value={s.slot_width_remarks} onChangeText={(v) => setField(idx, si, 'slot_width_remarks', v)} />)}
                            </View>
                            <View style={{ marginBottom: 8 }}>
                              <Text style={m.fieldLabel}>Dimension (D) = {rec.required_dim} mm (±0.5)</Text>
                              <TextInput style={[m.num, dOk === true && m.numOk, dOk === false && m.numBad]} value={String(s.slot_dimension_measured ?? '')} onChangeText={(v) => setField(idx, si, 'slot_dimension_measured', v)} keyboardType="numeric" />
                              {dOk === false && (<TextInput style={m.remark} placeholder="Reason" value={s.slot_dimension_remarks} onChangeText={(v) => setField(idx, si, 'slot_dimension_remarks', v)} />)}
                            </View>
                            {showT && (
                              <View>
                                <Text style={m.fieldLabel}>{meta.third_label} = {meta.third_required} mm (±{tTol})</Text>
                                <TextInput style={[m.num, tOk === true && m.numOk, tOk === false && m.numBad]} value={String(s.slot_third_measured ?? '')} onChangeText={(v) => setField(idx, si, 'slot_third_measured', v)} keyboardType="numeric" />
                                {tOk === false && (<TextInput style={m.remark} placeholder="Reason" value={s.slot_third_remarks} onChangeText={(v) => setField(idx, si, 'slot_third_remarks', v)} />)}
                              </View>
                            )}
                          </>
                        ) : null}
                      </View>
                    );
                  })}
                </View>
              );
            })}
          </ScrollView>
          <TouchableOpacity style={[m.saveBtn, { backgroundColor: '#0891B2', opacity: saving ? 0.6 : 1 }]} onPress={submit}>
            {saving ? <ActivityIndicator color="#fff" /> : <><Ionicons name="clipboard" size={18} color="#fff" /><Text style={m.saveText}>Save Shaft WIP QC</Text></>}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  return { open, render };
}

// ─────────────────────── Final Inspection ────────────────────────

export function useFinalInspection(params?: { onSaved?: () => void }) {
  const { onSaved } = params || {};
  const [show, setShow] = useState(false);
  const [wo, setWo] = useState<any>(null);
  const [ctx, setCtx] = useState<any>(null);
  const [applicable, setApplicable] = useState<any>({ runout: true, water: true, dust: true, friction: true, painting: true });
  const [items, setItems] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  const open = useCallback(async (workOrder: any) => {
    setShow(true);
    setWo(workOrder);
    setCtx(null);
    setItems([]);
    setLoading(true);
    try {
      const api = await makeApi();
      const { data } = await api.get(`/work-orders/${workOrder.id}/final-inspection`);
      setCtx(data.context);
      setApplicable(data.context?.applicable_tests || { runout: true, water: true, dust: true, friction: true, painting: true });
      const rec = data.record;
      const initItems = (data.context?.items || []).map((c: any) => {
        const existing = (rec?.items || []).find((x: any) => x.item_index === c.item_index);
        const sampleCount = Math.max(c.sample_qty || 0, existing?.sample_qty || 0);
        const prevSamples = existing?.samples || [];
        const samples = Array.from({ length: sampleCount }, (_, i) => {
          const p = prevSamples[i] || {};
          return {
            sample_no: i + 1,
            runout_mm: p.runout_mm ?? '',
            water_ok: p.water_ok ?? null,
            dust_ok: p.dust_ok ?? null,
            friction_coeff: p.friction_coeff ?? '',
            painting_visual_ok: p.painting_visual_ok ?? null,
            dft_microns: p.dft_microns ?? '',
            bearing_match: p.bearing_match ?? null,
            bearing_reason: p.bearing_reason ?? '',
            rust_preventive: p.rust_preventive ?? null,
            rust_reason: p.rust_reason ?? '',
            welding_ok: p.welding_ok ?? null,
            remarks: p.remarks ?? '',
          };
        });
        return {
          ...c,
          expected_dft_microns: existing?.expected_dft_microns ?? '',
          samples,
        };
      });
      setItems(initItems);
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || e?.message || 'Failed to load Final Inspection');
      setShow(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const close = () => setShow(false);

  const patchSample = (itemIdx: number, sampleIdx: number, field: string, value: any) => {
    setItems(prev => prev.map((it, i) => {
      if (i !== itemIdx) return it;
      const samples = it.samples.map((s: any, si: number) => si === sampleIdx ? { ...s, [field]: value } : s);
      return { ...it, samples };
    }));
  };

  const patchItem = (itemIdx: number, field: string, value: any) => {
    setItems(prev => prev.map((it, i) => (i === itemIdx ? { ...it, [field]: value } : it)));
  };

  // Inline pass/fail evaluator for UI preview (honours applicable flags)
  const evalSample = (item: any, s: any) => {
    const tol = (item.pipe_length_mm || 0) <= 1350 ? 1.6 : 2.0;
    const r = parseFloat(s.runout_mm);
    const f = parseFloat(s.friction_coeff);
    const dft = parseFloat(s.dft_microns);
    const expDft = parseFloat(item.expected_dft_microns);
    const runout_ok = !isNaN(r) && r < tol;
    const friction_ok = !isNaN(f) && f < 0.02;
    const dft_ok = !isNaN(dft) && !isNaN(expDft) && expDft > 0 && Math.abs(dft - expDft) <= expDft * 0.20;
    const checks: boolean[] = [];
    if (applicable.runout) checks.push(runout_ok);
    if (applicable.water) checks.push(s.water_ok === true);
    if (applicable.dust) checks.push(s.dust_ok === true);
    if (applicable.friction) checks.push(friction_ok);
    if (applicable.painting) { checks.push(s.painting_visual_ok === true); checks.push(dft_ok); }
    checks.push(s.bearing_match === true);
    checks.push(s.rust_preventive === true);
    checks.push(s.welding_ok === true);
    const overall = checks.every(Boolean);
    return { runout_ok, friction_ok, dft_ok, overall };
  };

  const save = async () => {
    if (!wo) return;
    const payload = {
      items: items.map(it => ({
        item_index: it.item_index,
        expected_dft_microns: it.expected_dft_microns === '' ? null : parseFloat(it.expected_dft_microns),
        samples: it.samples.map((s: any) => ({
          sample_no: s.sample_no,
          runout_mm: s.runout_mm === '' ? null : parseFloat(s.runout_mm),
          water_ok: s.water_ok,
          dust_ok: s.dust_ok,
          friction_coeff: s.friction_coeff === '' ? null : parseFloat(s.friction_coeff),
          painting_visual_ok: s.painting_visual_ok,
          dft_microns: s.dft_microns === '' ? null : parseFloat(s.dft_microns),
          bearing_match: s.bearing_match,
          bearing_reason: s.bearing_reason || '',
          rust_preventive: s.rust_preventive,
          rust_reason: s.rust_reason || '',
          welding_ok: s.welding_ok,
          remarks: s.remarks || '',
        })),
      })),
    };
    setSaving(true);
    try {
      const api = await makeApi();
      const { data } = await api.post(`/work-orders/${wo.id}/final-inspection`, payload);
      Alert.alert('Saved', data.message || 'Final Inspection saved');
      setShow(false);
      onSaved?.();
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || e?.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const downloadReport = async (kind: 'pdf' | 'excel') => {
    if (!wo) return;
    const token = await AsyncStorage.getItem('token');
    const url = `${API_BASE}/work-orders/${wo.id}/final-inspection/${kind}?token=${token}`;
    if (typeof window !== 'undefined') window.open(url, '_blank');
  };

  const YN = ({ value, onChange, testID }: any) => (
    <View style={{ flexDirection: 'row', gap: 6 }}>
      <Pressable onPress={() => onChange(true)} testID={`${testID}-yes`}
        style={[m.chip, value === true && m.chipOk]}>
        <Text style={[m.chipText, value === true && m.chipOkText]}>Yes</Text>
      </Pressable>
      <Pressable onPress={() => onChange(false)} testID={`${testID}-no`}
        style={[m.chip, value === false && m.chipBad]}>
        <Text style={[m.chipText, value === false && m.chipBadText]}>No</Text>
      </Pressable>
    </View>
  );

  const PF = ({ value, onChange, testID, labels = ['Pass', 'Fail'] }: any) => (
    <View style={{ flexDirection: 'row', gap: 6 }}>
      <Pressable onPress={() => onChange(true)} testID={`${testID}-pass`}
        style={[m.chip, value === true && m.chipOk]}>
        <Text style={[m.chipText, value === true && m.chipOkText]}>{labels[0]}</Text>
      </Pressable>
      <Pressable onPress={() => onChange(false)} testID={`${testID}-fail`}
        style={[m.chip, value === false && m.chipBad]}>
        <Text style={[m.chipText, value === false && m.chipBadText]}>{labels[1]}</Text>
      </Pressable>
    </View>
  );

  const render = () => (
    <Modal visible={show} transparent animationType="slide" onRequestClose={close}>
      <View style={m.overlay}>
        <View style={m.modal}>
          <View style={m.head}>
            <View>
              <Text style={m.title}>Final Inspection · {ctx?.wo_number || wo?.wo_number || ''}</Text>
              <Text style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{ctx?.customer_name || ''}</Text>
            </View>
            <Pressable onPress={close} testID="final-inspection-close"><Ionicons name="close" size={22} color="#0F172A" /></Pressable>
          </View>

          {loading ? (
            <ActivityIndicator size="large" color="#C5964A" style={{ marginVertical: 30 }} />
          ) : (
            <ScrollView>
              {(() => {
                const na = Object.entries(applicable).filter(([, v]) => !v).map(([k]) => k);
                const labels: any = { runout: 'Runout', water: 'Water', dust: 'Dust', friction: 'Friction', painting: 'Painting' };
                return na.length > 0 ? (
                  <View style={{ backgroundColor: '#FEF3C7', borderLeftWidth: 3, borderLeftColor: '#F59E0B', padding: 8, borderRadius: 6, marginBottom: 10 }}>
                    <Text style={{ fontSize: 11, color: '#92400E', fontWeight: '700' }}>Not Applicable per SO: {na.map((k: string) => labels[k]).join(', ')}</Text>
                  </View>
                ) : null;
              })()}
              {items.length === 0 && (
                <Text style={{ padding: 16, color: '#94A3B8', textAlign: 'center' }}>No items on this WO.</Text>
              )}
              {items.map((item, ii) => {
                const locked = item.sample_qty > 0;
                return (
                  <View key={item.item_index} style={m.itemBlock}>
                    <Text style={m.itemTitle}>#{item.item_index + 1} · {item.product_name}</Text>
                    <View style={m.metaRow}>
                      <Text style={m.metaLabel}>Qty: <Text style={m.metaVal}>{item.quantity}</Text></Text>
                      <Text style={m.metaLabel}>Pipe L: <Text style={m.metaVal}>{item.pipe_length_mm} mm</Text></Text>
                      {applicable.runout && (
                        <Text style={m.metaLabel}>Runout Tol: <Text style={m.metaVal}>&lt; {item.runout_tolerance_mm} mm</Text></Text>
                      )}
                      <Text style={m.metaLabel}>Bearing (WO): <Text style={m.metaVal}>{item.bearing_spec}</Text></Text>
                      <Text style={m.metaLabel}>Samples (locked from Pipe QC): <Text style={m.metaVal}>{item.sample_qty}</Text></Text>
                    </View>
                    {applicable.painting && (
                      <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                        <Text style={m.qtyLabel}>Expected DFT (µm):</Text>
                        <TextInput
                          style={m.qtyInput}
                          keyboardType="numeric"
                          value={String(item.expected_dft_microns ?? '')}
                          onChangeText={v => patchItem(ii, 'expected_dft_microns', v)}
                          placeholder="e.g. 60"
                          testID={`fi-expected-dft-${ii}`}
                        />
                        <Text style={m.qtySub}>± 20% allowed</Text>
                      </View>
                    )}

                    {!locked && (
                      <Text style={{ fontSize: 11, color: '#B91C1C', marginBottom: 6 }}>Sample count is 0 — complete Pipe or Shaft WIP QC first to unlock inspection samples.</Text>
                    )}

                    {item.samples.map((s: any, si: number) => {
                      const ev = evalSample(item, s);
                      const tone = ev.overall ? '#10B981' : '#EF4444';
                      return (
                        <View key={si} style={[m.sampleCard, { borderLeftColor: tone }]}>
                          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <Text style={m.sampleTitle}>Sample #{s.sample_no}</Text>
                            <Text style={{ fontSize: 11, fontWeight: '700', color: tone }}>{ev.overall ? 'PASS' : 'FAIL'}</Text>
                          </View>

                          <View style={{ flexDirection: 'row', gap: 10, flexWrap: 'wrap' }}>
                            {applicable.runout && (
                              <View style={{ minWidth: 120 }}>
                                <Text style={m.fieldLabel}>Runout (mm)</Text>
                                <TextInput
                                  style={[m.num, s.runout_mm !== '' && (ev.runout_ok ? m.numOk : m.numBad)]}
                                  keyboardType="numeric"
                                  value={String(s.runout_mm ?? '')}
                                  onChangeText={v => patchSample(ii, si, 'runout_mm', v)}
                                  placeholder={`< ${item.runout_tolerance_mm}`}
                                  testID={`fi-runout-${ii}-${si}`}
                                />
                              </View>
                            )}
                            {applicable.friction && (
                              <View style={{ minWidth: 110 }}>
                                <Text style={m.fieldLabel}>Friction (COF)</Text>
                                <TextInput
                                  style={[m.num, s.friction_coeff !== '' && (ev.friction_ok ? m.numOk : m.numBad)]}
                                  keyboardType="numeric"
                                  value={String(s.friction_coeff ?? '')}
                                  onChangeText={v => patchSample(ii, si, 'friction_coeff', v)}
                                  placeholder="< 0.02"
                                  testID={`fi-cof-${ii}-${si}`}
                                />
                              </View>
                            )}
                            {applicable.painting && (
                              <View style={{ minWidth: 110 }}>
                                <Text style={m.fieldLabel}>DFT (µm)</Text>
                                <TextInput
                                  style={[m.num, s.dft_microns !== '' && (ev.dft_ok ? m.numOk : m.numBad)]}
                                  keyboardType="numeric"
                                  value={String(s.dft_microns ?? '')}
                                  onChangeText={v => patchSample(ii, si, 'dft_microns', v)}
                                  placeholder={item.expected_dft_microns ? `≈ ${item.expected_dft_microns}` : '—'}
                                  testID={`fi-dft-${ii}-${si}`}
                                />
                              </View>
                            )}
                          </View>

                          <View style={{ flexDirection: 'row', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
                            {applicable.water && (
                              <View>
                                <Text style={m.fieldLabel}>Water Test</Text>
                                <PF value={s.water_ok} onChange={(v: boolean) => patchSample(ii, si, 'water_ok', v)} testID={`fi-water-${ii}-${si}`} />
                              </View>
                            )}
                            {applicable.dust && (
                              <View>
                                <Text style={m.fieldLabel}>Dust Test</Text>
                                <PF value={s.dust_ok} onChange={(v: boolean) => patchSample(ii, si, 'dust_ok', v)} testID={`fi-dust-${ii}-${si}`} />
                              </View>
                            )}
                            {applicable.painting && (
                              <View>
                                <Text style={m.fieldLabel}>Painting Visual</Text>
                                <PF value={s.painting_visual_ok} onChange={(v: boolean) => patchSample(ii, si, 'painting_visual_ok', v)} testID={`fi-paint-${ii}-${si}`} labels={['Satisfactory', 'Not']} />
                              </View>
                            )}
                            <View>
                              <Text style={m.fieldLabel}>Welding</Text>
                              <PF value={s.welding_ok} onChange={(v: boolean) => patchSample(ii, si, 'welding_ok', v)} testID={`fi-weld-${ii}-${si}`} labels={['Satisfactory', 'Not']} />
                            </View>
                          </View>

                          <View style={{ flexDirection: 'row', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
                            <View>
                              <Text style={m.fieldLabel}>Bearing # &amp; Make match WO?</Text>
                              <YN value={s.bearing_match} onChange={(v: boolean) => patchSample(ii, si, 'bearing_match', v)} testID={`fi-bearing-${ii}-${si}`} />
                              {s.bearing_match === false && (
                                <TextInput
                                  style={m.remark}
                                  value={s.bearing_reason}
                                  onChangeText={v => patchSample(ii, si, 'bearing_reason', v)}
                                  placeholder="Reason for mismatch..."
                                  testID={`fi-bearing-reason-${ii}-${si}`}
                                />
                              )}
                            </View>
                            <View>
                              <Text style={m.fieldLabel}>Rust Preventive applied?</Text>
                              <YN value={s.rust_preventive} onChange={(v: boolean) => patchSample(ii, si, 'rust_preventive', v)} testID={`fi-rust-${ii}-${si}`} />
                              {s.rust_preventive === false && (
                                <TextInput
                                  style={m.remark}
                                  value={s.rust_reason}
                                  onChangeText={v => patchSample(ii, si, 'rust_reason', v)}
                                  placeholder="Reason..."
                                  testID={`fi-rust-reason-${ii}-${si}`}
                                />
                              )}
                            </View>
                          </View>

                          <TextInput
                            style={[m.num, { marginTop: 10, fontWeight: '500' }]}
                            value={s.remarks}
                            onChangeText={v => patchSample(ii, si, 'remarks', v)}
                            placeholder="Remarks (optional)"
                            testID={`fi-remarks-${ii}-${si}`}
                          />
                        </View>
                      );
                    })}
                  </View>
                );
              })}
            </ScrollView>
          )}

          <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
            <TouchableOpacity
              style={[m.saveBtn, { flex: 1, backgroundColor: '#475569' }]}
              onPress={() => downloadReport('pdf')}
              disabled={!items.length}
              testID="final-inspection-pdf"
            >
              <Ionicons name="document-text" size={16} color="#fff" />
              <Text style={m.saveText}>PDF</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[m.saveBtn, { flex: 1, backgroundColor: '#047857' }]}
              onPress={() => downloadReport('excel')}
              disabled={!items.length}
              testID="final-inspection-excel"
            >
              <Ionicons name="grid" size={16} color="#fff" />
              <Text style={m.saveText}>Excel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[m.saveBtn, { flex: 2, backgroundColor: '#C5964A', opacity: saving ? 0.6 : 1 }]}
              onPress={save}
              disabled={saving || !items.length}
              testID="final-inspection-save"
            >
              {saving ? <ActivityIndicator color="#fff" /> : <Ionicons name="save" size={16} color="#fff" />}
              <Text style={m.saveText}>{saving ? 'Saving...' : 'Save Inspection'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  return { open, render };
}


const m = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(15,23,42,0.55)', justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, maxHeight: '92%' },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  title: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  sub: { fontSize: 12, fontWeight: '700' },
  itemBlock: { backgroundColor: 'rgba(241,245,249,0.55)', borderRadius: 12, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#E2E8F0' },
  itemTitle: { fontSize: 14, fontWeight: '700', color: '#0F172A', marginBottom: 4 },
  metaRow: { flexDirection: 'row', gap: 12, marginBottom: 10, flexWrap: 'wrap' },
  metaLabel: { fontSize: 11, color: '#64748B' },
  metaVal: { color: '#0F172A', fontWeight: '700' },
  qtyRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  qtyLabel: { fontSize: 12, fontWeight: '600' },
  qtyInput: { width: 80, backgroundColor: '#fff', borderWidth: 1, borderColor: '#C5964A', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, fontSize: 14, fontWeight: '700', color: '#0F172A', textAlign: 'center' },
  qtySub: { fontSize: 10, color: '#94A3B8' },
  sampleCard: { backgroundColor: '#fff', borderRadius: 10, padding: 10, marginBottom: 8, borderLeftWidth: 3 },
  sampleTitle: { fontSize: 12, fontWeight: '700', color: '#0F172A', marginBottom: 8 },
  fieldLabel: { fontSize: 11, color: '#64748B', marginBottom: 4 },
  sectionLabel: { fontSize: 11, fontWeight: '700', marginBottom: 6, marginTop: 2 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, borderWidth: 1, borderColor: '#CBD5E1' },
  chipText: { fontSize: 11, fontWeight: '700', color: '#94A3B8' },
  chipOk: { borderColor: '#10B981', backgroundColor: 'rgba(16,185,129,0.12)' },
  chipOkText: { color: '#10B981' },
  chipBad: { borderColor: '#EF4444', backgroundColor: 'rgba(239,68,68,0.12)' },
  chipBadText: { color: '#EF4444' },
  remark: { marginTop: 6, backgroundColor: '#FEF2F2', borderWidth: 1, borderColor: '#FCA5A5', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, fontSize: 12, color: '#0F172A' },
  num: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#CBD5E1', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, fontSize: 13, fontWeight: '700', color: '#0F172A' },
  numOk: { backgroundColor: '#ECFDF5', borderColor: '#10B981' },
  numBad: { backgroundColor: '#FEF2F2', borderColor: '#EF4444' },
  saveBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderRadius: 14, paddingVertical: 15, marginTop: 10 },
  saveText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});
