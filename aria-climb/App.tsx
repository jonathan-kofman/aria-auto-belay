import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { I18nextProvider } from 'react-i18next';
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import firestore from '@react-native-firebase/firestore';
import { useAuthStore } from './src/store/authStore';
import * as authService from './src/services/firebase/auth';
import { RootNavigator } from './src/navigation/RootNavigator';
import en from './src/locales/en.json';
import es from './src/locales/es.json';
import fr from './src/locales/fr.json';
import de from './src/locales/de.json';
import ja from './src/locales/ja.json';

SplashScreen.preventAutoHideAsync();

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
    firestore().settings({
      persistence: true,
      cacheSizeBytes: firestore.CACHE_SIZE_UNLIMITED,
    });
  }, []);

  useEffect(() => {
    const unsubscribe = authService.onAuthStateChanged((result) => {
      setLoading(true);
      setUser(result.user);
      setPendingRoleSelect(result.pendingRoleSelect);
      setLoading(false);
    });
    return () => unsubscribe();
  }, [setUser, setPendingRoleSelect, setLoading]);

  const [fontsLoaded] = useFonts({
    // Add custom fonts here if needed; optional for Phase 1
  });

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <I18nextProvider i18n={i18next}>
      <NavigationContainer>
        <RootNavigator />
        <StatusBar style="auto" />
      </NavigationContainer>
    </I18nextProvider>
  );
}
