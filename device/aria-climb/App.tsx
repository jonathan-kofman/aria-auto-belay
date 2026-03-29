import './src/shims';
import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { I18nextProvider } from 'react-i18next';
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useAuthStore } from './src/store/authStore';
import { RootNavigator } from './src/navigation/RootNavigator';
import * as authService from './src/services/firebase/auth';
import en from './src/locales/en.json';
import es from './src/locales/es.json';
import fr from './src/locales/fr.json';
import de from './src/locales/de.json';
import ja from './src/locales/ja.json';

i18next.use(initReactI18next).init({
  compatibilityJSON: 'v4',
  lng: 'en',
  resources: { en: { translation: en }, es: { translation: es }, fr: { translation: fr }, de: { translation: de }, ja: { translation: ja } },
  fallbackLng: 'en',
});

export default function App() {
  const setUser = useAuthStore((s) => s.setUser);
  const setPendingRoleSelect = useAuthStore((s) => s.setPendingRoleSelect);
  const setLoading = useAuthStore((s) => s.setLoading);

  useEffect(() => {
    // Real auth flow (Firebase). If Firebase isn't available (e.g. Expo Go),
    // we fail open to the auth screens instead of blocking the UI.
    setLoading(true);
    try {
      const unsub = authService.onAuthStateChanged(({ user, pendingRoleSelect }) => {
        setUser(user);
        setPendingRoleSelect(pendingRoleSelect);
        setLoading(false);
      });
      return unsub;
    } catch {
      setUser(null);
      setPendingRoleSelect(false);
      setLoading(false);
      return;
    }
  }, [setLoading, setUser, setPendingRoleSelect]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <I18nextProvider i18n={i18next}>
        <NavigationContainer>
          <RootNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
      </I18nextProvider>
    </GestureHandlerRootView>
  );
}
