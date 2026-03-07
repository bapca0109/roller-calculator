// Font family configuration for the app
// Using Calibri with appropriate fallbacks

export const FONTS = {
  regular: 'Calibri',
  bold: 'CalibriBold',
  // Fallback font stack for web
  webFontStack: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
};

// Font weights mapping
export const FONT_WEIGHTS = {
  regular: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
};
