import { useEffect, useRef, useCallback, useState } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { api } from '@/lib/api';
import type { GeneratedImage, SelfCheck, GenerationPhase } from '@/lib/types';

function safeParse(raw: string): Record<string, unknown> | null {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function safeHandle(e: MessageEvent, handler: (data: Record<string, unknown>) => void): void {
  const data = safeParse(e.data);
  if (!data) return;
  try {
    handler(data);
  } catch {
    // Silently catch SSE handler errors in production
  }
}

export function useSSE() {
  const { dispatch } = useWizard();
  const esRef = useRef<EventSource | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(3000);
  const reconnectAttempts = useRef(0);
  const unmountedRef = useRef(false);
  const connectRef = useRef<((jobId: string) => Promise<void>) | null>(null);

  const connect = useCallback(async (jobId: string) => {
    if (!jobId || esRef.current) return;
    // Clear any pending reconnect timer
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    jobIdRef.current = jobId;

    let ticket: string;
    try {
      ticket = await api.getSSETicket();
    } catch {
      dispatch({ type: 'SET_ERROR', error: 'Nie udało się nawiązać połączenia SSE' });
      return;
    }

    const es = api.createSSE(jobId, ticket);
    esRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      reconnectDelay.current = 3000;
      reconnectAttempts.current = 0;
      // Clear stale connection error on successful (re)connect
      dispatch({ type: 'SET_ERROR', error: null });
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      esRef.current = null;

      reconnectAttempts.current += 1;
      if (reconnectAttempts.current > 5) {
        dispatch({ type: 'SET_ERROR', error: 'Utracono połączenie z serwerem. Odśwież stronę.' });
        toast.error('Utracono połączenie z serwerem', { id: 'sse-lost' });
        return;
      }

      const delay = reconnectDelay.current;
      reconnectDelay.current = Math.min(delay * 2, 30000);

      reconnectTimer.current = setTimeout(() => {
        if (jobIdRef.current && !unmountedRef.current) {
          connectRef.current?.(jobIdRef.current);
        }
      }, delay);
    };

    es.addEventListener('progress', (e) => safeHandle(e as MessageEvent, (data) => {
      dispatch({
        type: 'SET_PROGRESS',
        progress: {
          step: (data.step as number) || 0,
          total: (data.total as number) || 0,
          message: (data.message as string) || '',
        },
      });
    }));

    es.addEventListener('image', (e) => safeHandle(e as MessageEvent, (data) => {
      const img: GeneratedImage = {
        url: data.url as string,
        key: (data.key as string) || `img_${Date.now()}`,
        type: (data.type as GeneratedImage['type']) || 'lifestyle',
        label: (data.label as string) || '',
      };
      dispatch({ type: 'ADD_LIVE_IMAGE', image: img });
    }));

    es.addEventListener('product_dna', (e) => safeHandle(e as MessageEvent, (data) => {
      dispatch({ type: 'SET_PRODUCT_DNA', dna: (data.dna || data) as Record<string, unknown> });
    }));

    es.addEventListener('extraction', (e) => safeHandle(e as MessageEvent, (data) => {
      if (data.category || data.colors || data.features) {
        dispatch({
          type: 'SET_ANALYSIS',
          data: {
            category: (data.category as string) || '',
            colors: (data.colors as Record<string, string>) || {},
            features: Array.isArray(data.features)
              ? (data.features as Array<{ key: string; value: string }>)
              : Object.entries((data.features || {}) as Record<string, string>).map(([key, value]) => ({
                  key,
                  value,
                })),
          },
        });
      }
    }));

    es.addEventListener('phase1_complete', (e) => safeHandle(e as MessageEvent, (data) => {
      dispatch({ type: 'SET_PHASE', phase: 'phase1_approval' as GenerationPhase });
      dispatch({ type: 'SET_PHASE_IMAGES', images: (data.images as GeneratedImage[]) || [] });
      dispatch({ type: 'SET_PHASE_ROUND', round: (data.round as number) || 1 });
    }));

    es.addEventListener('phase2_complete', (e) => safeHandle(e as MessageEvent, (data) => {
      dispatch({ type: 'SET_PHASE', phase: 'phase2_approval' as GenerationPhase });
      dispatch({ type: 'SET_PHASE_IMAGES', images: (data.images as GeneratedImage[]) || [] });
      dispatch({ type: 'SET_PHASE_ROUND', round: (data.round as number) || 1 });
    }));

    es.addEventListener('selfcheck', (e) => safeHandle(e as MessageEvent, (data) => {
      const check: SelfCheck = {
        score: (data.score as number) || 0,
        model: (data.model as string) || '',
        differences: (data.differences as string[]) || [],
      };
      dispatch({ type: 'ADD_SELFCHECK', check });
    }));

    es.addEventListener('retry', (e) => safeHandle(e as MessageEvent, (data) => {
      const scene = (data.scene as string) || '';
      const attempt = (data.attempt as number) || 0;
      dispatch({
        type: 'SET_PROGRESS',
        progress: { step: 0, total: 0, message: `Ponowna próba${scene ? `: ${scene}` : ''} (${attempt})` },
      });
    }));

    es.addEventListener('soft_warning', (e) => safeHandle(e as MessageEvent, (data) => {
      const msg = (data.message as string) || 'Ostrzeżenie';
      toast.warning(msg, { id: 'sse-warning' });
      dispatch({
        type: 'SET_PROGRESS',
        progress: { step: 0, total: 0, message: msg },
      });
    }));

    es.addEventListener('phase_timeout', () => {
      toast.error('Przekroczono czas oczekiwania na akceptację fazy', { id: 'phase-timeout' });
      dispatch({ type: 'SET_ERROR', error: 'Przekroczono czas oczekiwania na akceptację fazy' });
      dispatch({ type: 'SET_GENERATING', isGenerating: false });
      dispatch({ type: 'SET_PHASE', phase: 'idle' });
      es.close();
      esRef.current = null;
      jobIdRef.current = null;
      setIsConnected(false);
    });

    es.addEventListener('cancelled', () => {
      toast.info('Generowanie anulowane', { id: 'generation-cancelled' });
      dispatch({ type: 'SET_ERROR', error: null });
      dispatch({ type: 'SET_GENERATING', isGenerating: false });
      dispatch({ type: 'SET_PHASE', phase: 'idle' });
      es.close();
      esRef.current = null;
      jobIdRef.current = null;
      setIsConnected(false);
    });

    es.addEventListener('complete', (e) => safeHandle(e as MessageEvent, (data) => {
      const elapsedSec = (data.elapsed_sec as number) || 0;
      const mins = Math.floor(elapsedSec / 60);
      const secs = Math.round(elapsedSec % 60);
      const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
      toast.success(`Generowanie zakończone w ${timeStr}`, { id: 'generation-complete' });
      dispatch({
        type: 'SET_RESULTS',
        images: (data.images as GeneratedImage[]) || [],
        sections: (data.sections as { title: string; description: string; features: Record<string, string>; category: string }) || { title: '', description: '', features: {}, category: '' },
        description: (data.description_html as string) || '',
      });
      if (data.costs) {
        const costs = data.costs as Record<string, unknown>;
        dispatch({
          type: 'SET_COST',
          total: (costs.total as number) || 0,
          perModel: (costs.per_model as Record<string, number>) || {},
        });
      }
      // Banned AI phrases warning
      const bannedPhrases = data.banned_phrases as string[] | undefined;
      if (bannedPhrases && bannedPhrases.length > 0) {
        const preview = bannedPhrases.slice(0, 3).join(', ');
        const suffix = bannedPhrases.length > 3 ? ` (+${bannedPhrases.length - 3})` : '';
        toast.warning(`Opis zawiera frazy AI: ${preview}${suffix}. Sprawdź i popraw w edytorze.`, {
          id: 'banned-phrases',
          duration: 10000,
        });
      }
      dispatch({
        type: 'SET_ELAPSED',
        seconds: elapsedSec,
        timestamp: (data.timestamp as string) || '',
      });
      es.close();
      esRef.current = null;
      jobIdRef.current = null;
      setIsConnected(false);
    }));

    es.addEventListener('error', (e) => {
      if (e instanceof MessageEvent) {
        safeHandle(e, (data) => {
          const msg = (data.message as string) || 'Błąd generowania';
          toast.error(msg, { id: 'sse-error' });
          dispatch({ type: 'SET_ERROR', error: msg });
          dispatch({ type: 'SET_GENERATING', isGenerating: false });
          dispatch({ type: 'SET_PHASE', phase: 'idle' });
          es.close();
          esRef.current = null;
          jobIdRef.current = null;
          setIsConnected(false);
        });
      }
    });

    es.addEventListener('cost_update', (e) => safeHandle(e as MessageEvent, (data) => {
      dispatch({
        type: 'SET_COST',
        total: (data.total as number) || (data.total_usd as number) || 0,
        perModel: (data.per_model as Record<string, number>) || {},
      });
    }));

    es.addEventListener('warning', (e) => safeHandle(e as MessageEvent, (data) => {
      const msg = (data.message as string) || '';
      if (msg) toast.warning(msg, { id: 'sse-warning' });
    }));

    es.addEventListener('background_removed', (e) => safeHandle(e as MessageEvent, (data) => {
      const msg = (data.message as string) || '';
      if (msg) {
        toast.info(msg, { id: 'bg-removed' });
      }
    }));
  }, [dispatch]);

  // Keep ref in sync for reconnect timer callback
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    jobIdRef.current = null;
    setIsConnected(false);
  }, []);

  // Manual reconnect after max retries exhausted
  const reconnect = useCallback(() => {
    const savedJobId = jobIdRef.current;
    if (!savedJobId) return;
    // Reset counters
    reconnectAttempts.current = 0;
    reconnectDelay.current = 3000;
    // Close stale connection
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    dispatch({ type: 'SET_ERROR', error: null });
    connectRef.current?.(savedJobId);
  }, [dispatch]);

  // Reconnect when tab becomes visible and connection is dead
  useEffect(() => {
    const handleVisibility = () => {
      if (
        document.visibilityState === 'visible' &&
        jobIdRef.current &&
        !esRef.current &&
        reconnectAttempts.current < 5
      ) {
        reconnectAttempts.current = 0;
        reconnectDelay.current = 3000;
        connectRef.current?.(jobIdRef.current);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  useEffect(() => {
    return () => {
      unmountedRef.current = true;
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect, reconnect, isConnected };
}
