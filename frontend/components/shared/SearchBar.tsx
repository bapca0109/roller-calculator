import React from 'react';
import { View, TextInput, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface SearchBarProps {
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  resultCount?: number | null;   // when >=0 and value.length>0, show count row
  testID?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({ value, onChangeText, placeholder = 'Search…', resultCount = null, testID }) => {
  return (
    <View style={styles.container}>
      <View style={styles.inputWrapper}>
        <Ionicons name="search-outline" size={20} color="#94A3B8" style={styles.icon} />
        <TextInput
          style={styles.input}
          placeholder={placeholder}
          placeholderTextColor="#94A3B8"
          value={value}
          onChangeText={onChangeText}
          autoCapitalize="none"
          autoCorrect={false}
          testID={testID}
        />
        {value.length > 0 && (
          <TouchableOpacity onPress={() => onChangeText('')} style={styles.clearBtn} testID={testID ? `${testID}-clear` : undefined}>
            <Ionicons name="close-circle" size={20} color="#94A3B8" />
          </TouchableOpacity>
        )}
      </View>
      {value.length > 0 && resultCount !== null && (
        <View style={styles.resultsRow}>
          <Text style={styles.resultCount}>
            {resultCount} result{resultCount !== 1 ? 's' : ''} found
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.85)',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(226,232,240,0.7)',
    paddingHorizontal: 12,
    height: 44,
  },
  icon: { marginRight: 8 },
  input: { flex: 1, fontSize: 14, color: '#0F172A', outlineStyle: 'none' as any, outlineWidth: 0 as any, borderWidth: 0 as any },
  clearBtn: { padding: 4 },
  resultsRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 4, paddingVertical: 6 },
  resultCount: { fontSize: 11, color: '#64748B', fontWeight: '600' },
});
