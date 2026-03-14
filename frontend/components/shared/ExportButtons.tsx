import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Platform,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import api from '../../utils/api';

interface ExportError {
  format: 'pdf' | 'excel';
  message: string;
  timestamp: Date;
}

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
  const [lastError, setLastError] = useState<ExportError | null>(null);
  const [showRetryModal, setShowRetryModal] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const MAX_RETRIES = 3;

  const getErrorMessage = (error: any, format: string): string => {
    // Parse common error scenarios with user-friendly messages
    if (error.message?.includes('Network')) {
      return 'Network connection failed. Please check your internet and try again.';
    }
    if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
      return 'Session expired. Please log out and log back in.';
    }
    if (error.message?.includes('404')) {
      return 'Export file not found. Please try again.';
    }
    if (error.message?.includes('500')) {
      return 'Server error. Our team has been notified. Please try again later.';
    }
    if (error.message?.includes('download') || error.message?.includes('Failed')) {
      return `Failed to download ${format.toUpperCase()} file. Tap Retry to try again.`;
    }
    return error.message || `Failed to export ${format.toUpperCase()}. Tap Retry to try again.`;
  };

  const handleExport = async (format: 'pdf' | 'excel', isRetry: boolean = false) => {
    if (isRetry) {
      setShowRetryModal(false);
    }
    
    setExporting(format);
    setLastError(null);
    
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
          throw new Error(errorText || `HTTP ${response.status}: Export failed`);
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
        
        // Success - reset retry count
        setRetryCount(0);
        Alert.alert('Success', `${format.toUpperCase()} exported successfully!`);
      } else {
        // iOS/Android: Download using FileSystem and share
        const fileUri = `${FileSystem.cacheDirectory}${filename}`;
        
        // Download file with timeout handling
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
          throw new Error(`Download failed with status ${downloadResult.status}`);
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
        
        // Success - reset retry count
        setRetryCount(0);
      }
    } catch (error: any) {
      console.error('Export error:', error);
      
      const errorMessage = getErrorMessage(error, format);
      const newError: ExportError = {
        format,
        message: errorMessage,
        timestamp: new Date(),
      };
      setLastError(newError);
      
      // Show retry modal on mobile, or alert on web
      if (Platform.OS !== 'web' && retryCount < MAX_RETRIES) {
        setShowRetryModal(true);
      } else {
        Alert.alert(
          'Export Failed', 
          errorMessage,
          retryCount < MAX_RETRIES 
            ? [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Retry', onPress: () => handleRetry(format) }
              ]
            : [{ text: 'OK' }]
        );
      }
    } finally {
      setExporting(null);
    }
  };

  const handleRetry = (format: 'pdf' | 'excel') => {
    setRetryCount(prev => prev + 1);
    handleExport(format, true);
  };

  const renderRetryModal = () => (
    <Modal
      visible={showRetryModal}
      transparent
      animationType="fade"
      onRequestClose={() => setShowRetryModal(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.retryModalContent}>
          <View style={styles.retryModalHeader}>
            <Ionicons name="warning-outline" size={32} color="#960018" />
            <Text style={styles.retryModalTitle}>Export Failed</Text>
          </View>
          
          <Text style={styles.retryModalMessage}>
            {lastError?.message || 'An error occurred while exporting.'}
          </Text>
          
          {retryCount > 0 && (
            <Text style={styles.retryCountText}>
              Attempt {retryCount + 1} of {MAX_RETRIES + 1}
            </Text>
          )}
          
          <View style={styles.retryModalButtons}>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => {
                setShowRetryModal(false);
                setRetryCount(0);
              }}
              data-testid="export-cancel-btn"
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            
            {retryCount < MAX_RETRIES && lastError && (
              <TouchableOpacity
                style={styles.retryButton}
                onPress={() => handleRetry(lastError.format)}
                data-testid="export-retry-btn"
              >
                <Ionicons name="refresh-outline" size={18} color="#fff" />
                <Text style={styles.retryButtonText}>Retry</Text>
              </TouchableOpacity>
            )}
          </View>
          
          <Text style={styles.retryTipText}>
            Tip: Make sure you have a stable internet connection
          </Text>
        </View>
      </View>
    </Modal>
  );

  if (compact) {
    return (
      <>
        {renderRetryModal()}
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
      </>
    );
  }

  return (
    <>
      {renderRetryModal()}
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
    </>
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
  // Retry Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  retryModalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
  },
  retryModalHeader: {
    alignItems: 'center',
    marginBottom: 16,
  },
  retryModalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1e293b',
    marginTop: 8,
  },
  retryModalMessage: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 8,
  },
  retryCountText: {
    fontSize: 12,
    color: '#94a3b8',
    marginBottom: 16,
  },
  retryModalButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
    width: '100%',
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    backgroundColor: '#f8fafc',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#64748b',
  },
  retryButton: {
    flex: 1,
    flexDirection: 'row',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#960018',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  retryButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  retryTipText: {
    fontSize: 11,
    color: '#94a3b8',
    textAlign: 'center',
    marginTop: 16,
    fontStyle: 'italic',
  },
});

export default ExportButtons;
