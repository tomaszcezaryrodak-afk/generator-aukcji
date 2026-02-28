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
  } catch (err) {
    console.error('[SSE] Event handler error:', err);
  }
}

export function useSSE() {
  const { dispatch } = useWizard();
  const esRef = useRef<EventSource | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const connect = useCallback(async (jobId: string) => {
    if (!jobId || esRef.current) return;
    jobIdRef.current = jobId;

    let ticket: string;
    try {
      ticket = await api.getSSETicket();
    } catch {
      dispatch({ type: 'SET_ERROR', error: 'Nie udało się uzyskać ticketu SSE' });
      return;
    }

    const es = api.createSSE(jobId, ticket);
    esRef.current = es;

    es.onopen = () => setIsConnected(true);

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      esRef.current = null;

      reconnectTimer.current = setTimeout(() => {
        if (jobIdRef.current && !unmountedRef.current) {
          connect(jobIdRef.current);
        }
      }, 3000);
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
      dispatch({
        type: 'SET_PROGRESS',
        progress: { step: 0, total: 0, message: `Ponowna próba: ${(data.reason as string) || ''}` },
      });
    }));

    es.addEventListener('soft_warning', (e) => safeHandle(e as MessageEvent, (data) => {
      const msg = (data.message as string) || 'Ostrzeżenie';
      toast.warning(msg);
      dispatch({
        type: 'SET_PROGRESS',
        progress: { step: 0, total: 0, message: msg },
      });
    }));

    es.addEventListener('phase_timeout', () => {
      toast.error('Przekroczono czas oczekiwania na akceptację fazy');
      dispatch({ type: 'SET_ERROR', error: 'Przekroczono czas oczekiwania na akceptację fazy' });
    });

    es.addEventListener('complete', (e) => safeHandle(e as MessageEvent, (data) => {
      toast.success('Generowanie zakończone');
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
      es.close();
      esRef.current = null;
      jobIdRef.current = null;
      setIsConnected(false);
    }));

    es.addEventListener('error', (e) => {
      if (e instanceof MessageEvent) {
        safeHandle(e, (data) => {
          const msg = (data.message as string) || 'Błąd generowania';
          toast.error(msg);
          dispatch({ type: 'SET_ERROR', error: msg });
        });
      }
    });

    es.addEventListener('cost_update', (e) => safeHandle(e as MessageEvent, (data) => {
      dispatch({
        type: 'SET_COST',
        total: (data.total as number) || 0,
        perModel: (data.per_model as Record<string, number>) || {},
      });
    }));
  }, [dispatch]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current !== null) clearTimeout(reconnectTimer.current);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    jobIdRef.current = null;
    setIsConnected(false);
  }, []);

  useEffect(() => {
    return () => {
      unmountedRef.current = true;
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect, isConnected };
}
