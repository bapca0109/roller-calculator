import React from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { RevisionHistoryEntry } from './types';

interface RevisionHistoryModalProps {
  visible: boolean;
  onClose: () => void;
  history: RevisionHistoryEntry[];
  formatDate: (timestamp: string) => string;
}

export const RevisionHistoryModal: React.FC<RevisionHistoryModalProps> = ({
  visible,
  onClose,
  history,
  formatDate,
}) => {
  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Revision History</Text>
            <TouchableOpacity onPress={onClose} data-testid="close-history-modal">
              <Ionicons name="close" size={24} color="#333" />
            </TouchableOpacity>
          </View>
          
          <ScrollView style={{ flex: 1 }}>
            {history.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="time-outline" size={48} color="#ccc" />
                <Text style={styles.emptyTitle}>No revisions yet</Text>
                <Text style={styles.emptySubtext}>
                  Changes made to this quote will appear here
                </Text>
              </View>
            ) : (
              history.map((entry, index) => (
                <View key={index} style={styles.revisionEntry}>
                  <View style={styles.revisionHeader}>
                    <View style={styles.revisionTimeline}>
                      <View style={[styles.revisionDot, index === 0 && styles.revisionDotActive]} />
                      {index < history.length - 1 && <View style={styles.revisionLine} />}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.revisionDate}>
                        {formatDate(entry.timestamp)}
                      </Text>
                      <Text style={styles.revisionUser}>
                        by {entry.changed_by_name || entry.changed_by}
                      </Text>
                    </View>
                    <View style={[
                      styles.revisionActionBadge, 
                      entry.action === 'approved' && { backgroundColor: '#E8F5E9' },
                      entry.action === 'rejected' && { backgroundColor: '#FFEBEE' },
                    ]}>
                      <Text style={[
                        styles.revisionActionText,
                        entry.action === 'approved' && { color: '#2E7D32' },
                        entry.action === 'rejected' && { color: '#C62828' },
                      ]}>
                        {entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                      </Text>
                    </View>
                  </View>
                  
                  {Object.keys(entry.changes).length > 0 && (
                    <View style={styles.revisionChanges}>
                      {Object.entries(entry.changes).map(([field, values]: [string, any], cIdx) => (
                        <View key={cIdx} style={styles.revisionChangeRow}>
                          <Text style={styles.revisionChangeLabel}>{field}:</Text>
                          <View style={styles.revisionChangeValues}>
                            {values.old && (
                              <Text style={styles.revisionOldValue}>{values.old}</Text>
                            )}
                            {values.old && values.new && (
                              <Ionicons name="arrow-forward" size={14} color="#666" style={{ marginHorizontal: 8 }} />
                            )}
                            <Text style={styles.revisionNewValue}>{values.new}</Text>
                          </View>
                        </View>
                      ))}
                    </View>
                  )}
                  
                  {Object.keys(entry.changes).length === 0 && entry.summary && (
                    <Text style={styles.revisionSummary}>{entry.summary}</Text>
                  )}
                </View>
              ))
            )}
          </ScrollView>
          
          <TouchableOpacity 
            style={styles.closeButton}
            onPress={onClose}
            data-testid="close-history-button"
          >
            <Text style={styles.closeButtonText}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
    width: '100%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#960018',
  },
  emptyState: {
    padding: 40,
    alignItems: 'center',
  },
  emptyTitle: {
    color: '#666',
    marginTop: 12,
    fontSize: 16,
    textAlign: 'center',
  },
  emptySubtext: {
    color: '#999',
    marginTop: 4,
    fontSize: 14,
    textAlign: 'center',
  },
  revisionEntry: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  revisionHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  revisionTimeline: {
    width: 24,
    alignItems: 'center',
    marginRight: 12,
  },
  revisionDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#CBD5E1',
    borderWidth: 2,
    borderColor: '#E2E8F0',
  },
  revisionDotActive: {
    backgroundColor: '#960018',
    borderColor: '#FEE2E2',
  },
  revisionLine: {
    width: 2,
    flex: 1,
    backgroundColor: '#E2E8F0',
    position: 'absolute',
    top: 14,
    bottom: -20,
  },
  revisionDate: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1E293B',
  },
  revisionUser: {
    fontSize: 12,
    color: '#64748B',
    marginTop: 2,
  },
  revisionActionBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: '#F1F5F9',
  },
  revisionActionText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#475569',
  },
  revisionChanges: {
    marginTop: 12,
    marginLeft: 36,
    padding: 12,
    backgroundColor: '#F8FAFC',
    borderRadius: 8,
  },
  revisionChangeRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  revisionChangeLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748B',
    width: 100,
  },
  revisionChangeValues: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  revisionOldValue: {
    fontSize: 12,
    color: '#94A3B8',
    textDecorationLine: 'line-through',
  },
  revisionNewValue: {
    fontSize: 12,
    color: '#0F172A',
    fontWeight: '500',
  },
  revisionSummary: {
    marginTop: 8,
    marginLeft: 36,
    fontSize: 13,
    color: '#64748B',
    fontStyle: 'italic',
  },
  closeButton: {
    backgroundColor: '#960018',
    margin: 16,
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default RevisionHistoryModal;
