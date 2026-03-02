import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { useConfirm } from '@/hooks/useConfirm';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import LiveGallery from './LiveGallery';
import Lightbox from '@/components/shared/Lightbox';
import InlineAlert from '@/components/shared/InlineAlert';
import { api } from '@/lib/api';
import { pluralPL } from '@/lib/utils';
import { CheckCircle, MessageSquare, XCircle, AlertTriangle } from 'lucide-react';

const MAX_FEEDBACK_LENGTH = 500;
const FEEDBACK_CHIPS_PHASE1 = ['Białe tło', 'Dodaj cień', 'Lepsze kadrowanie', 'Wyższy kontrast'] as const;
const FEEDBACK_CHIPS_PHASE2 = ['Cieplejsze światło', 'Drewniany blat', 'Zmień aranżację', 'Jaśniejsze kolory'] as const;

export default memo(function PhaseGate() {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const phaseNumber = state.currentPhase === 'phase1_approval' ? 1 : 2;
  const phaseLabel = phaseNumber === 1 ? 'Packshoty' : 'Lifestyle';
  const remainingRounds = Math.max(0, 8 - state.phaseRound);

  const handleApprove = useCallback(async () => {
    if (!sessionId) return;
    setIsSubmitting(true);
    try {
      await api.approvePhase(sessionId);
      toast.success(`Faza ${phaseNumber} zaakceptowana`, { id: 'phase-approved' });
      dispatch({
        type: 'SET_PHASE',
        phase: phaseNumber === 1 ? 'phase2' : 'finalizing',
      });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', error: `Błąd akceptacji: ${(err as Error).message}` });
    } finally {
      setIsSubmitting(false);
    }
  }, [sessionId, phaseNumber, dispatch]);

  const handleFeedback = useCallback(async () => {
    if (!sessionId || !feedback.trim()) return;
    setIsSubmitting(true);
    try {
      await api.sendFeedback(sessionId, feedback.trim());
      toast.info('Poprawki wysłane, regenerowanie...', { id: 'phase-feedback' });
      setFeedback('');
      dispatch({
        type: 'SET_PHASE',
        phase: phaseNumber === 1 ? 'phase1' : 'phase2',
      });
      dispatch({ type: 'SET_PHASE_ROUND', round: state.phaseRound + 1 });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', error: `Błąd wysyłania poprawki: ${(err as Error).message}` });
    } finally {
      setIsSubmitting(false);
    }
  }, [sessionId, feedback, phaseNumber, state.phaseRound, dispatch]);

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const approveRef = useRef<HTMLButtonElement>(null);

  // Auto-focus approve button on mount
  useEffect(() => {
    const timer = setTimeout(() => approveRef.current?.focus(), 300);
    return () => clearTimeout(timer);
  }, []);

  // Keyboard shortcuts:
  // Enter (outside textarea): approve
  // Ctrl/Cmd+Enter (in textarea): send feedback
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isSubmitting) return;
      const target = e.target as HTMLElement;
      const inTextarea = target.tagName === 'TEXTAREA';

      if (e.key === 'Escape' && inTextarea && feedback.trim()) {
        e.preventDefault();
        setFeedback('');
        return;
      }

      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && inTextarea && feedback.trim()) {
        e.preventDefault();
        handleFeedback();
        return;
      }

      if (e.key === 'Enter' && !e.shiftKey && !feedback.trim() && !inTextarea && target.tagName !== 'INPUT') {
        e.preventDefault();
        handleApprove();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [feedback, isSubmitting, handleApprove, handleFeedback]);

  const doCancel = useCallback(async () => {
    if (!sessionId) return;
    setIsSubmitting(true);
    try {
      await api.cancelGeneration(sessionId);
      toast.warning('Generowanie anulowane', { id: 'generation-cancelled' });
      dispatch({ type: 'SET_GENERATING', isGenerating: false });
      dispatch({ type: 'SET_PHASE', phase: 'idle' });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', error: `Błąd anulowania: ${(err as Error).message}` });
    } finally {
      setIsSubmitting(false);
    }
  }, [sessionId, dispatch]);

  const { isConfirming: confirmCancel, handleClick: handleCancel, handleBlur: handleCancelBlur } = useConfirm(doCancel);

  return (
    <Card className="animate-fade-in-up border-primary/20 shadow-sm shadow-primary/5">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
              {phaseNumber}
            </span>
            {phaseLabel}
          </CardTitle>
          <Badge
            variant={state.phaseRound >= 6 ? 'destructive' : state.phaseRound >= 4 ? 'warning' : 'outline'}
            className="font-mono"
          >
            Runda {state.phaseRound}/8
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Sprawdź {state.phaseImages.length > 0 ? `${state.phaseImages.length} ${pluralPL(state.phaseImages.length, 'wygenerowaną grafikę', 'wygenerowane grafiki', 'wygenerowanych grafik')}` : 'wygenerowane grafiki'}. Zaakceptuj lub wskaż poprawki
        </p>
        <div className="pt-2 space-y-1.5">
          <Progress value={(state.phaseRound / 8) * 100} className="h-1.5" aria-label={`Runda ${state.phaseRound} z 8`} />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1" aria-hidden="true">
              {Array.from({ length: 8 }).map((_, i) => (
                <span
                  key={i}
                  className={`h-1.5 w-1.5 rounded-full transition-colors duration-300 ${i < state.phaseRound ? 'bg-primary' : 'bg-border'}`}
                />
              ))}
            </div>
            <span className="text-[10px] text-muted-foreground/50 tabular-nums">
              {remainingRounds > 0 ? `${remainingRounds} pozostało` : 'Limit'}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {state.error && (
          <InlineAlert message={state.error} onDismiss={() => dispatch({ type: 'SET_ERROR', error: null })} />
        )}

        <LiveGallery images={state.phaseImages} expectedCount={0} onImageClick={setLightboxIndex} />
        {lightboxIndex !== null && state.phaseImages.length > 0 && (
          <Lightbox images={state.phaseImages} initialIndex={lightboxIndex} onClose={() => setLightboxIndex(null)} />
        )}

        <div className="space-y-3 border-t border-border pt-4">
          {/* Approve button */}
          <Button
            ref={approveRef}
            size="lg"
            className="w-full gap-2 animate-pulse-glow"
            onClick={handleApprove}
            disabled={isSubmitting}
          >
            <CheckCircle className="h-5 w-5" />
            Akceptuj i przejdź dalej
          </Button>
          <p className="text-center text-[10px] text-muted-foreground/40 hidden md:flex md:items-center md:justify-center md:gap-1">
            <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Enter</kbd>
            <span>aby zaakceptować</span>
          </p>

          {/* Revision limit warning */}
          {remainingRounds <= 3 && remainingRounds > 0 && (
            <div className="flex items-center gap-2 rounded-lg bg-primary/5 border border-primary/20 px-3 py-2">
              <AlertTriangle className="h-4 w-4 text-primary shrink-0" />
              <p className="text-xs text-foreground">
                {remainingRounds === 1
                  ? 'Ostatnia runda poprawek'
                  : `${pluralPL(remainingRounds, 'Pozostała', 'Pozostały', 'Pozostało')} ${remainingRounds} ${pluralPL(remainingRounds, 'runda', 'rundy', 'rund')} poprawek`}
              </p>
            </div>
          )}

          {remainingRounds > 0 ? (
            <>
              {!feedback.trim() && (
                <div className="flex flex-wrap gap-1.5" role="group" aria-label="Szybkie sugestie poprawek">
                  {(phaseNumber === 1 ? FEEDBACK_CHIPS_PHASE1 : FEEDBACK_CHIPS_PHASE2).map((chip, i) => (
                    <button
                      key={chip}
                      type="button"
                      className="rounded-md border border-border bg-card px-2 py-1 text-[11px] text-muted-foreground touch-manipulation hover:bg-primary/5 hover:text-foreground hover:border-primary/30 transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:pointer-events-none animate-chip-in"
                      disabled={isSubmitting}
                      onClick={() => { setFeedback(chip); requestAnimationFrame(() => textareaRef.current?.focus()); }}
                      style={{ animationDelay: `${i * 0.05}s` }}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}
              <div className="relative">
                <Textarea
                  ref={textareaRef}
                  placeholder={phaseNumber === 1 ? 'np. zmień tło na białe, dodaj cień, lepsze kadrowanie...' : 'np. cieplejsze oświetlenie, drewniany blat, zmień aranżację...'}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value.slice(0, MAX_FEEDBACK_LENGTH))}
                  rows={3}
                  maxLength={MAX_FEEDBACK_LENGTH}
                  className="resize-none pr-16"
                  aria-label={`Poprawki do fazy ${phaseNumber}`}
                  autoComplete="off"
                />
                <span
                  className="absolute bottom-2 right-3 text-[10px] text-muted-foreground/60 tabular-nums"
                  aria-live="polite"
                >
                  {feedback.trim() ? `${feedback.split(/\s+/).filter(Boolean).length} słów · ` : ''}{feedback.length}/{MAX_FEEDBACK_LENGTH}
                </span>
              </div>
              <div className="flex gap-2">
                <div className="flex-1 space-y-1">
                  <Button
                    variant="outline"
                    className="w-full gap-2"
                    onClick={handleFeedback}
                    disabled={isSubmitting || !feedback.trim()}
                  >
                    <MessageSquare className="h-4 w-4" />
                    Wyślij poprawki
                  </Button>
                  {feedback.trim() && (
                    <p className="text-center text-[10px] text-muted-foreground/40 hidden md:block">
                      <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Ctrl+Enter</kbd> aby wysłać
                    </p>
                  )}
                </div>
                <Button
                  variant={confirmCancel ? 'destructive' : 'ghost'}
                  size="sm"
                  className="min-h-11 gap-1 text-muted-foreground"
                  onClick={handleCancel}
                  onBlur={handleCancelBlur}
                  disabled={isSubmitting}
                  aria-label={confirmCancel ? 'Potwierdź anulowanie generowania' : 'Anuluj generowanie'}
                >
                  <XCircle className="h-4 w-4" />
                  {confirmCancel ? 'Na pewno?' : 'Anuluj'}
                </Button>
              </div>
            </>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-lg bg-destructive/5 border border-destructive/20 px-3 py-2" role="alert">
                <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                <p className="text-xs text-destructive">
                  Wykorzystano limit poprawek. Zaakceptuj wynik lub anuluj generowanie.
                </p>
              </div>
              <Button
                variant={confirmCancel ? 'destructive' : 'ghost'}
                size="sm"
                className="gap-1 text-muted-foreground"
                onClick={handleCancel}
                onBlur={handleCancelBlur}
                disabled={isSubmitting}
                aria-label={confirmCancel ? 'Potwierdź anulowanie generowania' : 'Anuluj generowanie'}
              >
                <XCircle className="h-4 w-4" />
                {confirmCancel ? 'Na pewno?' : 'Anuluj generowanie'}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
