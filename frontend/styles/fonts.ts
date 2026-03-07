import { Platform, TextStyle } from 'react-native';

// Calibri font family with fallbacks
export const FONT_FAMILY = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'Calibri',
});

export const FONT_FAMILY_BOLD = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'CalibriBold',
});

// Common text styles with Calibri font
export const textStyles: { [key: string]: TextStyle } = {
  regular: {
    fontFamily: FONT_FAMILY,
    fontWeight: '400',
  },
  medium: {
    fontFamily: FONT_FAMILY,
    fontWeight: '500',
  },
  semibold: {
    fontFamily: Platform.OS === 'web' ? FONT_FAMILY : FONT_FAMILY_BOLD,
    fontWeight: '600',
  },
  bold: {
    fontFamily: Platform.OS === 'web' ? FONT_FAMILY : FONT_FAMILY_BOLD,
    fontWeight: '700',
  },
};

// Helper function to get font style
export const getFontStyle = (weight: 'regular' | 'medium' | 'semibold' | 'bold' = 'regular'): TextStyle => {
  return textStyles[weight];
};
