import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const billNyayScreenSrc = readFileSync(join(process.cwd(), 'src', 'screens', 'BillNyayScreen.tsx'), 'utf-8');
const daaviSetuScreenSrc = readFileSync(join(process.cwd(), 'src', 'screens', 'DaaviSetuScreen.tsx'), 'utf-8');
const endpointsSrc = readFileSync(join(process.cwd(), 'src', 'api', 'endpoints.ts'), 'utf-8');
const typesSrc = readFileSync(join(process.cwd(), 'src', 'api', 'types.ts'), 'utf-8');
const stringsSrc = readFileSync(join(process.cwd(), 'src', 'translations', 'strings.ts'), 'utf-8');

// Regression coverage for the mobile gap survey's items #1/#2 (BillNyay appeal
// drafting + PDF download/share were previously unreachable from the mobile client
// even though the backend pipeline worked end to end) and #3 (DaaviSetu claim
// package ZIP download) and #8 (universal case deletion parity — DaaviSetu had no
// delete control, only BillNyay did).

describe('BillNyay appeal pipeline is wired to the mobile client (#18/#39/#65/#66)', () => {
  it('endpoints.ts exposes a typed call to POST /cases/{id}/appeal', () => {
    assert.ok(
      /appeal:\s*\(caseId: string, language[^)]*\)\s*=>/.test(endpointsSrc),
      'api.billnyay.appeal must exist'
    );
    assert.ok(
      /\/api\/v1\/billnyay\/cases\/\$\{caseId\}\/appeal\?language=/.test(endpointsSrc),
      'appeal() must POST the real backend route with a language query param'
    );
  });

  it('types.ts declares BillNyayAppealResponse matching the backend AppealResponse contract', () => {
    const interfaceMatch = typesSrc.match(/interface BillNyayAppealResponse \{[\s\S]*?\n\}/);
    assert.ok(interfaceMatch, 'BillNyayAppealResponse interface not found');
    const body = interfaceMatch![0];
    for (const field of [
      'appeal_letter',
      'scorecard',
      'status',
      'denial_facts_extracted',
      'llm_backed',
      'consensus',
      'revision_count',
      'pdf_download_url',
    ]) {
      assert.ok(new RegExp(`${field}[?:]`).test(body), `BillNyayAppealResponse is missing field: ${field}`);
    }
  });

  it('BillNyayScreen calls api.billnyay.appeal and stores the result', () => {
    assert.ok(/api\.billnyay\.appeal\(caseId, language\)/.test(billNyayScreenSrc));
    assert.ok(/setAppealResult\(result\)/.test(billNyayScreenSrc));
  });

  it('the draft-appeal button is only offered once a case exists', () => {
    const buttonBlockMatch = billNyayScreenSrc.match(/\{caseId && \(\s*<Button\s*title=\{appealLoading[\s\S]*?\)\}/);
    assert.ok(buttonBlockMatch, 'draft-appeal Button must be gated on caseId');
  });

  it('never claims LLM grounding when llm_backed is false — must render the offline-template disclosure', () => {
    assert.ok(
      /!appealResult\.llm_backed[\s\S]{0,300}appealTemplateNotice/.test(billNyayScreenSrc),
      'llm_backed === false must render appealTemplateNotice, not be silently dropped'
    );
  });

  it('discloses when denial facts could not be extracted from the document', () => {
    assert.ok(
      /!appealResult\.denial_facts_extracted[\s\S]{0,300}appealFactsNotExtracted/.test(billNyayScreenSrc),
      'denial_facts_extracted === false must render a warning, not be hidden'
    );
  });
});

describe('BillNyay appeal PDF download reuses the authenticated query-token pattern (SEC-08)', () => {
  it('handleDownloadAppealPdf looks up the real case access token, not an unauthenticated request', () => {
    const fnMatch = billNyayScreenSrc.match(/const handleDownloadAppealPdf[\s\S]*?\n  };/);
    assert.ok(fnMatch, 'handleDownloadAppealPdf not found');
    assert.ok(/getCaseAccessToken\(caseId\)/.test(fnMatch![0]));
    assert.ok(/if \(!token\)/.test(fnMatch![0]), 'must guard on a missing token');
    assert.ok(
      /appeal\/pdf\?access_token=\$\{encodeURIComponent\(token\)\}/.test(fnMatch![0]),
      'must hit the real appeal/pdf route with the token attached'
    );
    assert.ok(
      !/console\.(log|warn|error)\([^)]*token/i.test(fnMatch![0]),
      'the access token must never be logged'
    );
  });

  it('handleShareAppeal shares the actual drafted letter text via the native Share sheet', () => {
    assert.ok(/Share\.share\(\{ message: appealResult\.appeal_letter \}\)/.test(billNyayScreenSrc));
  });
});

describe('DaaviSetu claim package ZIP download is wired to the mobile client (#81)', () => {
  it('handleDownloadPackage hits the real claim/package route with the case access token', () => {
    const fnMatch = daaviSetuScreenSrc.match(/const handleDownloadPackage[\s\S]*?\n  };/);
    assert.ok(fnMatch, 'handleDownloadPackage not found');
    assert.ok(/getCaseAccessToken\(caseId\)/.test(fnMatch![0]));
    assert.ok(/if \(!token\)/.test(fnMatch![0]), 'must guard on a missing token');
    assert.ok(
      /claim\/package\?access_token=\$\{encodeURIComponent\(token\)\}/.test(fnMatch![0]),
      'must hit the real ZIP package route, not the single PDF route'
    );
  });

  it('the download-package button is rendered alongside the existing PDF download, not instead of it', () => {
    assert.ok(/onPress=\{handleDownloadPdf\}/.test(daaviSetuScreenSrc));
    assert.ok(/onPress=\{handleDownloadPackage\}/.test(daaviSetuScreenSrc));
  });
});

describe('Universal case deletion parity: DaaviSetu gets the same control BillNyay already had (#8)', () => {
  it('DaaviSetuScreen calls the real DELETE /cases/{id} endpoint, not a local-only reset', () => {
    const fnMatch = daaviSetuScreenSrc.match(/const handleDeleteCase[\s\S]*?\n  };/);
    assert.ok(fnMatch, 'handleDeleteCase not found on DaaviSetuScreen');
    assert.ok(/api\.kadi\.deleteCase\(caseId\)/.test(fnMatch![0]));
    // Local state is cleared by dropping the deleted case and the shared active case.
    assert.ok(/setDeletedCaseId\(caseId\)/.test(fnMatch![0]), 'must clear local case state after real deletion');
    assert.ok(/clearActiveCase\(caseId\)/.test(fnMatch![0]), 'must clear the shared active case too');
  });

  it('confirms before deleting, same UX contract as BillNyayScreen', () => {
    assert.ok(/Alert\.alert\(\s*t\.common\.deleteCaseConfirmTitle/.test(daaviSetuScreenSrc));
  });

  it('shared deleteCase* strings are localized in all 3 languages under common, not just billnyay', () => {
    // The interface declaration (`common: { ...: string; }`) also matches the shape,
    // so only count blocks with actual string literal values.
    const commonBlocks = (stringsSrc.match(/common: \{[\s\S]*?\n\s{4}\}/g) || []).filter((block) =>
      /delete: '/.test(block)
    );
    assert.strictEqual(commonBlocks.length, 3, 'expected one populated common{} block per language');
    for (const block of commonBlocks) {
      assert.ok(/deleteCaseBtn: '/.test(block));
      assert.ok(/deleteCaseConfirmTitle: '/.test(block));
      assert.ok(/deleteCaseConfirmBody: '/.test(block));
    }
  });
});
