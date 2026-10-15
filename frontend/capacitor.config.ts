import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Capacitor Mobile Application Configuration for CartMate.
 * Enables native packaging for iOS (TestFlight / App Store) and Android (Google Play).
 */
const config: CapacitorConfig = {
  appId: 'pl.cartmate.app',
  appName: 'CartMate',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    cleartext: false,
  },
};

export default config;
