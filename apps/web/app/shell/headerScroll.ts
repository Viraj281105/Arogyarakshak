/** Visual state of the sticky header. Neither field changes its height (no layout shift). */
export interface HeaderState {
  /** Raised surface (border + shadow) once the page has scrolled. */
  elevated: boolean;
  /** Slid out of view with a transform (small screens only). */
  hidden: boolean;
}

export interface ScrollInput {
  /** Current window.scrollY. */
  y: number;
  /** scrollY at the previous update. */
  lastY: number;
  /** Below the desktop breakpoint, where hiding is allowed. */
  compact: boolean;
  reducedMotion: boolean;
  /** Drawer open or keyboard focus inside the header: never hide. */
  pinned: boolean;
}

const ELEVATE_AFTER = 8;
const HIDE_AFTER = 120;
const JITTER = 6;

/** Pure: next header state from the scroll position. Unit-tested in tests/shell.test.ts. */
export function nextHeaderState(prev: HeaderState, s: ScrollInput): HeaderState {
  const elevated = s.y > ELEVATE_AFTER;
  if (!s.compact || s.reducedMotion || s.pinned || s.y <= HIDE_AFTER) return { elevated, hidden: false };
  const delta = s.y - s.lastY;
  if (Math.abs(delta) < JITTER) return { elevated, hidden: prev.hidden };
  return { elevated, hidden: delta > 0 };
}
