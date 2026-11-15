import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';
import { readReducedMotion, subscribeReducedMotion } from './logic';

/** Reactive OS reduce-motion preference. False until the async read resolves. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    let alive = true;
    readReducedMotion(AccessibilityInfo).then((v) => {
      if (alive) setReduced(v);
    });
    const unsubscribe = subscribeReducedMotion(AccessibilityInfo, setReduced);
    return () => {
      alive = false;
      unsubscribe();
    };
  }, []);

  return reduced;
}
