import { useCallback, useRef } from 'react';

/**
 * Browser Notification API hook.
 * Requests permission proactively and fires a system notification
 * when generation finishes while tab is in background.
 */
export function useNotification() {
  const permissionRef = useRef<NotificationPermission>(
    'Notification' in window ? Notification.permission : 'denied',
  );

  const requestPermission = useCallback(async () => {
    if (!('Notification' in window)) return;
    if (permissionRef.current === 'granted') return;
    try {
      const result = await Notification.requestPermission();
      permissionRef.current = result;
    } catch {
      // Safari older versions throw on requestPermission
    }
  }, []);

  const notify = useCallback((title: string, body?: string) => {
    if (!('Notification' in window)) return;
    if (permissionRef.current !== 'granted') return;
    if (!document.hidden) return; // Only notify when tab is in background

    try {
      const n = new Notification(title, {
        body,
        icon: '/app/favicon.svg',
        tag: 'generation-complete',
      });
      // Auto-focus tab on click
      n.onclick = () => {
        window.focus();
        n.close();
      };
      // Auto-close after 10s
      setTimeout(() => n.close(), 10_000);
    } catch {
      // Notification constructor can throw in some contexts
    }
  }, []);

  return { requestPermission, notify };
}
