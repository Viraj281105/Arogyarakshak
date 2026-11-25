import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { register, signIn, type SessionStatus } from '../api/session';
import { Button, Card } from '../components';
import { useLanguage } from '../hooks/useLanguage';
import { passwordProblem } from '../shared/api-client/accounts';
import { useTheme } from '../theme';

/** Sign in or create an account. Everything else in the app needs a session (ADR-029). */
export const SignInScreen: React.FC<{ status: SessionStatus }> = ({ status }) => {
  const { colors, spacing, radii, typography } = useTheme();
  const { t } = useLanguage();
  const a = t.auth;
  const [mode, setMode] = useState<'signIn' | 'register'>('signIn');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const registering = mode === 'register';

  const submit = async () => {
    if (busy || !email.trim() || !password) return;
    if (registering && passwordProblem(password, email)) {
      setError(a.passwordHint);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (registering) await register(email, password);
      await signIn(email, password);
      setPassword('');
    } catch (err) {
      const failure = err as { statusCode?: number; message?: string };
      setError(failure.statusCode === 0 ? a.unreachable : failure.message || a.unreachable);
    } finally {
      setBusy(false);
    }
  };

  const field = {
    borderColor: colors.borderMedium,
    borderWidth: 1,
    borderRadius: radii.md,
    color: colors.textPrimary,
    backgroundColor: colors.bgSurface,
    minHeight: spacing.minTouchTarget,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
    fontSize: typography.sizes.md,
  };
  const label = { color: colors.textPrimary, fontSize: typography.sizes.sm, marginBottom: spacing.xs };

  return (
    <ScrollView contentContainerStyle={[styles.page, { padding: spacing.md }]} keyboardShouldPersistTaps="handled">
      <Card>
        <Text accessibilityRole="header" style={[styles.title, { color: colors.textPrimary, fontSize: typography.sizes.lg }]}>
          {registering ? a.registerTitle : a.signInTitle}
        </Text>
        <Text style={{ color: colors.textSecondary, marginBottom: spacing.md }}>{a.lede}</Text>
        {status === 'expired' && (
          <Text accessibilityLiveRegion="polite" style={{ color: colors.textPrimary, marginBottom: spacing.md }}>
            {a.expired}
          </Text>
        )}
        <Text style={label}>{a.email}</Text>
        <TextInput
          accessibilityLabel={a.email}
          style={field}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          autoComplete="email"
          textContentType="emailAddress"
          maxLength={320}
        />
        <Text style={label}>{a.password}</Text>
        <TextInput
          accessibilityLabel={a.password}
          accessibilityHint={registering ? a.passwordHint : undefined}
          style={field}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize="none"
          autoComplete={registering ? 'new-password' : 'current-password'}
          textContentType={registering ? 'newPassword' : 'password'}
          maxLength={128}
          onSubmitEditing={submit}
        />
        {registering && <Text style={{ color: colors.textSecondary, marginBottom: spacing.md }}>{a.passwordHint}</Text>}
        {error && (
          <Text accessibilityRole="alert" accessibilityLiveRegion="assertive" style={{ color: colors.statusDanger, marginBottom: spacing.md }}>
            {error}
          </Text>
        )}
        <Button title={registering ? a.createAccount : a.signIn} onPress={submit} loading={busy} disabled={!email.trim() || !password} />
        <View style={{ marginTop: spacing.sm }}>
          <Button
            variant="outline"
            title={registering ? a.haveAccount : a.noAccount}
            onPress={() => {
              setMode(registering ? 'signIn' : 'register');
              setError(null);
            }}
          />
        </View>
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  page: { flexGrow: 1, justifyContent: 'center' },
  title: { fontWeight: '700', marginBottom: 4 },
});
