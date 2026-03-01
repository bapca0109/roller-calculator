/**
 * Corporate Professional Color Palette
 * Belt Conveyor Roller Calculator App
 */

export const Colors = {
  // Primary - Carmine Red
  primary: {
    main: '#960018',
    light: '#C32E41',
    dark: '#6B0011',
    contrastText: '#FFFFFF',
  },
  
  // Secondary - Slate Blue
  secondary: {
    main: '#475569',
    light: '#64748B',
    dark: '#1E293B',
    contrastText: '#FFFFFF',
  },
  
  // Backgrounds
  background: {
    default: '#F8FAFC',
    paper: '#FFFFFF',
    subtle: '#F1F5F9',
    dark: '#1E293B',
  },
  
  // Text Colors
  text: {
    primary: '#0F172A',
    secondary: '#475569',
    disabled: '#94A3B8',
    light: '#FFFFFF',
  },
  
  // Status Colors
  status: {
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
  },
  
  // Border Colors
  border: {
    default: '#E2E8F0',
    light: '#F1F5F9',
    dark: '#CBD5E1',
  },
  
  // Specific Component Colors
  tab: {
    active: '#960018',
    inactive: '#94A3B8',
    background: '#FFFFFF',
  },
  
  // Card Accents for Roller Types
  rollerTypes: {
    carrying: '#10B981',
    impact: '#3B82F6',
    return: '#F59E0B',
  },
};

// Typography Scale
export const Typography = {
  h1: {
    fontSize: 32,
    fontWeight: '700' as const,
    lineHeight: 40,
    color: Colors.text.primary,
  },
  h2: {
    fontSize: 24,
    fontWeight: '700' as const,
    lineHeight: 32,
    color: Colors.text.primary,
  },
  h3: {
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 28,
    color: Colors.text.primary,
  },
  bodyLarge: {
    fontSize: 18,
    fontWeight: '400' as const,
    lineHeight: 28,
    color: Colors.text.primary,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 24,
    color: Colors.text.primary,
  },
  caption: {
    fontSize: 14,
    fontWeight: '500' as const,
    color: Colors.text.secondary,
  },
  overline: {
    fontSize: 12,
    fontWeight: '700' as const,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    color: Colors.text.secondary,
  },
};

// Spacing Scale (base unit: 4)
export const Spacing = {
  xs: 4,
  s: 8,
  m: 16,
  l: 24,
  xl: 32,
  xxl: 48,
};

// Border Radius
export const Radius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

// Shadow Presets
export const Shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHover: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 8,
    elevation: 5,
  },
  floating: {
    shadowColor: '#960018',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
};

export default Colors;
