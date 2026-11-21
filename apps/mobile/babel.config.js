// babel-preset-expo only. react-native-reanimated is not a dependency (the motion system uses
// React Native's Animated; see docs/development/performance-budgets.md). If it is ever re-added,
// babel-preset-expo (SDK 52) applies its plugin itself: do not list the plugin here as well.
module.exports = function (api) {
  api.cache(true);
  return { presets: ['babel-preset-expo'] };
};
