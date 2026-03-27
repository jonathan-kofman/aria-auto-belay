/**
 * Ensures the Google services Gradle plugin is applied for both Groovy and Kotlin DSL.
 * The @react-native-firebase/app plugin only patches Groovy; Expo may generate .gradle.kts.
 */
const { withProjectBuildGradle, withAppBuildGradle } = require('@expo/config-plugins');

const GOOGLE_SERVICES_VERSION = '4.4.4';

function withGoogleServicesProjectGradle(config) {
  return withProjectBuildGradle(config, (config) => {
    const { contents, language } = config.modResults;
    if (contents.includes('com.google.gms:google-services') || contents.includes('com.google.gms.google-services')) {
      return config;
    }
    if (language === 'kt') {
      // Kotlin DSL: add to plugins { } block (may span multiple lines)
      const pluginsBlock = /plugins\s*\{([\s\S]*?)\}/;
      if (pluginsBlock.test(contents)) {
        config.modResults.contents = contents.replace(
          pluginsBlock,
          (match, inner) => `plugins {\n  id("com.google.gms.google-services") version "${GOOGLE_SERVICES_VERSION}" apply false\n${inner}}`
        );
      } else {
        config.modResults.contents = contents + `\nplugins {\n  id("com.google.gms.google-services") version "${GOOGLE_SERVICES_VERSION}" apply false\n}\n`;
      }
    }
    return config;
  });
}

function withGoogleServicesAppGradle(config) {
  return withAppBuildGradle(config, (config) => {
    const { contents, language } = config.modResults;
    if (contents.includes('com.google.gms.google-services')) {
      return config;
    }
    if (language === 'kt') {
      // Kotlin DSL: add to app plugins { } block (may span multiple lines)
      const pluginsBlock = /plugins\s*\{([\s\S]*?)\}/;
      if (pluginsBlock.test(contents)) {
        config.modResults.contents = contents.replace(
          pluginsBlock,
          (match, inner) => `plugins {\n  id("com.google.gms.google-services")\n${inner}}`
        );
      } else {
        config.modResults.contents = contents + '\nplugins { id("com.google.gms.google-services") }\n';
      }
    }
    return config;
  });
}

module.exports = function withGoogleServicesGradle(config) {
  config = withGoogleServicesProjectGradle(config);
  config = withGoogleServicesAppGradle(config);
  return config;
};
