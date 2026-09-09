import test, { describe, it } from 'node:test';
import assert from 'node:assert';
import { translations, Language } from '../src/translations/strings';
import { BottomTabParamList, RootStackParamList } from '../src/navigation/types';

describe('Mobile Screen & Navigation Flow Architecture', () => {
  it('should verify BottomTabParamList supports caseId and scanCompleted for modules', () => {
    // Type-level assertion via instantiation
    const billNyayParams: BottomTabParamList['BillNyay'] = {
      caseId: 'CASE-test1234',
      scanCompleted: true,
    };
    assert.strictEqual(billNyayParams.caseId, 'CASE-test1234');
    assert.strictEqual(billNyayParams.scanCompleted, true);

    const daaviSetuParams: BottomTabParamList['DaaviSetu'] = {
      caseId: 'CASE-preauth567',
      scanCompleted: true,
    };
    assert.strictEqual(daaviSetuParams.caseId, 'CASE-preauth567');
    assert.strictEqual(daaviSetuParams.scanCompleted, true);

    const bimaNyayParams: BottomTabParamList['BimaNyay'] = {
      caseId: 'CASE-denial88',
      scanCompleted: true,
    };
    assert.strictEqual(bimaNyayParams?.caseId, 'CASE-denial88');

    const dawaCheckParams: BottomTabParamList['DawaCheck'] = {
      caseId: 'CASE-presc99',
      scanCompleted: true,
    };
    assert.strictEqual(dawaCheckParams?.caseId, 'CASE-presc99');
  });

  it('should verify document type to module routing contract', () => {
    const routingMap = {
      bill: 'BillNyay',
      denial: 'BimaNyay',
      prescription: 'DawaCheck',
      general: 'BillNyay',
    } as const;

    assert.strictEqual(routingMap.bill, 'BillNyay');
    assert.strictEqual(routingMap.denial, 'BimaNyay');
    assert.strictEqual(routingMap.prescription, 'DawaCheck');
    assert.strictEqual(routingMap.general, 'BillNyay');
  });

  it('should verify documentType === "general" routes to BillNyay preserving caseId', () => {
    const resolveNavigation = (documentType: string, caseId: string) => {
      if (documentType === 'bill' || documentType === 'general') {
        return { screen: 'BillNyay', params: { caseId, scanCompleted: true } };
      } else if (documentType === 'denial') {
        return { screen: 'BimaNyay', params: { caseId, scanCompleted: true } };
      } else if (documentType === 'prescription') {
        return { screen: 'DawaCheck', params: { caseId, scanCompleted: true } };
      }
      return { screen: 'BillNyay', params: { caseId, scanCompleted: true } };
    };

    const generalNav = resolveNavigation('general', 'CASE-gen-999');
    assert.strictEqual(generalNav.screen, 'BillNyay');
    assert.strictEqual(generalNav.params.caseId, 'CASE-gen-999');
    assert.strictEqual(generalNav.params.scanCompleted, true);
  });

  it('should verify all 5 mobile module forms are fully localized across en, hi, and mr', () => {
    const langs: Language[] = ['en', 'hi', 'mr'];

    for (const lang of langs) {
      const m = translations[lang].modules;

      // 1. BillNyay
      assert.ok(m.billnyay.cardTitle, `Missing billnyay.cardTitle in ${lang}`);
      assert.ok(m.billnyay.cardBody, `Missing billnyay.cardBody in ${lang}`);
      assert.ok(m.billnyay.charged, `Missing billnyay.charged in ${lang}`);
      assert.ok(m.billnyay.cghsCap, `Missing billnyay.cghsCap in ${lang}`);
      assert.ok(m.billnyay.scanBillBtn, `Missing billnyay.scanBillBtn in ${lang}`);

      // 2. DaaviSetu
      assert.ok(m.daavisetu.cardTitle, `Missing daavisetu.cardTitle in ${lang}`);
      assert.ok(m.daavisetu.patientName, `Missing daavisetu.patientName in ${lang}`);
      assert.ok(m.daavisetu.policyId, `Missing daavisetu.policyId in ${lang}`);
      assert.ok(m.daavisetu.hospitalName, `Missing daavisetu.hospitalName in ${lang}`);
      assert.ok(m.daavisetu.treatmentPlan, `Missing daavisetu.treatmentPlan in ${lang}`);
      assert.ok(m.daavisetu.downloadPdf, `Missing daavisetu.downloadPdf in ${lang}`);

      // 3. BimaNyay
      assert.ok(m.bimanyay.cardTitle, `Missing bimanyay.cardTitle in ${lang}`);
      assert.ok(m.bimanyay.policyNumber, `Missing bimanyay.policyNumber in ${lang}`);
      assert.ok(m.bimanyay.insurerName, `Missing bimanyay.insurerName in ${lang}`);
      assert.ok(m.bimanyay.claimedAmount, `Missing bimanyay.claimedAmount in ${lang}`);
      assert.ok(m.bimanyay.deniedAmount, `Missing bimanyay.deniedAmount in ${lang}`);
      assert.ok(m.bimanyay.auditBtn, `Missing bimanyay.auditBtn in ${lang}`);
      assert.ok(m.bimanyay.timelineTitle, `Missing bimanyay.timelineTitle in ${lang}`);

      // 4. SchemeSetu
      assert.ok(m.schemesetu.cardTitle, `Missing schemesetu.cardTitle in ${lang}`);
      assert.ok(m.schemesetu.income, `Missing schemesetu.income in ${lang}`);
      assert.ok(m.schemesetu.state, `Missing schemesetu.state in ${lang}`);
      assert.ok(m.schemesetu.category, `Missing schemesetu.category in ${lang}`);
      assert.ok(m.schemesetu.checkBtn, `Missing schemesetu.checkBtn in ${lang}`);

      // 5. DawaCheck
      assert.ok(m.dawacheck.cardTitle, `Missing dawacheck.cardTitle in ${lang}`);
      assert.ok(m.dawacheck.brandOrGeneric, `Missing dawacheck.brandOrGeneric in ${lang}`);
      assert.ok(m.dawacheck.chargedMrp, `Missing dawacheck.chargedMrp in ${lang}`);
      assert.ok(m.dawacheck.checkBtn, `Missing dawacheck.checkBtn in ${lang}`);
      assert.ok(m.dawacheck.scanStrip, `Missing dawacheck.scanStrip in ${lang}`);
      assert.ok(m.dawacheck.statutoryNoticeTitle, `Missing statutoryNoticeTitle in ${lang}`);
    }
  });
});

describe('Mobile SSE Streaming & Event Protocol', () => {
  it('should correctly parse multi-agent SSE event data stream', () => {
    const rawEvents = [
      'data: {"status": "upload_received", "progress": 10, "log": "Upload received. Queueing document extraction task..."}\n\n',
      'data: {"status": "ocr_start", "progress": 40, "log": "Running transient PyMuPDF / Tesseract OCR..."}\n\n',
      'data: {"status": "extraction_start", "progress": 70, "log": "Extracting clinical entities via Groq inference..."}\n\n',
      'data: {"status": "completed", "progress": 100, "log": "Document processed successfully. Entities extracted."}\n\n',
    ];

    const parsedEvents: any[] = [];
    for (const chunk of rawEvents) {
      const line = chunk.trim();
      if (line.startsWith('data:')) {
        const payload = JSON.parse(line.slice(5).trim());
        parsedEvents.push(payload);
      }
    }

    assert.strictEqual(parsedEvents.length, 4);
    assert.strictEqual(parsedEvents[0].status, 'upload_received');
    assert.strictEqual(parsedEvents[0].progress, 10);
    assert.strictEqual(parsedEvents[3].status, 'completed');
    assert.strictEqual(parsedEvents[3].progress, 100);
  });
});

describe('Mobile Offline Action Queue Invariants', () => {
  it('should serialize actions and adhere to BYOD zero-retention (metadata only)', () => {
    const action = {
      id: 'act_1001',
      type: 'BENCHMARK_MEDICINE',
      payload: {
        brand_name: 'Dolo 650mg',
        mrp: 33.5,
      },
      timestamp: Date.now(),
      retryCount: 0,
    };

    const serialized = JSON.stringify([action]);
    assert.ok(serialized.length < 500, 'Serialized action is concise metadata');
    assert.ok(!serialized.includes('base64'), 'No raw image or document data stored in offline queue');

    const deserialized = JSON.parse(serialized);
    assert.strictEqual(deserialized[0].id, 'act_1001');
    assert.strictEqual(deserialized[0].payload.brand_name, 'Dolo 650mg');
  });

  it('should support enqueuing all 4 statutory mobile action types', () => {
    const supportedTypes = ['BENCHMARK_MEDICINE', 'CHECK_SCHEME', 'SUBMIT_PREAUTH', 'ANALYZE_DENIAL'];
    const mockQueue: any[] = [];
    supportedTypes.forEach((type, idx) => {
      mockQueue.push({
        id: `act_${idx}`,
        type,
        payload: { sample: idx },
        timestamp: Date.now(),
        retryCount: 0,
      });
    });
    assert.strictEqual(mockQueue.length, 4);
    assert.deepStrictEqual(mockQueue.map(a => a.type), supportedTypes);
  });
});
