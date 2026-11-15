"use client";

import CountUp from "../../motion/CountUp";

// `format` is a function, so it must be defined on the client side of the boundary.
export default function LabCountUp() {
  return <CountUp to={1234567} format={(n) => `Rs ${Math.round(n).toLocaleString("en-IN")}`} />;
}
