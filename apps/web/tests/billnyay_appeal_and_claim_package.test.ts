import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const billNyayViewSrc = readFileSync(
  join(process.cwd(), 'app', 'components', 'modules', 'BillNyayView.tsx'),
  'utf-8'
);
const daaviSetuViewSrc = readFileSync(
  join(process.cwd(), 'app', 'components', 'modules', 'DaaviSetuView.tsx'),
  'utf-8'
);

// Regression coverage for the mobile-gap survey's web-side findings: the flagship
// appeal-drafting pipeline (#18/#66) was reachable from the API but neither client
// ever called it, and DaaviSetu's ZIP claim package (#81) was likewise never
// downloaded from either client — only the single PDF was.

describe('BillNyay web view drafts and downloads the appeal letter (#18/#66)', () => {
  it('handleDraftAppeal calls the real 5-agent appeal endpoint with the case access token', () => {
    const fnMatch = billNyayViewSrc.match(/const handleDraftAppeal = async \(\) => \{[\s\S]*?\n  \};/);
    assert.ok(fnMatch, 'handleDraftAppeal not found');
    assert.ok(
      /\/api\/v1\/billnyay\/cases\/\$\{caseId\}\/appeal\?language=/.test(fnMatch![0]),
      'must POST the real appeal route with a language query param'
    );
    assert.ok(/caseAuthHeaders\(caseToken\)/.test(fnMatch![0]), 'must attach the case access token');
  });

  it('never claims LLM grounding when llm_backed is false — renders the offline-template disclosure', () => {
    assert.ok(
      /!appealData\.llm_backed[\s\S]{0,700}Offline template/.test(billNyayViewSrc),
      'llm_backed === false must render a disclosure, not be silently dropped'
    );
  });

  it('discloses when denial facts could not be extracted from the document', () => {
    assert.ok(
      /!appealData\.denial_facts_extracted[\s\S]{0,700}could not be extracted/.test(billNyayViewSrc),
      'denial_facts_extracted === false must render a warning, not be hidden'
    );
  });

  it('renders the actual drafted letter text, not a placeholder', () => {
    assert.ok(/\{appealData\.appeal_letter\}/.test(billNyayViewSrc));
  });

  it('downloads the exact signed PDF via an authenticated blob fetch, not a plain <a href>', () => {
    const fnMatch = billNyayViewSrc.match(/const handleDownloadAppealPdf = async \(\) => \{[\s\S]*?\n  \};/);
    assert.ok(fnMatch, 'handleDownloadAppealPdf not found');
    assert.ok(
      /\/api\/v1\/billnyay\/cases\/\$\{caseId\}\/appeal\/pdf/.test(fnMatch![0]),
      'must fetch the real appeal/pdf route'
    );
    assert.ok(/caseAuthHeaders\(caseToken\)/.test(fnMatch![0]), 'must attach the case access token');
    assert.ok(/res\.blob\(\)/.test(fnMatch![0]), 'must download as a blob, matching the DaaviSetu PDF pattern');
  });

  it('the appeal action button only renders once a case actually exists', () => {
    assert.ok(
      /\{caseId && \(\s*<div[\s\S]*?onClick=\{handleDraftAppeal\}/.test(billNyayViewSrc),
      'the draft-appeal button must be gated on an active caseId'
    );
  });
});

describe('DaaviSetu web view downloads the full claim package ZIP (#81)', () => {
  it('handleDownloadPackage fetches the real ZIP route, not the single-PDF route', () => {
    const fnMatch = daaviSetuViewSrc.match(/const handleDownloadPackage = \(\)[\s\S]*?claim package"\);/);
    assert.ok(fnMatch, 'handleDownloadPackage not found');
    assert.ok(
      /\/api\/v1\/daavisetu\/cases\/\$\{caseId\}\/claim\/package/.test(fnMatch![0]),
      'must target the claim/package route, not claim/pdf'
    );
  });

  it('the ZIP download button is rendered alongside the existing PDF download, not instead of it', () => {
    assert.ok(/onClick=\{handleDownloadPdf\}/.test(daaviSetuViewSrc));
    assert.ok(/onClick=\{handleDownloadPackage\}/.test(daaviSetuViewSrc));
  });

  it('both downloads share the authenticated blob-fetch helper, so the ZIP is not fetched unauthenticated', () => {
    const helperMatch = daaviSetuViewSrc.match(/const downloadBlob = async[\s\S]*?\n  \};/);
    assert.ok(helperMatch, 'downloadBlob helper not found');
    assert.ok(/caseAuthHeaders\(caseToken\)/.test(helperMatch![0]));
  });
});
