module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
    plugins: [
      // Must be last for worklets/Reanimated to transform correctly
      'react-native-reanimated/plugin',
    ],
  };
};
