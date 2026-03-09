// Industrial Minimalist Theme - Design System
// Based on design_guidelines.json

export const theme = {
  colors: {
    primary: {
      DEFAULT: '#960018',
      50: '#fdf2f2',
      100: '#fde8e8',
      200: '#fbd5d5',
      300: '#f8b4b4',
      400: '#f98080',
      500: '#960018',
      600: '#750012',
      700: '#5a000e',
      800: '#42000a',
      900: '#2b0006',
    },
    secondary: {
      DEFAULT: '#475569',
      foreground: '#ffffff',
    },
    background: {
      default: '#F8FAFC',
      paper: '#FFFFFF',
      subtle: '#F1F5F9',
      dark: '#0F172A',
    },
    text: {
      primary: '#0F172A',
      secondary: '#64748B',
      muted: '#94A3B8',
      inverted: '#FFFFFF',
    },
    border: {
      default: '#E2E8F0',
      light: '#F1F5F9',
      focus: '#960018',
    },
    status: {
      success: '#10B981',
      successBg: '#ECFDF5',
      warning: '#F59E0B',
      warningBg: '#FFFBEB',
      error: '#EF4444',
      errorBg: '#FEF2F2',
      info: '#3B82F6',
      infoBg: '#EFF6FF',
    },
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
    xxxl: 32,
  },
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    full: 9999,
  },
  shadows: {
    sm: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
      elevation: 1,
    },
    md: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.08,
      shadowRadius: 4,
      elevation: 2,
    },
    lg: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.1,
      shadowRadius: 8,
      elevation: 4,
    },
  },
  typography: {
    h1: {
      fontSize: 28,
      fontWeight: '700' as const,
      letterSpacing: -0.5,
      color: '#0F172A',
    },
    h2: {
      fontSize: 22,
      fontWeight: '600' as const,
      letterSpacing: -0.3,
      color: '#0F172A',
    },
    h3: {
      fontSize: 18,
      fontWeight: '600' as const,
      color: '#1E293B',
    },
    body: {
      fontSize: 15,
      fontWeight: '400' as const,
      color: '#64748B',
      lineHeight: 22,
    },
    bodyLarge: {
      fontSize: 16,
      fontWeight: '400' as const,
      color: '#475569',
      lineHeight: 24,
    },
    caption: {
      fontSize: 13,
      fontWeight: '400' as const,
      color: '#94A3B8',
    },
    label: {
      fontSize: 12,
      fontWeight: '600' as const,
      letterSpacing: 0.5,
      textTransform: 'uppercase' as const,
      color: '#64748B',
    },
    mono: {
      fontSize: 14,
      fontFamily: 'SpaceMono-Regular',
      color: '#0F172A',
    },
  },
};

// Asset URLs from design guidelines
export const assets = {
  heroBackground: 'https://images.unsplash.com/photo-1748946469988-61310d7ea26a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBmYWN0b3J5JTIwY29udmV5b3IlMjBiZWx0JTIwc3lzdGVtJTIwY2xlYW58ZW58MHx8fHwxNzczMDc3MzQyfDA&ixlib=rb-4.1.0&q=85',
  productPlaceholder: 'https://images.unsplash.com/photo-1764875471704-95de704ee3a2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTN8MHwxfHNlYXJjaHwyfHxtZXRhbCUyMGNvbnZleW9yJTIwcm9sbGVyfGVufDB8fHx8MTc3MzA3NzM1M3ww&ixlib=rb-4.1.0&q=85',
  blueprintAbstract: 'https://images.unsplash.com/photo-1727522974676-c2f9c32ee692?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHw0fHxhYnN0cmFjdCUyMGluZHVzdHJpYWwlMjBibHVlcHJpbnRzJTIwdGVjaG5pY2FsJTIwZHJhd2luZ3xlbnwwfHx8fDE3NzMwNzczNDV8MA&ixlib=rb-4.1.0&q=85',
  userAvatar: 'https://images.pexels.com/photos/4484075/pexels-photo-4484075.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
};

export default theme;
