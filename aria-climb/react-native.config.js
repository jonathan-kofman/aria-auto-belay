module.exports = {
  dependencies: {
    // Disable native autolinking for react-native-worklets. We only need the
    // Babel plugin, not the native module, so Android/iOS builds can skip it.
    'react-native-worklets': {
      platforms: {
        android: null,
        ios: null,
      },
    },
  },
};

