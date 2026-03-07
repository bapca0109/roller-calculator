import { Platform, TextStyle } from 'react-native';
import { Text as RNText, TextProps } from 'react-native';

// Calibri font family with fallbacks
export const FONT_FAMILY = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'Calibri',
});

export const FONT_FAMILY_BOLD = Platform.select({
  web: 'Calibri, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  default: 'CalibriBold',
});

// Set default font for all Text components
// This is applied globally when the app starts
export const setDefaultTextFont = () => {
  // @ts-ignore - we're modifying the prototype
  const oldRender = RNText.render;
  // @ts-ignore
  RNText.render = function (...args: any[]) {
    const origin = oldRender.call(this, ...args);
    return {
      ...origin,
      props: {
        ...origin.props,
        style: [{ fontFamily: FONT_FAMILY }, origin.props.style],
      },
    };
  };
};
