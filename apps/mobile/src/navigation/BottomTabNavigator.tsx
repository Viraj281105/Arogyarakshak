import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { BottomTabParamList } from './types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import { TabBar } from '../components/TabBar';
import { useReducedMotion } from '../motion';
import { tabTransition, TAB_ICON, TAB_MAX_FONT_SCALE } from '../shell/logic';
import { motion } from '../generated/tokens';
import {
  HomeScreen,
  BillNyayScreen,
  DaaviSetuScreen,
  BimaNyayScreen,
  SchemeSetuScreen,
  DawaCheckScreen,
} from '../screens';

const Tab = createBottomTabNavigator<BottomTabParamList>();

const icon = (glyph: string) => () => (
  <Text maxFontSizeMultiplier={TAB_MAX_FONT_SCALE} style={styles.icon}>
    {glyph}
  </Text>
);

export const BottomTabNavigator: React.FC = () => {
  const { colors } = useTheme();
  const { t } = useLanguage();
  const reduced = useReducedMotion();

  return (
    <Tab.Navigator
      tabBar={(props) => <TabBar {...props} />}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: colors.bgBase },
        animation: tabTransition(reduced),
        transitionSpec: { animation: 'timing', config: { duration: motion.duration.base } },
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarLabel: t.tabs.home, tabBarIcon: icon('🏠') }} />
      <Tab.Screen
        name="BillNyay"
        component={BillNyayScreen}
        options={{ tabBarLabel: t.tabs.billnyay, tabBarIcon: icon('⚖️') }}
      />
      <Tab.Screen
        name="DaaviSetu"
        component={DaaviSetuScreen}
        options={{ tabBarLabel: t.tabs.daavisetu, tabBarIcon: icon('📋') }}
      />
      <Tab.Screen
        name="BimaNyay"
        component={BimaNyayScreen}
        options={{ tabBarLabel: t.tabs.bimanyay, tabBarIcon: icon('🛡️') }}
      />
      <Tab.Screen
        name="SchemeSetu"
        component={SchemeSetuScreen}
        options={{ tabBarLabel: t.tabs.schemesetu, tabBarIcon: icon('🏛️') }}
      />
      <Tab.Screen
        name="DawaCheck"
        component={DawaCheckScreen}
        options={{ tabBarLabel: t.tabs.dawacheck, tabBarIcon: icon('💊') }}
      />
    </Tab.Navigator>
  );
};

const styles = StyleSheet.create({
  icon: TAB_ICON,
});
