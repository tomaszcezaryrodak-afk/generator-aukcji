import { useEffect } from 'react';

/**
 * Locks body scroll while a modal/dialog is open.
 * Restores original overflow value on unmount.
 */
export function useBodyScrollLock() {
  useEffect(() => {
    const original = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = original;
    };
  }, []);
}
