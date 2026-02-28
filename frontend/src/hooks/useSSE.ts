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

export function useSSE(sessionId: string | null) {
  const { dispatch } = useWizard();
  const esRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!sessionId || esRef.current) return;

    const es = api.createSSE(sessionId);
    esRef.current = es;

    es.onopen = () => setIsConnected(true);

    es.onerror = () => {
      setIsConnected(false);
      es.close();
      esRef.current = null;

      reconnectTimer.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    es.addEventListener('progress', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      dispatch({
        type: 'SET_PROGRESS',
        progress: {
          step: (data.step as number) || 0,
          total: (data.total as number) || 0,
          message: (data.message as string) || '',
        },
      });
    });

    es.addEventListener('image', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      const img: GeneratedImage = {
        url: data.url as string,
        key: (data.key as string) || `img_${Date.now()}`,
        type: (data.type as GeneratedImage['type']) || 'lifestyle',
        label: (data.label as string) || '',
      };
      dispatch({ type: 'ADD_LIVE_IMAGE', image: img });
    });

    es.addEventListener('product_dna', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      dispatch({ type: 'SET_PRODUCT_DNA', dna: (data.dna || data) as Record<string, unknown> });
    });

    es.addEventListener('extraction', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
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
    });

    es.addEventListener('phase1_complete', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      dispatch({ type: 'SET_PHASE', phase: 'phase1_approval' as GenerationPhase });
      dispatch({ type: 'SET_PHASE_IMAGES', images: (data.images as GeneratedImage[]) || [] });
      dispatch({ type: 'SET_PHASE_ROUND', round: (data.round as number) || 1 });
    });

    es.addEventListener('phase2_complete', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      dispatch({ type: 'SET_PHASE', phase: 'phase2_approval' as GenerationPhase });
      dispatch({ type: 'SET_PHASE_IMAGES', images: (data.images as GeneratedImage[]) || [] });
      dispatch({ type: 'SET_PHASE_ROUND', round: (data.round as number) || 1 });
    });

    es.addEventListener('selfcheck', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      const check: SelfCheck = {
        score: (data.score as number) || 0,
        model: (data.model as string) || '',
        differences: (data.differences as string[]) || [],
      };
      dispatch({ type: 'ADD_SELFCHECK', check });
    });

    es.addEventListener('retry', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      dispatch({
        type: 'SET_PROGRESS',
        progress: { step: 0, total: 0, message: `Ponowna próba: ${(data.reason as string) || ''}` },
      });
    });

    es.addEventListener('soft_warning', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      const msg = (data.message as string) || 'Ostrzeżenie';
      toast.warning(msg);
      dispatch({
        type: 'SET_PROGRESS',
        progress: { step: 0, total: 0, message: msg },
      });
    });

    es.addEventListener('phase_timeout', () => {
      toast.error('Przekroczono czas oczekiwania na akceptację fazy');
      dispatch({ type: 'SET_ERROR', error: 'Przekroczono czas oczekiwania na akceptację fazy' });
    });

    es.addEventListener('complete', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
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
      setIsConnected(false);
    });

    es.addEventListener('error', (e) => {
      if (e instanceof MessageEvent) {
        const data = safeParse(e.data);
        if (!data) return;
        const msg = (data.message as string) || 'Błąd generowania';
        toast.error(msg);
        dispatch({ type: 'SET_ERROR', error: msg });
      }
    });

    es.addEventListener('cost_update', (e) => {
      const data = safeParse(e.data);
      if (!data) return;
      dispatch({
        type: 'SET_COST',
        total: (data.total as number) || 0,
        perModel: (data.per_model as Record<string, number>) || {},
      });
    });
  }, [sessionId, dispatch]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current !== null) clearTimeout(reconnectTimer.current);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect, isConnected };
}
