import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../../utils/api';

interface ExportButtonsProps {
  endpoint: string;
  pdfEndpoint?: string;
  queryParams?: Record<string, string>;
  filenamePrefix?: string;
  showPdf?: boolean;
  showExcel?: boolean;
  compact?: boolean;
}

export const ExportButtons: React.FC<ExportButtonsProps> = ({
  endpoint,
  pdfEndpoint,
  queryParams = {},
  filenamePrefix = 'Export',
  showPdf = false,
  showExcel = true,
  compact = false,
}) => {
  const [exporting, setExporting] = useState<'pdf' | 'excel' | null>(null);

  const handleExport = async (format: 'pdf' | 'excel') => {
    setExporting(format);
    try {
      const token = await AsyncStorage.getItem('token');
      
      // Use pdfEndpoint for PDF if provided, otherwise derive from excel endpoint
      const exportEndpoint = format === 'pdf' 
        ? (pdfEndpoint || endpoint.replace('/excel', '/pdf'))
        : endpoint;
      
      // Build query string
      const params = new URLSearchParams(queryParams).toString();
      const url = `${api.defaults.baseURL}${exportEndpoint}${params ? `?${params}` : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Export failed');
      }

      const blob = await response.blob();
      const extension = format === 'pdf' ? 'pdf' : 'xlsx';
      const filename = `${filenamePrefix}_${new Date().toISOString().slice(0, 10)}.${extension}`;

      if (Platform.OS === 'web') {
        // Web: Create download link
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
        Alert.alert('Success', `${format.toUpperCase()} exported successfully!`);
      } else {
        // Mobile: Show message
        Alert.alert('Export', `${format.toUpperCase()} export is available on web version.`);
      }
    } catch (error: any) {
      console.error('Export error:', error);
      Alert.alert('Error', error.message || `Failed to export ${format.toUpperCase()}`);
    } finally {
      setExporting(null);
    }
  };

  if (compact) {
    return (
      <View style={styles.compactContainer}>
        {showExcel && (
          <TouchableOpacity
            style={[styles.compactButton, styles.excelButton]}
            onPress={() => handleExport('excel')}
            disabled={exporting !== null}
            data-testid="export-excel-btn"
          >
            {exporting === 'excel' ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Ionicons name="download-outline" size={18} color="#fff" />
            )}
          </TouchableOpacity>
        )}
        {showPdf && (
          <TouchableOpacity
            style={[styles.compactButton, styles.pdfButton]}
            onPress={() => handleExport('pdf')}
            disabled={exporting !== null}
            data-testid="export-pdf-btn"
          >
            {exporting === 'pdf' ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Ionicons name="document-outline" size={18} color="#fff" />
            )}
          </TouchableOpacity>
        )}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {showExcel && (
        <TouchableOpacity
          style={[styles.button, styles.excelButton]}
          onPress={() => handleExport('excel')}
          disabled={exporting !== null}
          data-testid="export-excel-btn"
        >
          {exporting === 'excel' ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="grid-outline" size={16} color="#fff" />
              <Text style={styles.buttonText}>Excel</Text>
            </>
          )}
        </TouchableOpacity>
      )}
      {showPdf && (
        <TouchableOpacity
          style={[styles.button, styles.pdfButton]}
          onPress={() => handleExport('pdf')}
          disabled={exporting !== null}
          data-testid="export-pdf-btn"
        >
          {exporting === 'pdf' ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="document-outline" size={16} color="#fff" />
              <Text style={styles.buttonText}>PDF</Text>
            </>
          )}
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    gap: 8,
  },
  compactContainer: {
    flexDirection: 'row',
    gap: 6,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  compactButton: {
    width: 36,
    height: 36,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  excelButton: {
    backgroundColor: '#217346',
  },
  pdfButton: {
    backgroundColor: '#960018',
  },
  buttonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
});

export default ExportButtons;
