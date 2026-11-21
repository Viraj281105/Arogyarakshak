import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { RootStackParamList } from './types';
import { BottomTabNavigator } from './BottomTabNavigator';
import { CameraScanScreen } from '../screens';
import { useTheme } from '../theme';
import { useReducedMotion } from '../motion';
import { stackTransition } from '../shell/logic';
import { motion } from '../generated/tokens';

const Stack = createNativeStackNavigator<RootStackParamList>();

export const RootNavigator: React.FC = () => {
  const { colors } = useTheme();
  const reduced = useReducedMotion();

  return (
    <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bgBase } }}>
      <Stack.Screen name="MainTabs" component={BottomTabNavigator} />
      <Stack.Screen
        name="CameraScan"
        component={CameraScanScreen}
        options={{
          presentation: 'fullScreenModal',
          animation: stackTransition(reduced),
          animationDuration: motion.duration.base,
        }}
      />
    </Stack.Navigator>
  );
};
