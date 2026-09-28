import React, { useEffect, useRef, useState } from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../theme';
import { Card } from './Card';
import { Badge } from './Badge';
import { Button } from './Button';
import { api } from '../api/endpoints';
import { ApiError, CaseMedicineBenchmark } from '../api/types';
import { createRequestGuard } from '../services/caseProcessing';
import { humanizeEnum } from '../services/labels';
import { describePriceCheck } from '../services/priceCheck';

const BLOCKED = new Set(['AWAITING_HUMAN_READING', 'READERS_DISAGREED', 'READING_NOT_APPLIED', 'OCR_UNCERTAIN']);
const FLAGGABLE = new Set(['READERS_DISAGREED', 'READING_NOT_APPLIED', 'OCR_UNCERTAIN']);

/**
 * DawaCheck for the medicines extracted from the patient's own documents. Shows the
 * server's trust decision per medicine: an entry whose OCR reading humans have not
 * settled is NOT price-checked, and the card says why and how to settle it. Loads only
 * once processing is ready; a stale response never overwrites a newer one.
 */
export const CaseMedicinesCard: React.FC<{
  caseId: string | null;
  ready: boolean;
  refreshToken?: unknown;
  onChanged?: () => void;
}> = ({ caseId, ready, refreshToken, onChanged }) => {
  const { colors, spacing, typography } = useTheme();
  const [rows, setRows] = useState<CaseMedicineBenchmark[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const guard = useRef(createRequestGuard()).current;

  useEffect(() => {
    if (!caseId || !ready) {
      guard.reset();
      setRows(null);
      return;
    }
    const token = guard.begin();
    setError(null);
    api.dawacheck
      .caseBenchmark(caseId)
      .then((data) => {
        if (guard.isCurrent(token)) setRows(data);
      })
      .catch((err: ApiError) => {
        if (guard.isCurrent(token)) setError(err.detail || err.message);
      });
  }, [caseId, ready, refreshToken, tick, guard]);

  if (!caseId || !ready) return null;

  const ask = async (entityId: string) => {
    setBusy(entityId);
    try {
      await api.clinical.flagForTranscription(caseId, entityId);
      onChanged?.();
      setTick((n) => n + 1);
    } catch (err) {
      setError((err as ApiError).detail || (err as ApiError).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card style={{ marginVertical: spacing.sm }}>
      <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: typography.sizes.md }}>💊 Medicines from your documents</Text>
      {error && (
        <View style={{ marginVertical: spacing.xs }}>
          <Text style={{ color: colors.statusDanger, fontSize: typography.sizes.xs }}>⚠️ Could not load the price check: {error}</Text>
          <Button title="Try again" onPress={() => setTick((n) => n + 1)} variant="outline" size="sm" />
        </View>
      )}
      {!rows && !error && (
        <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>Checking your medicines…</Text>
      )}
      {rows && rows.length === 0 && (
        <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
          No medicines were extracted from this case&apos;s documents. You can still check one by name below.
        </Text>
      )}
      {(rows ?? []).map((r) => {
        const state = r.trust?.state ?? '';
        const blocked = BLOCKED.has(state);
        const price = r.benchmark ? describePriceCheck(r.benchmark) : null;
        return (
          <View key={r.entity_id} style={{ borderTopWidth: 1, borderColor: colors.borderSubtle, paddingTop: spacing.xs, marginTop: spacing.xs, gap: 4 }}>
            <Text style={{ color: colors.textPrimary, fontWeight: '600' }}>{r.brand_name}</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              <Badge
                label={blocked ? r.trust?.label ?? humanizeEnum(state) : r.name_provenance === 'HUMAN_REVIEWED' ? 'Human-reviewed' : 'Machine-extracted'}
                variant={blocked ? 'warning' : r.name_provenance === 'HUMAN_REVIEWED' ? 'success' : 'info'}
              />
              {price && <Badge label={price.badge} variant={price.variant} />}
            </View>
            {price ? (
              <View style={{ gap: 2 }}>
                <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
                  {price.billed} · {price.ceiling}
                </Text>
                {price.reason && <Text style={{ color: colors.statusWarning, fontSize: typography.sizes.xs }}>{price.reason}</Text>}
                {price.basisNote && <Text style={{ color: colors.textMuted, fontSize: typography.sizes.xs }}>{price.basisNote}</Text>}
              </View>
            ) : (
              <Text style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>{r.note ?? 'Not price-checked.'}</Text>
            )}
            {blocked && FLAGGABLE.has(state) && (
              <Button
                title={busy === r.entity_id ? 'Requesting…' : 'Ask for a human reading of this entry'}
                onPress={() => ask(r.entity_id)}
                variant="outline"
                size="sm"
                disabled={busy === r.entity_id}
              />
            )}
          </View>
        );
      })}
    </Card>
  );
};
