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
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
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
      
      const extension = format === 'pdf' ? 'pdf' : 'xlsx';
      const filename = `${filenamePrefix}_${new Date().toISOString().slice(0, 10)}.${extension}`;
      const mimeType = format === 'pdf' 
        ? 'application/pdf' 
        : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

      if (Platform.OS === 'web') {
        // Web: Fetch and download
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
        // iOS/Android: Download using FileSystem and share
        const fileUri = `${FileSystem.cacheDirectory}${filename}`;
        
        // Download file
        const downloadResult = await FileSystem.downloadAsync(
          url,
          fileUri,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (downloadResult.status !== 200) {
          throw new Error('Failed to download file');
        }

        // Check if sharing is available
        const isAvailable = await Sharing.isAvailableAsync();
        
        if (isAvailable) {
          // Share the file (allows saving to Files, sending via email, etc.)
          await Sharing.shareAsync(downloadResult.uri, {
            mimeType: mimeType,
            dialogTitle: `Share ${format.toUpperCase()} File`,
            UTI: format === 'pdf' ? 'com.adobe.pdf' : 'org.openxmlformats.spreadsheetml.sheet',
          });
        } else {
          // Fallback alert if sharing not available
          Alert.alert(
            'Download Complete', 
            `File saved to: ${downloadResult.uri}`,
            [{ text: 'OK' }]
          );
        }
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
