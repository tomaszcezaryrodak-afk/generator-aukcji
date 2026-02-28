import { useState } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import LiveGallery from './LiveGallery';
import { api } from '@/lib/api';
import { CheckCircle, MessageSquare, XCircle } from 'lucide-react';

const MAX_FEEDBACK_LENGTH = 500;

export default function PhaseGate() {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const phaseNumber = state.currentPhase === 'phase1_approval' ? 1 : 2;
  const phaseLabel = phaseNumber === 1 ? 'Packshoty' : 'Lifestyle';

  const handleApprove = async () => {
    if (!sessionId) return;
    setIsSubmitting(true);
    try {
      await api.approvePhase(sessionId);
      toast.success(`Faza ${phaseNumber} zaakceptowana`);
      dispatch({
        type: 'SET_PHASE',
        phase: phaseNumber === 1 ? 'phase2' : 'finalizing',
      });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', error: `Błąd akceptacji: ${(err as Error).message}` });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFeedback = async () => {
    if (!sessionId || !feedback.trim()) return;
    setIsSubmitting(true);
    try {
      await api.sendFeedback(sessionId, feedback.trim());
      toast.info('Poprawki wysłane, regenerowanie...');
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
  };

  const handleCancel = async () => {
    if (!sessionId) return;
    if (!window.confirm('Anulować generowanie? Postęp zostanie utracony.')) return;
    setIsSubmitting(true);
    try {
      await api.cancelGeneration(sessionId);
      toast.warning('Generowanie anulowane');
      dispatch({ type: 'SET_GENERATING', isGenerating: false });
      dispatch({ type: 'SET_PHASE', phase: 'idle' });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', error: `Błąd anulowania: ${(err as Error).message}` });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="border-primary/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            Faza {phaseNumber}: {phaseLabel}
          </CardTitle>
          <Badge variant={state.phaseRound >= 6 ? 'warning' : 'outline'}>
            Runda {state.phaseRound}/8
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Sprawdź wygenerowane grafiki. Zaakceptuj lub wskaż poprawki
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <LiveGallery images={state.phaseImages} expectedCount={0} />

        <div className="space-y-3 border-t border-border pt-4">
          <Button
            size="lg"
            className="w-full gap-2"
            onClick={handleApprove}
            disabled={isSubmitting}
          >
            <CheckCircle className="h-5 w-5" />
            Akceptuj {phaseLabel}
          </Button>

          <div className="relative">
            <Textarea
              placeholder={`Opisz poprawki do ${phaseLabel.toLowerCase()}...`}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value.slice(0, MAX_FEEDBACK_LENGTH))}
              rows={3}
              aria-label={`Poprawki do fazy ${phaseNumber}`}
            />
            <span
              className="absolute bottom-2 right-2 text-xs text-muted-foreground"
              aria-live="polite"
              aria-label={`${feedback.length} z ${MAX_FEEDBACK_LENGTH} znaków`}
            >
              {feedback.length}/{MAX_FEEDBACK_LENGTH}
            </span>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1 gap-2"
              onClick={handleFeedback}
              disabled={isSubmitting || !feedback.trim()}
            >
              <MessageSquare className="h-4 w-4" />
              Popraw
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="min-h-11 gap-1"
              onClick={handleCancel}
              disabled={isSubmitting}
            >
              <XCircle className="h-4 w-4" />
              Anuluj
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
