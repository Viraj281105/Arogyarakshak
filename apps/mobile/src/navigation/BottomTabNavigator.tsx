import React from 'react';
import { Text, Platform, StyleSheet } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { BottomTabParamList } from './types';
import { useTheme } from '../theme';
import { useLanguage } from '../hooks/useLanguage';
import {
  HomeScreen,
  BillNyayScreen,
  DaaviSetuScreen,
  BimaNyayScreen,
  SchemeSetuScreen,
  DawaCheckScreen,
} from '../screens';

const Tab = createBottomTabNavigator<BottomTabParamList>();

export const BottomTabNavigator: React.FC = () => {
  const { colors, spacing, typography } = useTheme();
  const { t } = useLanguage();

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.bgSurface,
          borderTopColor: colors.borderSubtle,
          height: Platform.OS === 'ios' ? 88 : 64,
          paddingBottom: Platform.OS === 'ios' ? 24 : 8,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.brandCyan,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarItemStyle: {
          minHeight: spacing.minTouchTarget, // 44px
        },
        tabBarLabelStyle: {
          fontSize: typography.sizes.xs,
          fontWeight: '600',
        },
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarLabel: t.tabs.home,
          tabBarIcon: ({ color }) => <Text style={[styles.icon, { color }]}>🏠</Text>,
        }}
      />
      <Tab.Screen
        name="BillNyay"
        component={BillNyayScreen}
        options={{
          tabBarLabel: t.tabs.billnyay,
          tabBarIcon: ({ color }) => <Text style={[styles.icon, { color }]}>⚖️</Text>,
        }}
      />
      <Tab.Screen
        name="DaaviSetu"
        component={DaaviSetuScreen}
        options={{
          tabBarLabel: t.tabs.daavisetu,
          tabBarIcon: ({ color }) => <Text style={[styles.icon, { color }]}>📋</Text>,
        }}
      />
      <Tab.Screen
        name="BimaNyay"
        component={BimaNyayScreen}
        options={{
          tabBarLabel: t.tabs.bimanyay,
          tabBarIcon: ({ color }) => <Text style={[styles.icon, { color }]}>🛡️</Text>,
        }}
      />
      <Tab.Screen
        name="SchemeSetu"
        component={SchemeSetuScreen}
        options={{
          tabBarLabel: t.tabs.schemesetu,
          tabBarIcon: ({ color }) => <Text style={[styles.icon, { color }]}>🏛️</Text>,
        }}
      />
      <Tab.Screen
        name="DawaCheck"
        component={DawaCheckScreen}
        options={{
          tabBarLabel: t.tabs.dawacheck,
          tabBarIcon: ({ color }) => <Text style={[styles.icon, { color }]}>💊</Text>,
        }}
      />
    </Tab.Navigator>
  );
};

const styles = StyleSheet.create({
  icon: {
    fontSize: 20,
  },
});
