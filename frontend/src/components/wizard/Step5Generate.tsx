import { useRef } from 'react';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { useSSE } from '@/hooks/useSSE';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import GenerationProgress from '@/components/generation/GenerationProgress';
import LiveGallery from '@/components/generation/LiveGallery';
import PhaseGate from '@/components/generation/PhaseGate';
import { api } from '@/lib/api';
import { Wand2, XCircle, ArrowLeft } from 'lucide-react';

export default function Step5Generate() {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const { connect, disconnect, isConnected } = useSSE(sessionId);
  const hasStarted = useRef(false);

  const startGeneration = async () => {
    if (!sessionId || hasStarted.current) return;
    hasStarted.current = true;

    dispatch({ type: 'SET_GENERATING', isGenerating: true });
    dispatch({ type: 'SET_PHASE', phase: 'dna' });
    dispatch({ type: 'SET_ERROR', error: null });

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
      connect();
    } catch (err) {
      hasStarted.current = false;
      dispatch({ type: 'SET_ERROR', error: `Błąd generowania: ${(err as Error).message}` });
      dispatch({ type: 'SET_GENERATING', isGenerating: false });
    }
  };

  const handleCancel = async () => {
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
  };

  if (state.currentPhase === 'phase1_approval' || state.currentPhase === 'phase2_approval') {
    return <PhaseGate />;
  }

  if (state.isGenerating) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5 text-primary" />
              Generowanie grafik
            </CardTitle>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              aria-label="Anuluj generowanie"
            >
              <XCircle className="mr-1 h-4 w-4" /> Anuluj
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div aria-live="polite">
            <GenerationProgress {...state.progress} />
          </div>
          {state.liveImages.length > 0 && (
            <LiveGallery images={state.liveImages} />
          )}
          {isConnected && (
            <p className="text-xs text-muted-foreground">
              Połączono · odbieranie aktualizacji
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generowanie grafik</CardTitle>
        <p className="text-sm text-muted-foreground">
          Kliknij, aby rozpocząć generowanie packshotów i aranżacji.
          Szacunkowy koszt: ~0.50 USD (~1.80 PLN) za zestaw
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {state.error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive" role="alert">
            {state.error}
          </div>
        )}
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="lg"
            onClick={() => dispatch({ type: 'SET_STEP', step: 4 })}
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Wstecz
          </Button>
          <Button
            size="lg"
            className="flex-1 gap-2"
            onClick={startGeneration}
          >
            <Wand2 className="h-5 w-5" />
            Rozpocznij generowanie
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
