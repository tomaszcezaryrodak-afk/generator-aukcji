import { useRef, useState, useEffect, useCallback, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { useSSE } from '@/hooks/useSSE';
import { useConfirm } from '@/hooks/useConfirm';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import GenerationProgress from '@/components/generation/GenerationProgress';
import LiveGallery from '@/components/generation/LiveGallery';
import PhaseGate from '@/components/generation/PhaseGate';
import Lightbox from '@/components/shared/Lightbox';
import InlineAlert from '@/components/shared/InlineAlert';
import { api } from '@/lib/api';
import { pluralPL } from '@/lib/utils';
import { Wand2, XCircle, ArrowLeft, Loader2, Image, FileText, CheckCircle, RefreshCw } from 'lucide-react';

const PHASE_LABELS: Record<string, string> = {
  dna: 'Analiza DNA produktu',
  phase1: 'Generowanie packshotów',
  phase1_approval: 'Akceptacja packshotów',
  phase2: 'Generowanie scen lifestyle',
  phase2_approval: 'Akceptacja lifestyle',
  finalizing: 'Finalizacja i opis SEO',
};

export default memo(function Step5Generate() {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const { connect, disconnect, reconnect, isConnected } = useSSE();
  const hasStarted = useRef(false);
  const [isStarting, setIsStarting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const startGeneration = useCallback(async () => {
    if (!sessionId || hasStarted.current) return;
    hasStarted.current = true;
    setIsStarting(true);

    dispatch({ type: 'SET_GENERATING', isGenerating: true });
    dispatch({ type: 'SET_PHASE', phase: 'dna' });

    try {
      const featureMap: Record<string, string> = {};
      state.confirmedFeatures.forEach((f) => {
        featureMap[f.key] = f.value;
      });

      const res = await api.startGeneration({
        session_id: sessionId,
        colors: state.confirmedColors,
        features: featureMap,
      });

      dispatch({ type: 'SET_JOB_ID', jobId: res.job_id });
      await connect(res.job_id);
    } catch (err) {
      hasStarted.current = false;
      setIsStarting(false);
      dispatch({ type: 'SET_ERROR', error: `Błąd generowania: ${(err as Error).message}` });
      dispatch({ type: 'SET_GENERATING', isGenerating: false });
    }
  }, [sessionId, state.confirmedFeatures, state.confirmedColors, dispatch, connect]);

  const doCancel = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.cancelGeneration(sessionId);
    } catch {
      // ignore
    }
    disconnect();
    hasStarted.current = false;
    dispatch({ type: 'SET_GENERATING', isGenerating: false });
    dispatch({ type: 'SET_PHASE', phase: 'idle' });
    toast.info('Generowanie anulowane', { id: 'generation-cancelled' });
  }, [sessionId, disconnect, dispatch]);

  const { isConfirming: confirmCancel, handleClick: handleCancel, handleBlur: handleCancelBlur } = useConfirm(doCancel);

  // Reset local state when generation ends (cancel, error, timeout, SSE disconnect)
  useEffect(() => {
    if (!state.isGenerating && !state.resultImages?.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset on generation end
      setIsStarting(false);
      hasStarted.current = false;
    }
  }, [state.isGenerating, state.resultImages?.length]);

  // Elapsed timer during generation
  useEffect(() => {
    if (!state.isGenerating) return;
    const start = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [state.isGenerating]);

  // (confirm timer managed by useConfirm hook)

  // Enter to start generation (pre-generation screen only)
  // MUST be before conditional returns to comply with Rules of Hooks
  useEffect(() => {
    if (state.isGenerating) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !isStarting && !hasStarted.current) {
        const target = e.target as HTMLElement;
        if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') return;
        e.preventDefault();
        startGeneration();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [state.isGenerating, isStarting, startGeneration]);

  if (state.currentPhase === 'phase1_approval' || state.currentPhase === 'phase2_approval') {
    return <PhaseGate />;
  }

  if (state.isGenerating) {
    return (
      <Card className="animate-fade-in-up animate-border-pulse bg-gradient-to-br from-card to-primary/[0.02]" aria-busy="true">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5 text-primary animate-pulse" />
              {PHASE_LABELS[state.currentPhase] || 'Generowanie grafik'}
            </CardTitle>
            <Button
              variant={confirmCancel ? 'destructive' : 'outline'}
              size="sm"
              className={`gap-1.5 ${confirmCancel ? '' : 'text-destructive hover:bg-destructive hover:text-white'}`}
              onClick={handleCancel}
              onBlur={handleCancelBlur}
              aria-label={confirmCancel ? 'Potwierdź anulowanie generowania' : 'Anuluj generowanie'}
            >
              <XCircle className="h-4 w-4" /> {confirmCancel ? 'Na pewno?' : 'Anuluj'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div aria-live="polite">
            <GenerationProgress {...state.progress} elapsed={elapsed} />
          </div>
          {state.liveImages.length > 0 && (
            <>
              <LiveGallery images={state.liveImages} onImageClick={setLightboxIndex} />
              {lightboxIndex !== null && (
                <Lightbox images={state.liveImages} initialIndex={lightboxIndex} onClose={() => setLightboxIndex(null)} />
              )}
            </>
          )}
          {state.error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 flex items-center justify-between gap-3 animate-fade-in-up" role="alert">
              <p className="text-sm text-destructive">{state.error}</p>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0 gap-1.5 text-xs border-destructive/30 text-destructive hover:bg-destructive hover:text-white"
                onClick={() => {
                  reconnect();
                  toast.info('Ponawiam połączenie...', { id: 'sse-reconnect' });
                }}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Ponów
              </Button>
            </div>
          )}
          <div className="flex items-center justify-between text-xs text-muted-foreground" role="status" aria-live="polite">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <span className="relative flex h-2 w-2" aria-hidden="true">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                  </span>
                  Połączono · odbieranie aktualizacji
                </>
              ) : (
                <>
                  <span className="relative flex h-2 w-2" aria-hidden="true">
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  </span>
                  Łączenie...
                </>
              )}
            </div>
            {state.totalCost > 0 && (
              <span className="font-mono tabular-nums text-muted-foreground/40" aria-label={`Koszt: $${state.totalCost.toFixed(3)}`}>
                ${state.totalCost.toFixed(3)}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  const colorCount = Object.keys(state.confirmedColors).length;
  const featureCount = state.confirmedFeatures.length;

  return (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Wand2 className="h-5 w-5 text-primary" />
          <CardTitle>Generowanie grafik</CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">
          Kliknij, aby rozpocząć generowanie packshotów i aranżacji
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        {state.error && (
          <InlineAlert message={state.error} onDismiss={() => dispatch({ type: 'SET_ERROR', error: null })} />
        )}

        {/* Summary of what will be generated */}
        <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
          <p className="text-sm font-semibold text-foreground">Co zostanie wygenerowane</p>
          <div className="grid gap-2.5 sm:grid-cols-2" role="group" aria-label="Elementy do wygenerowania">
            <div className="flex items-start gap-2.5 text-sm rounded-lg p-2.5 -m-2.5 transition-colors hover:bg-primary/5 animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
              <Image className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Packshoty</p>
                <p className="text-xs text-muted-foreground">Kompozycja zestawu + indywidualne</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5 text-sm rounded-lg p-2.5 -m-2.5 transition-colors hover:bg-primary/5 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
              <Image className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Sceny lifestyle</p>
                <p className="text-xs text-muted-foreground">Kuchnie, blaty drewniane i granitowe</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5 text-sm rounded-lg p-2.5 -m-2.5 transition-colors hover:bg-primary/5 animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
              <FileText className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Opis SEO</p>
                <p className="text-xs text-muted-foreground">Zoptymalizowany pod Allegro</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5 text-sm rounded-lg p-2.5 -m-2.5 transition-colors hover:bg-primary/5 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              <CheckCircle className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">Akceptacja</p>
                <p className="text-xs text-muted-foreground">Każda faza wymaga zatwierdzenia</p>
              </div>
            </div>
          </div>
        </div>

        {/* Input summary */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground" aria-label="Podsumowanie danych wejściowych">
          {state.suggestedCategory && (
            <span className="rounded-md bg-primary/10 px-2.5 py-1 text-primary font-medium animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
              {state.suggestedCategory}
            </span>
          )}
          <span className="rounded-md bg-muted/40 px-2 py-1 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>{state.images.length} {pluralPL(state.images.length, 'zdjęcie', 'zdjęcia', 'zdjęć')}</span>
          <span className="rounded-md bg-muted/40 px-2 py-1 animate-fade-in-up" style={{ animationDelay: '0.15s' }}>{colorCount} {pluralPL(colorCount, 'kolor', 'kolory', 'kolorów')}</span>
          <span className="rounded-md bg-muted/40 px-2 py-1 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>{featureCount} {pluralPL(featureCount, 'cecha', 'cechy', 'cech')}</span>
        </div>

        {/* Source image thumbnails */}
        {state.images.length > 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto overscroll-x-contain pb-1 animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
            {state.images.slice(0, 6).map((img, i) => (
              <img
                key={i}
                src={img.preview}
                alt={img.name}
                className="h-10 w-10 shrink-0 rounded-md object-cover border border-border/50 opacity-70 transition-all duration-200 hover:opacity-100 hover:scale-110 hover:shadow-sm"
                decoding="async"
              />
            ))}
            {state.images.length > 6 && (
              <span className="text-[10px] text-muted-foreground/50 px-1 shrink-0">+{state.images.length - 6}</span>
            )}
          </div>
        )}

        {/* Cost & time estimate */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground/60 rounded-md bg-muted/20 px-3 py-2">
          <span>Szacowany koszt: ~1.80 PLN (~$0.50)</span>
          <span className="h-3 w-px bg-border hidden sm:block" aria-hidden="true" />
          <span>Szacowany czas: ~3-5 min</span>
          <span className="h-3 w-px bg-border hidden sm:block" aria-hidden="true" />
          <span>Wymaga zatwierdzenia 2 faz</span>
        </div>

        <div className="flex gap-3 pt-1">
          <Button
            variant="outline"
            size="lg"
            onClick={() => dispatch({ type: 'SET_STEP', step: 4 })}
            disabled={isStarting}
          >
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Wstecz
          </Button>
          <Button
            size="lg"
            className="flex-1 gap-2 animate-pulse-glow"
            onClick={startGeneration}
            disabled={isStarting}
          >
            {isStarting ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Wand2 className="h-5 w-5" />
            )}
            {isStarting ? 'Uruchamianie...' : 'Rozpocznij generowanie'}
          </Button>
        </div>
        {!isStarting && (
          <p className="text-center text-[10px] text-muted-foreground/40 hidden md:flex md:items-center md:justify-center md:gap-1">
            <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Enter</kbd>
            <span>aby rozpocząć</span>
          </p>
        )}
      </CardContent>
    </Card>
  );
});
