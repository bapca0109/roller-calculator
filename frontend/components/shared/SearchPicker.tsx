import React, { useState, useMemo } from 'react';
import { View, Text, TextInput, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export type SearchItem = {
  id: string;
  label: string;
  sublabel?: string;
  right?: string;
};

type Props = {
  value: string;
  items: SearchItem[];
  onSelect: (id: string, item: SearchItem) => void;
  placeholder?: string;
  emptyText?: string;
  testID?: string;
  maxResults?: number;
  /** If false the user can change their selection by tapping a small "change" button; otherwise the selected item is locked until programmatically cleared */
  allowChange?: boolean;
};

/**
 * Unified search-driven picker: a single TextInput feeds a short list of matching
 * rows. Supports ↑/↓/Enter/Esc keyboard navigation and mouse hover. When an item
 * is selected it collapses into a compact "selected" chip with a small edit
 * button, mirroring the PO line-item UX in Store → Raise PO.
 */
export function SearchPicker({
  value,
  items,
  onSelect,
  placeholder = 'Search...',
  emptyText = 'No matches found',
  testID,
  maxResults = 8,
  allowChange = true,
}: Props) {
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);
  const [editing, setEditing] = useState(false);

  const selected = useMemo(() => items.find(it => it.id === value), [items, value]);
  const showPicker = !selected || editing;

  const matched = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [] as SearchItem[];
    return items
      .filter(it => {
        const l = (it.label || '').toLowerCase();
        const s = (it.sublabel || '').toLowerCase();
        return l.includes(q) || s.includes(q);
      })
      .slice(0, maxResults);
  }, [query, items, maxResults]);

  const hl = Math.min(highlight, Math.max(0, matched.length - 1));

  const doSelect = (item: SearchItem) => {
    onSelect(item.id, item);
    setQuery('');
    setHighlight(0);
    setEditing(false);
  };

  const onKey = (e: any) => {
    const key = e?.nativeEvent?.key || e?.key;
    if (!key) return;
    if (key === 'ArrowDown') { e.preventDefault?.(); setHighlight(h => Math.min(h + 1, Math.max(0, matched.length - 1))); }
    else if (key === 'ArrowUp') { e.preventDefault?.(); setHighlight(h => Math.max(h - 1, 0)); }
    else if (key === 'Enter') { e.preventDefault?.(); if (matched[hl]) doSelect(matched[hl]); }
    else if (key === 'Escape') { setQuery(''); setHighlight(0); setEditing(false); }
  };

  if (selected && !showPicker) {
    return (
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#ECFDF5', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 8, borderWidth: 1, borderColor: '#10B981', marginBottom: 6 }} testID={testID ? `${testID}-selected` : undefined}>
        <Ionicons name="checkmark-circle" size={16} color="#10B981" />
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 12, fontWeight: '700', color: '#0F172A' }} numberOfLines={1}>{selected.label}</Text>
          {selected.sublabel ? <Text style={{ fontSize: 10, color: '#64748B' }} numberOfLines={1}>{selected.sublabel}</Text> : null}
        </View>
        {allowChange && (
          <Pressable onPress={() => { setEditing(true); setQuery(''); setHighlight(0); }} testID={testID ? `${testID}-change` : undefined} style={{ paddingHorizontal: 6, paddingVertical: 2 }}>
            <Text style={{ fontSize: 10, fontWeight: '700', color: '#C5964A' }}>Change</Text>
          </Pressable>
        )}
      </View>
    );
  }

  return (
    <View style={{ marginBottom: 6 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#F1F5F9', borderRadius: 10, borderWidth: 1, borderColor: '#E2E8F0', paddingHorizontal: 10 }}>
        <Ionicons name="search" size={14} color="#94A3B8" />
        <TextInput
          style={{ flex: 1, paddingVertical: 8, paddingHorizontal: 6, fontSize: 13, color: '#0F172A', outlineWidth: 0 } as any}
          value={query}
          onChangeText={v => { setQuery(v); setHighlight(0); }}
          onKeyPress={onKey}
          {...({ onKeyDown: onKey } as any)}
          placeholder={placeholder}
          placeholderTextColor="#94A3B8"
          testID={testID}
          autoCapitalize="none"
          autoFocus={editing}
        />
        {!!query && (
          <Pressable onPress={() => { setQuery(''); setHighlight(0); }} testID={testID ? `${testID}-clear` : undefined}>
            <Ionicons name="close-circle" size={16} color="#94A3B8" />
          </Pressable>
        )}
        {editing && selected && (
          <Pressable onPress={() => { setEditing(false); setQuery(''); }} testID={testID ? `${testID}-cancel-edit` : undefined} style={{ marginLeft: 6 }}>
            <Text style={{ fontSize: 10, fontWeight: '700', color: '#64748B' }}>Cancel</Text>
          </Pressable>
        )}
      </View>
      {query.length > 0 && (
        matched.length === 0 ? (
          <View style={{ padding: 10, backgroundColor: '#FEF3C7', borderRadius: 8, marginTop: 4 }}>
            <Text style={{ fontSize: 11, color: '#92400E', fontWeight: '600' }}>{emptyText}</Text>
          </View>
        ) : (
          <View style={{ backgroundColor: '#FFFFFF', borderRadius: 10, borderWidth: 1, borderColor: '#E2E8F0', marginTop: 4, overflow: 'hidden' }}>
            {matched.map((item, mi) => {
              const isHl = mi === hl;
              return (
                <Pressable
                  key={item.id}
                  onPress={() => doSelect(item)}
                  onHoverIn={() => setHighlight(mi)}
                  style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 8, borderTopWidth: mi === 0 ? 0 : 1, borderTopColor: '#F1F5F9', backgroundColor: isHl ? '#FEF3C7' : 'transparent' }}
                  testID={testID ? `${testID}-option-${item.id}` : undefined}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 12, color: '#0F172A', fontWeight: isHl ? '800' : '600' }} numberOfLines={1}>{item.label}</Text>
                    {item.sublabel ? <Text style={{ fontSize: 10, color: '#64748B' }} numberOfLines={1}>{item.sublabel}</Text> : null}
                  </View>
                  {item.right ? <Text style={{ fontSize: 10, color: '#10B981', fontWeight: '700' }}>{item.right}</Text> : null}
                </Pressable>
              );
            })}
          </View>
        )
      )}
      {query.length === 0 && (
        <Text style={{ fontSize: 10, color: '#94A3B8', marginTop: 4 }}>Start typing to find an item (↑↓ Enter)</Text>
      )}
    </View>
  );
}
