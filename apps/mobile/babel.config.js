// babel-preset-expo (SDK 52) adds react-native-reanimated/plugin itself when the package is
// installed, so it must NOT be listed again here (double application breaks worklets).
module.exports = function (api) {
  api.cache(true);
  return { presets: ['babel-preset-expo'] };
};
