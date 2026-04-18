import { Alert, Platform } from 'react-native';

/**
 * Cross-platform confirm dialog.
 * Resolves true if user confirms, false if cancelled.
 *
 * Usage:
 *   if (!(await confirmAction('Convert to Sales Order?', 'This will generate a new SO.'))) return;
 */
export function confirmAction(title: string, message?: string, confirmLabel = 'Yes, Proceed', cancelLabel = 'Cancel'): Promise<boolean> {
  if (Platform.OS === 'web') {
    // Use browser confirm — blocking, returns boolean synchronously
    const text = message ? `${title}\n\n${message}` : title;
    // eslint-disable-next-line no-alert
    const ok = typeof window !== 'undefined' && window.confirm ? window.confirm(text) : true;
    return Promise.resolve(ok);
  }
  return new Promise<boolean>((resolve) => {
    Alert.alert(
      title,
      message || '',
      [
        { text: cancelLabel, style: 'cancel', onPress: () => resolve(false) },
        { text: confirmLabel, style: 'default', onPress: () => resolve(true) },
      ],
      { cancelable: true, onDismiss: () => resolve(false) }
    );
  });
}
