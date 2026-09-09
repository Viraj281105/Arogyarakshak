"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";

interface BimaNyayViewProps {
  currentLang: Language;
}

export const BimaNyayView: React.FC<BimaNyayViewProps> = ({ currentLang }) => {
  const t = translations[currentLang].modules.bimanyay;

  // Form State
  const [policyNumber, setPolicyNumber] = useState("POL-884422");
  const [insurerName, setInsurerName] = useState("Star Health & Allied Insurance");
  const [policyAgeYears, setPolicyAgeYears] = useState("6.0");
  const [claimedAmount, setClaimedAmount] = useState("180000");
  const [deniedAmount, setDeniedAmount] = useState("180000");
  const [denialCategory, setDenialCategory] = useState("PED_NON_DISCLOSURE");
  const [denialReason, setDenialReason] = useState(
    "Claim repudiated due to alleged non-disclosure of hypertension at policy inception."
  );
  const [diagnosis, setDiagnosis] = useState("Acute Myocardial Infarction");

  // Output State
  const [activeTab, setActiveTab] = useState<"gro" | "bimabharosa" | "ombudsman">("gro");
  const [copied, setCopied] = useState(false);
  const [isAudited, setIsAudited] = useState(true);

  const reversalScore = parseFloat(policyAgeYears) >= 5.0 && denialCategory === "PED_NON_DISCLOSURE" ? 0.95 : 0.85;

  const formattedClaimed = parseFloat(claimedAmount || "0").toLocaleString("en-IN");
  const formattedDenied = parseFloat(deniedAmount || "0").toLocaleString("en-IN");

  const groLetter =
    currentLang === "hi"
      ? `प्रति:
शिकायत निवारण अधिकारी (GRO)
${insurerName}

विषय: पॉलिसी संख्या ${policyNumber} के अंतर्गत दावा निरस्तीकरण के विरुद्ध औपचारिक सांविधिक अपील

महोदय / महोदया,

मैं ${diagnosis} के उपचार हेतु कुल दावा राशि ₹${formattedClaimed} में से अस्वीकृत / काटी गई राशि ₹${formattedDenied} के मनमाने और विधि-विरुद्ध निरस्तीकरण के विरुद्ध यह औपचारिक सांविधिक अपील दर्ज कर रहा हूँ।

बीमाकर्ता द्वारा दिया गया निरस्तीकरण कारण:
"${denialReason}"

अपील के सांविधिक आधार:
1. IRDAI स्वास्थ्य बीमा मास्टर परिपत्र (२९ मई २०२४), धारा १६ के अनुसार ५ निरंतर नवीकरण वर्षों के पश्चात कोई भी स्वास्थ्य बीमा दावा पूर्व-मौजूदा बीमारी (PED) या गैर-प्रकटीकरण के आधार पर निरस्त नहीं किया जा सकता। यह पॉलिसी निरंतर ${policyAgeYears} वर्षों से सक्रिय है, अतः यह निरस्तीकरण कानूनन वर्जित है।
2. ३-सदस्यीय दावा समीक्षा समिति (CRC) के पूर्व लिखित अनुमोदन के बिना कोई भी दावा निरस्त नहीं किया जा सकता।

अतः आपसे अनुरोध है कि मेरे दावे की निष्पक्ष पुनर्परीक्षा कर १५ दिनों की सांविधिक समय-सीमा के भीतर स्वीकार्य दावा राशि ₹${formattedDenied} जारी करने की कृपा करें। समाधान न होने पर यह प्रकरण IRDAI बीमा भरोसा पोर्टल एवं बीमा लोकपाल के समक्ष प्रस्तुत किया जाएगा।

भवदीय,
पॉलिसीधारक (पॉलिसी संख्या: ${policyNumber})`
      : currentLang === "mr"
      ? `प्रति:
तक्रार निवारण अधिकारी (GRO)
${insurerName}

विषय: पॉलिसी क्र. ${policyNumber} अंतर्गत दावा नाकारल्याबाबत कायदेशीर वैधानिक अपील

महोदय / महोदया,

मी ${diagnosis} च्या उपचारासाठी एकूण दावा रक्कम ₹${formattedClaimed} पैकी नाकारण्यात आलेली ₹${formattedDenied} या रकमेच्या अवाजवी व एकतर्फी नकाराविरुद्ध ही औपचारिक वैधानिक तक्रार नोंदवत आहे.

विमा कंपनीने दिलेले नकाराचे कारण:
"${denialReason}"

अपीलचे कायदेशीर आधार:
1. IRDAI आरोग्य विमा मास्टर परिपत्रक (२९ मे २०२४), कलम १६ नुसार ५ सलग नूतनीकरण वर्षांनंतर कोणताही आरोग्य विमा दावा पूर्व-अस्तित्वात असलेला आजार (PED) किंवा माहिती न दिल्याचा आरोप करून नाकारता येत नाही. ही पॉलिसी सलग ${policyAgeYears} वर्षे सक्रिय असल्याने कंपनीचा नकार कायद्याने पूर्णतः अवैध आहे.
2. ३-सदस्यीय दावा पुनरावलोकन समितीच्या (CRC) पूर्व लेखी मंजुरीशिवाय कोणताही दावा नाकारता येत नाही.

तरी माझ्या दाव्याची फेरतपासणी करून १५ दिवसांच्या वैधानिक मुदतीत पात्र रक्कम ₹${formattedDenied} मंजूर करावी. अन्यथा सदर प्रकरण IRDAI विमा भरोसा पोर्टल व विमा लोकपाल यांच्याकडे वर्ग केले जाईल.

आपला नम्र,
पॉलिसीधारक (पॉलिसी क्र: ${policyNumber})`
      : `TO:
The Grievance Redressal Officer (GRO)
${insurerName}

SUBJECT: Formal Appeal Against Wrongful Repudiation of Claim Under Policy No. ${policyNumber}

Dear Sir / Madam,

I am writing to register an urgent statutory grievance against the wrongful repudiation of my health insurance claim amounting to INR ${formattedDenied} out of total expenses of INR ${formattedClaimed} for treatment of ${diagnosis}.

REASON CITED BY INSURER:
"${denialReason}"

STATUTORY GROUNDS OF APPEAL:
1. Under the IRDAI Master Circular on Health Insurance Business (May 29, 2024), Clause 16 stipulates an absolute Moratorium Period of 5 continuous years. This policy has completed ${policyAgeYears} continuous renewal years; therefore, contesting this claim on grounds of non-disclosure is barred by law.
2. No claim can be repudiated without prior written approval of the 3-member Claims Review Committee (CRC).

I request immediate release of the admissible settlement amount of INR ${formattedDenied} within the 15-day statutory resolution window.

Yours faithfully,
Policyholder (Policy No: ${policyNumber})`;

  const bimaBharosaText =
    currentLang === "hi"
      ? `${insurerName} द्वारा अनुचित दावा निरस्तीकरण के विरुद्ध शिकायत। पॉलिसी संख्या: ${policyNumber}। अस्वीकृत राशि: ₹${formattedDenied}। कंपनी का कारण: '${denialReason}'। आधार: पॉलिसी निरंतर ${policyAgeYears} वर्षों से सक्रिय है। पूर्व-मौजूदा बीमारी का दावा IRDAI मास्टर परिपत्र २०२४ धारा १६ (५-वर्षीय अधिस्थगन नियम) का सीधा उल्लंघन है। कंपनी १५ दिवसीय सांविधिक सीमा में समाधान देने में विफल रही। IRDAI से २% अतिरिक्त बैंक दर दंडात्मक ब्याज सहित दावा निपटान का निर्देश देने का अनुरोध है।`
      : currentLang === "mr"
      ? `${insurerName} विरुद्ध दावा अवाजवीपणे नाकारल्याबाबत तक्रार. पॉलिसी क्र: ${policyNumber}. नाकारलेली रक्कम: ₹${formattedDenied}. विमा कंपनीचे कारण: '${denialReason}'. आधार: पॉलिसी सलग ${policyAgeYears} वर्षे चालू आहे. पूर्व-आजार कारणास्तव नकार देणे IRDAI मास्टर परिपत्रक २०२४ कलम १६ (५ वर्षांचा स्थगिती कालावधी नियम) चे थेट उल्लंघन आहे. कंपनीने १५ दिवसांत निवारण केले नाही. IRDAI ने कंपनीस २% दंडात्मक व्याजासह तत्काळ भरपाई देण्याचे निर्देश द्यावेत ही नम्र विनंती.`
      : `Grievance against ${insurerName} for wrongful claim repudiation. Policy No: ${policyNumber}. Disallowed Amount: INR ${formattedDenied}. Rejection Reason: "${denialReason}". Grounds: Policy is ${policyAgeYears} years continuously active. Contesting under PED violates IRDAI Master Circular Clause 16 (5-Year Moratorium rule). Insurer failed to resolve within statutory window. Requesting IRDAI direction for immediate settlement with 2% penal interest.`;

  const ombudsmanStatement =
    currentLang === "hi"
      ? `बीमा लोकपाल के समक्ष शिकायत हेतु तथ्यों का विवरण
(बीमा लोकपाल नियम, २०१७ के नियम १४(१)(बी) के अंतर्गत)

१. शिकायतकर्ता का नाम एवं विवरण: [पॉलिसीधारक का नाम]
२. बीमाकर्ता कंपनी का नाम: ${insurerName}
३. पॉलिसी संख्या: ${policyNumber} (सक्रियता अवधि: ${policyAgeYears} वर्ष)
४. कुल दावा राशि: ₹${formattedClaimed} | अस्वीकृत राशि: ₹${formattedDenied}
५. बीमारी / उपचार का विवरण: ${diagnosis}
६. विधिक अनुतोष के आधार:
अस्वीकृति IRDAI मास्टर परिपत्र २०२४ के ५-वर्षीय अधिस्थगन (Moratorium) नियम का खुला उल्लंघन करती है। बीमाकर्ता ने विधिक संरक्षण की अवहेलना करते हुए मनमाने ढंग से कार्य किया है।
७. प्रार्थित अनुतोष:
${insurerName} को ₹${formattedDenied} की राशि विलंबित निपटान हेतु बैंक दर से २% अतिरिक्त सांविधिक दंडात्मक ब्याज सहित भुगतान करने का निर्देश जारी किया जाए।`
      : currentLang === "mr"
      ? `विमा लोकपाल यांच्याकडे तक्रारीसाठी वस्तुस्थितीचे विवरण
(विमा लोकपाल नियम, २०१७ च्या नियम १४(१)(बी) अन्वये)

१. तक्रारदाराचे नाव व तपशील: [पॉलिसीधारकाचे नाव]
२. विमा कंपनीचे नाव: ${insurerName}
३. पॉलिसी क्रमांक: ${policyNumber} (सलग कालावधी: ${policyAgeYears} वर्षे)
४. एकूण दावा रक्कम: ₹${formattedClaimed} | नाकारलेली रक्कम: ₹${formattedDenied}
५. आजार / उपचाराचे स्वरूप: ${diagnosis}
६. कायदेशीर दाव्याचे आधार:
सदर नकार IRDAI मास्टर परिपत्रक २०२४ मधील ५ वर्षांच्या मॉरेटोरियम नियमाचे थेट उल्लंघन करतो. विमा कंपनीने वैधानिक संरक्षणाची पायमल्ली करून मनमानी कारभार केला आहे.
७. मागितलेले कायदेशीर निवारण:
${insurerName} विमा कंपनीस नाकारलेली रक्कम ₹${formattedDenied} ही रक्कम विलंबित दाव्यावर बँक दरापेक्षा २% अधिक दंडात्मक व्याजासह देण्याचे निर्देश देण्यात यावेत.`
      : `STATEMENT OF FACTS FOR COMPLAINT TO INSURANCE OMBUDSMAN
(Under Rule 14(1)(b) of Insurance Ombudsman Rules, 2017)

1. Complainant / Insured: [Policyholder Name]
2. Insurer: ${insurerName}
3. Policy Number: ${policyNumber} (Continuous tenure: ${policyAgeYears} years)
4. Total Claim: INR ${formattedClaimed} | Repudiated: INR ${formattedDenied}
5. Medical Diagnosis: ${diagnosis}
6. Grounds for Statutory Relief:
Repudiation violates the 5-Year Moratorium clause mandated by IRDAI Master Circular 2024. Insurer acted arbitrarily in defiance of statutory protection.
7. Relief Sought: Order directing ${insurerName} to settle INR ${formattedDenied} plus 2% above bank rate penal interest.`;

  const handleCopy = () => {
    let textToCopy = groLetter;
    if (activeTab === "bimabharosa") textToCopy = bimaBharosaText;
    if (activeTab === "ombudsman") textToCopy = ombudsmanStatement;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Input Form */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          padding: "1.25rem",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-subtle)",
          marginBottom: "1.5rem",
        }}
      >
        <h3 style={{ marginBottom: "1rem" }}>{t.formTitle}</h3>

        <div className="grid-2" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.policyNumber}</label>
            <input
              type="text"
              className="input-field"
              value={policyNumber}
              onChange={(e) => setPolicyNumber(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.insurerName}</label>
            <input
              type="text"
              className="input-field"
              value={insurerName}
              onChange={(e) => setInsurerName(e.target.value)}
            />
          </div>
        </div>

        <div className="grid-3" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.policyAgeYears}</label>
            <input
              type="number"
              step="0.5"
              className="input-field"
              value={policyAgeYears}
              onChange={(e) => setPolicyAgeYears(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.claimedAmount}</label>
            <input
              type="number"
              className="input-field"
              value={claimedAmount}
              onChange={(e) => setClaimedAmount(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.deniedAmount}</label>
            <input
              type="number"
              className="input-field"
              value={deniedAmount}
              onChange={(e) => setDeniedAmount(e.target.value)}
            />
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.denialCategory}</label>
            <select
              className="select-field"
              value={denialCategory}
              onChange={(e) => setDenialCategory(e.target.value)}
            >
              <option value="PED_NON_DISCLOSURE">Pre-Existing Disease Non-Disclosure</option>
              <option value="ROOM_RENT_CAPPING">Room Rent Proportionate Deduction</option>
              <option value="INVESTIGATION_ONLY">Observation / Diagnostic Hospitalization Only</option>
              <option value="DELAYED_INTIMATION">Delayed Claim Intimation / Submission</option>
            </select>
          </div>
          <div>
            <label className="input-label">{t.diagnosis}</label>
            <input
              type="text"
              className="input-field"
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
            />
          </div>
        </div>

        <div style={{ marginBottom: "1.25rem" }}>
          <label className="input-label">{t.denialReason}</label>
          <textarea
            className="textarea-field"
            rows={2}
            value={denialReason}
            onChange={(e) => setDenialReason(e.target.value)}
          />
        </div>

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={() => setIsAudited(true)}
        >
          ⚖️ {t.analyzeBtn}
        </button>
      </div>

      {/* Audit Results */}
      {isAudited && (
        <div>
          <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-box" style={{ borderLeft: "4px solid var(--status-success)" }}>
              <div className="stat-label">{t.reversalScore}</div>
              <div className="stat-val" style={{ color: "var(--brand-emerald)" }}>
                {(reversalScore * 100).toFixed(0)}%
              </div>
              <span className="badge badge-success" style={{ marginTop: "0.5rem" }}>
                ✓ {t.wrongfulBadge}
              </span>
            </div>

            <div className="stat-box" style={{ borderLeft: "4px solid var(--brand-cyan)" }}>
              <div className="stat-label">{t.violationsTitle}</div>
              <ul style={{ listStyle: "none", marginTop: "0.5rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                <li>
                  <strong style={{ color: "var(--brand-cyan)" }}>IRDAI Master Circular (2024):</strong> Clause 16 (5-Yr Moratorium protection)
                </li>
                <li>
                  <strong style={{ color: "var(--brand-cyan)" }}>Claims Review Committee:</strong> Mandatory 3-member CRC clearance missing
                </li>
              </ul>
            </div>
          </div>

          {/* Appeals Tab Selector */}
          <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.5rem", marginBottom: "1rem", overflowX: "auto" }}>
            <button
              type="button"
              className={`btn ${activeTab === "gro" ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
              onClick={() => setActiveTab("gro")}
            >
              {t.groTab}
            </button>
            <button
              type="button"
              className={`btn ${activeTab === "bimabharosa" ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
              onClick={() => setActiveTab("bimabharosa")}
            >
              {t.bimaBharosaTab}
            </button>
            <button
              type="button"
              className={`btn ${activeTab === "ombudsman" ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
              onClick={() => setActiveTab("ombudsman")}
            >
              {t.ombudsmanTab}
            </button>
          </div>

          {/* Appeal Content */}
          <div style={{ position: "relative", marginBottom: "1.5rem" }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ position: "absolute", top: "0.75rem", right: "0.75rem", fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
              onClick={handleCopy}
            >
              {copied ? `✓ ${t.copied}` : `📋 ${t.copyDraft}`}
            </button>

            <pre
              style={{
                background: "var(--bg-base)",
                padding: "1rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                fontSize: "0.85rem",
                fontFamily: "monospace",
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
                lineHeight: 1.6,
                maxHeight: "340px",
                overflowY: "auto",
              }}
            >
              {activeTab === "gro" && groLetter}
              {activeTab === "bimabharosa" && bimaBharosaText}
              {activeTab === "ombudsman" && ombudsmanStatement}
            </pre>
          </div>

          {/* Statutory SLA Tracker */}
          <div>
            <h3>⏳ {t.timelineTitle}</h3>
            <div className="timeline-list">
              <div className="timeline-item">
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: "var(--text-primary)" }}>{t.tier1Label}</strong>
                    <span className="badge badge-info">ACTIVE</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                    Formal appeal pending with {insurerName} GRO. Mandatory resolution window: 15 days.
                  </p>
                </div>
              </div>

              <div className="timeline-item">
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: "var(--text-secondary)" }}>{t.tier2Label}</strong>
                    <span className="badge" style={{ background: "rgba(255,255,255,0.08)", color: "var(--text-muted)" }}>PENDING</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                    Escalate via IRDAI Bima Bharosa portal if GRO fails to resolve or rejects claim.
                  </p>
                </div>
              </div>

              <div className="timeline-item">
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: "var(--text-secondary)" }}>{t.tier3Label}</strong>
                    <span className="badge" style={{ background: "rgba(255,255,255,0.08)", color: "var(--text-muted)" }}>PENDING</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                    Binding arbitration with Insurance Ombudsman within 1 year. Awards up to ₹50 Lakhs.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
