import { useState, useRef, useEffect, useCallback } from 'react';

const AUTO_CANCEL_MS = 5000;

interface UseConfirmReturn {
  /** Whether the confirmation is pending (first click done, awaiting second) */
  isConfirming: boolean;
  /** Call on click: first click arms, second click fires onConfirm */
  handleClick: () => void;
  /** Call on blur to reset confirmation state */
  handleBlur: () => void;
}

/**
 * 2-click confirmation pattern with 5s auto-cancel.
 * Used for destructive actions (cancel generation, logout during generation).
 */
export function useConfirm(onConfirm: () => void): UseConfirmReturn {
  const [isConfirming, setIsConfirming] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  useEffect(() => {
    if (!isConfirming) return;
    timer.current = setTimeout(() => setIsConfirming(false), AUTO_CANCEL_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [isConfirming]);

  const handleClick = useCallback(() => {
    if (!isConfirming) {
      setIsConfirming(true);
      return;
    }
    setIsConfirming(false);
    if (timer.current) clearTimeout(timer.current);
    onConfirm();
  }, [isConfirming, onConfirm]);

  const handleBlur = useCallback(() => {
    setIsConfirming(false);
  }, []);

  return { isConfirming, handleClick, handleBlur };
}
