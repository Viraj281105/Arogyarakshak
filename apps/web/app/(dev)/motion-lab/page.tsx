import { notFound } from "next/navigation";
import Magnetic from "../../motion/Magnetic";
import Parallax from "../../motion/Parallax";
import Reveal from "../../motion/Reveal";
import ScrollScrub from "../../motion/ScrollScrub";
import LabCountUp from "./LabCountUp";
import LabStatus from "./LabStatus";

const card = {
  padding: "2rem",
  margin: "0 0 12rem",
  border: "1px solid currentColor",
  borderRadius: "0.75rem",
} as const;

// Dev-only gallery of every motion pattern. Not linked anywhere; 404s in production builds.
export default function MotionLabPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return (
    <main style={{ maxWidth: "40rem", margin: "0 auto", padding: "2rem 1rem 8rem" }}>
      <h1>Motion lab</h1>
      <LabStatus />
      <section style={{ ...card, marginTop: "2rem" }}>
        <h2>Magnetic</h2>
        <Magnetic>
          <button type="button">Hover me</button>
        </Magnetic>
      </section>
      <section style={card}>
        <h2>CountUp</h2>
        <p style={{ fontSize: "2rem" }}>
          <LabCountUp />
        </p>
      </section>
      <section style={card}>
        <h2>Reveal</h2>
        <Reveal>
          <p data-testid="reveal">Fades in on entry. Visible without scroll timelines.</p>
        </Reveal>
      </section>
      <section style={card}>
        <h2>Parallax</h2>
        <Parallax>
          <p data-testid="parallax">Drifts as it crosses the viewport.</p>
        </Parallax>
      </section>
      <section style={card}>
        <h2>ScrollScrub</h2>
        <ScrollScrub>
          <p data-testid="scrub">Settles in, tied to scroll position.</p>
        </ScrollScrub>
      </section>
    </main>
  );
}
