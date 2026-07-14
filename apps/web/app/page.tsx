export default function Home() {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <h1 style={{ fontSize: "2.5rem", fontWeight: 700, marginBottom: "1rem" }}>
        ArogyaRakshak
      </h1>
      <p style={{ fontSize: "1.125rem", opacity: 0.7 }}>
        Patient-facing bill audit, scheme eligibility &amp; medicine pricing
        platform.
      </p>
    </main>
  );
}
