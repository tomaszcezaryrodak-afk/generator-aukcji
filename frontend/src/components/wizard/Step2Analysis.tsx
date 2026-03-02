import { useEffect, useRef, useState, useMemo, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { pluralPL } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle, AlertCircle, RotateCcw } from 'lucide-react';

export default memo(function Step2Analysis() {
  const { state, dispatch, goNext } = useWizard();
  const { sessionId } = useAuth();
  const hasStarted = useRef(false);
  const hasNotified = useRef(false);
  const [retryCount, setRetryCount] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  // Elapsed timer during analysis
  useEffect(() => {
    if (!state.isAnalyzing) return;
    const start = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [state.isAnalyzing]);

  // Display elapsed only when analyzing (avoids stale value display after completion)
  const displayElapsed = state.isAnalyzing ? elapsed : 0;

  // MUST be before conditional returns (Rules of Hooks)
  const colorEntries = useMemo(
    () => Object.entries(state.suggestedColors).filter(
      ([, color]) => color && color !== 'null' && color.trim() !== '',
    ),
    [state.suggestedColors],
  );

  // Auto-advance to next step after analysis completes (1.5s delay)
  const prevAnalyzing = useRef(state.isAnalyzing);
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (prevAnalyzing.current && !state.isAnalyzing && state.suggestedCategory && !hasNotified.current) {
      hasNotified.current = true;
      toast.success('Analiza zakończona. Przechodz\u0119 dalej...', {
        action: { label: 'Zostań', onClick: () => { if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current); } },
        duration: 3000,
        id: 'analysis-done',
      });
      autoAdvanceTimer.current = setTimeout(() => goNext(), 1500);
    }
    prevAnalyzing.current = state.isAnalyzing;
  }, [state.isAnalyzing, state.suggestedCategory, goNext]);

  // Cleanup auto-advance timer
  useEffect(() => {
    return () => { if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current); };
  }, []);

  useEffect(() => {
    if (hasStarted.current || state.suggestedCategory) return;
    if (state.images.length === 0) return;

    let cancelled = false;
    hasStarted.current = true;
    dispatch({ type: 'SET_ANALYZING', isAnalyzing: true });

    const formData = new FormData();
    formData.append('catalog_key', 'granitowe_zlewy');
    state.images.forEach((img) => {
      formData.append('files', img.file);
    });
    if (state.specText) formData.append('specyfikacja', state.specText);
    if (sessionId) formData.append('session_id', sessionId);

    api
      .uploadAndAnalyze(formData)
      .then((res: Record<string, unknown>) => {
        if (cancelled) return;
        if (res.session_id) {
          dispatch({ type: 'SET_SESSION_ID', sessionId: res.session_id as string });
        }

        // API zwraca { suggestions: { kategoria, kolory, features, ... }, ... }
        const sug = (res.suggestions || res) as Record<string, unknown>;

        const rawColors = (sug.kolory || sug.colors || sug.suggested_colors || {}) as Record<string, string>;
        const rawFeatures = sug.features || {};
        const features = Array.isArray(rawFeatures)
          ? (rawFeatures as Array<{ key: string; value: string }>)
          : Object.entries((rawFeatures || {}) as Record<string, string>).map(([key, value]) => ({
              key,
              value,
            }));

        dispatch({
          type: 'SET_ANALYSIS',
          data: {
            category: ((sug.kategoria || sug.category || sug.suggested_category || '') as string),
            colors: rawColors,
            features,
          },
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        hasStarted.current = false;
        dispatch({ type: 'SET_ERROR', error: `Błąd analizy: ${err.message}` });
        dispatch({ type: 'SET_ANALYZING', isAnalyzing: false });
      });

    return () => { cancelled = true; };
  }, [state.images, state.specText, state.suggestedCategory, sessionId, dispatch, retryCount]);

  if (state.error && !state.isAnalyzing) {
    return (
      <Card className="animate-fade-in-up border-destructive/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Błąd analizy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-destructive" role="alert">{state.error}</p>
          <Button
            onClick={() => {
              dispatch({ type: 'SET_ERROR', error: null });
              hasStarted.current = false;
              setRetryCount((c) => c + 1);
            }}
            className="gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Spróbuj ponownie{retryCount > 0 ? ` (${retryCount + 1})` : ''}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (state.isAnalyzing) {
    return (
      <Card className="animate-fade-in-up">
        <CardHeader>
          <div aria-live="polite" aria-busy={true}>
            <CardTitle className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              Analizuję {state.images.length} {pluralPL(state.images.length, 'zdjęcie', 'zdjęcia', 'zdjęć')}...
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1 flex items-center gap-2">
              <span>AI rozpoznaje kategorię, kolory i parametry techniczne</span>
              <span className="inline-flex items-center gap-0.5">
                <span className="h-1 w-1 rounded-full bg-primary/60 animate-typing-dot" />
                <span className="h-1 w-1 rounded-full bg-primary/60 animate-typing-dot" style={{ animationDelay: '0.15s' }} />
                <span className="h-1 w-1 rounded-full bg-primary/60 animate-typing-dot" style={{ animationDelay: '0.3s' }} />
              </span>
              {displayElapsed > 0 && (
                <span className="font-mono text-[11px] text-muted-foreground/50 tabular-nums ml-auto" role="timer" aria-label="Czas analizy">
                  {displayElapsed}s
                </span>
              )}
            </p>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-3">
            <div>
              <Skeleton className="h-3 w-16 mb-1.5" />
              <Skeleton className="h-6 w-36 rounded-full" />
            </div>
            <div>
              <Skeleton className="h-3 w-28 mb-1.5" />
              <div className="flex gap-2">
                <Skeleton className="h-6 w-24 rounded-full" />
                <Skeleton className="h-6 w-20 rounded-full" />
              </div>
            </div>
            <div>
              <Skeleton className="h-3 w-24 mb-1.5" />
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-40 mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2.5 pt-2">
            {state.images.slice(0, 3).map((img, i) => (
              <div key={i} className="relative aspect-square overflow-hidden rounded-lg border border-border animate-pop-in" style={{ animationDelay: `${i * 0.1}s` }}>
                <img src={img.preview} alt={img.name} className="h-full w-full object-cover opacity-50" decoding="async" loading="lazy" />
                <div className="absolute inset-0 flex items-center justify-center bg-black/10">
                  <div className="h-5 w-5 rounded-full border-2 border-primary/40 border-t-primary animate-spin" />
                </div>
              </div>
            ))}
            {state.images.length > 3 && (
              <div className="flex items-center justify-center text-xs text-muted-foreground/60">
                +{state.images.length - 3} więcej
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="animate-fade-in-up border-green-500/10" role="status" aria-live="polite">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-green-500/10 animate-check-bounce">
            <CheckCircle className="h-4 w-4 text-green-600" />
          </div>
          Analiza zakończona
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg bg-primary/5 px-3 py-2.5 animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Kategoria</p>
          <Badge variant="secondary" className="mt-1.5">
            {state.suggestedCategory || 'Nierozpoznana'}
          </Badge>
        </div>

        {colorEntries.length > 0 && (
          <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Rozpoznane kolory</p>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {colorEntries.map(([key, color]) => (
                <Badge key={key} variant="outline" className="gap-1.5">
                  <span
                    className="h-3 w-3 rounded-full border border-border/50 shadow-inner"
                    style={{ backgroundColor: color }}
                  />
                  {key}: {color}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {state.suggestedFeatures.length > 0 && (
          <div className="animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Rozpoznane cechy</p>
            <div className="mt-1.5 divide-y divide-border/30">
              {state.suggestedFeatures.slice(0, 8).map((f) => (
                <div key={f.key} className="flex items-center justify-between gap-2 text-sm py-1.5 first:pt-0">
                  <span className="font-medium text-muted-foreground truncate">{f.key}</span>
                  <span className="text-right shrink-0">{f.value}</span>
                </div>
              ))}
              {state.suggestedFeatures.length > 8 && (
                <p className="text-xs text-muted-foreground pt-1">
                  +{state.suggestedFeatures.length - 8} więcej (widoczne w kroku Cechy)
                </p>
              )}
            </div>
          </div>
        )}

        {state.images.length > 0 && (
          <div className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Przeanalizowane zdjęcia</p>
            <div className="flex gap-1.5 overflow-x-auto overscroll-x-contain pb-1">
              {state.images.map((img, i) => (
                <img
                  key={i}
                  src={img.preview}
                  alt={img.name}
                  className="h-12 w-12 shrink-0 rounded-md object-cover border border-border/50 opacity-80 transition-all duration-200 hover:opacity-100 hover:scale-110 hover:shadow-sm"
                  decoding="async"
                />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
});
