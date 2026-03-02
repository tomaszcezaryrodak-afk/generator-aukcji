import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Returns a `copied` flag and a `trigger()` function.
 * After calling trigger(), `copied` becomes true for `duration` ms then resets.
 * Cleans up the timer on unmount. Replaces repeated useState+useRef+useEffect pattern.
 */
export function useCopyFeedback(duration = 2000) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const trigger = useCallback(() => {
    setCopied(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), duration);
  }, [duration]);

  return { copied, trigger } as const;
}
