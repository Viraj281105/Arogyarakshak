import React from 'react';
import { Linking, Share, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../../theme';
import { useLanguage } from '../../hooks/useLanguage';
import { Badge, Button, Card, StatementView } from '../../components';
import { BillNyayAppealResponse } from '../../api';
import { getCaseAccessToken } from '../../api/caseAuth';
import { ENV } from '../../config/env';

/** The drafted appeal letter (5-agent pipeline, #18), its honesty notices, the attributed
 *  clinical statement (ADR-011), and the signed-PDF download and share actions. */
export const AppealCard: React.FC<{
  appealResult: BillNyayAppealResponse;
  caseId: string;
  onError: (message: string) => void;
}> = ({ appealResult, caseId, onError }) => {
  const { colors, spacing, typography } = useTheme();
  const m = useLanguage().t.modules.billnyay;

  // Downloads the exact signed PDF the appeal drafted (#66) — served from stored
  // bytes, never regenerated, so it always matches what was hashed and signed.
  // Same query-token pattern as DaaviSetu's PDF download: Linking.openURL cannot
  // attach a custom header, so the one-time case access token travels as a
  // query parameter on this safe, read-only GET.
  const handleDownloadAppealPdf = async () => {
    const token = getCaseAccessToken(caseId);
    if (!token) {
      onError('Missing this case\'s access token — cannot download the PDF. Re-open the case from a fresh scan.');
      return;
    }
    const pdfUrl = `${ENV.API_BASE_URL}/api/v1/billnyay/cases/${caseId}/appeal/pdf?access_token=${encodeURIComponent(token)}`;
    try {
      const supported = await Linking.canOpenURL(pdfUrl);
      if (supported) {
        await Linking.openURL(pdfUrl);
      }
    } catch (e) {
      console.warn('Cannot open appeal PDF URL:', e);
    }
  };

  const handleShareAppeal = async () => {
    try {
      await Share.share({ message: appealResult.appeal_letter });
    } catch (e) {
      console.warn('Cannot share appeal letter:', e);
    }
  };

  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <View style={[styles.header, { marginBottom: spacing.sm }]}>
        <Text style={[styles.cardTitle, { color: colors.textPrimary, fontSize: typography.sizes.md }]}>
          {m.appealTitle}
        </Text>
        <Badge
          label={appealResult.status === 'approve' ? m.appealApprove : m.appealNeedsRevision}
          variant={appealResult.status === 'approve' ? 'success' : 'warning'}
        />
      </View>

      {!appealResult.llm_backed && (
        <Text style={{ color: '#f59e0b', fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
          {m.appealTemplateNotice}
        </Text>
      )}
      {appealResult.llm_backed && (
        <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
          {m.appealLlmBacked}
        </Text>
      )}
      {!appealResult.denial_facts_extracted && (
        <Text style={{ color: '#f59e0b', fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
          {m.appealFactsNotExtracted}
        </Text>
      )}

      <Text
        style={{ color: colors.textPrimary, fontSize: typography.sizes.sm, lineHeight: 20, marginBottom: spacing.sm }}
      >
        {appealResult.appeal_letter}
      </Text>

      {/* ADR-011: attached verbatim when it exists; its absence is stated, never implied away. */}
      {appealResult.human_clinical_statement_attached ? (
        appealResult.clinical_statements.map((s) => <StatementView key={s.statement_id} statement={s} />)
      ) : (
        <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
          No statement from a named clinician is attached. Clinical reasoning in this letter is general,
          software-drafted reasoning — not a doctor&apos;s opinion. (This note is for you; it is not in the PDF.)
        </Text>
      )}
      <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs, marginBottom: spacing.sm }}>
        The PDF is re-generated whenever a clinician&apos;s statement changes — download it again right before sending.
      </Text>

      <View style={{ gap: spacing.xs }}>
        <Button title={m.downloadAppealPdf} onPress={handleDownloadAppealPdf} variant="outline" />
        <Button title={m.shareAppealBtn} onPress={handleShareAppeal} variant="outline" />
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  cardTitle: { fontWeight: '600' },
});
