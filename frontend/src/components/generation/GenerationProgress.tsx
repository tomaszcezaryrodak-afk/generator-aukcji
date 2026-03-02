import { memo } from 'react';
import { Progress } from '@/components/ui/progress';
import { Loader2 } from 'lucide-react';

interface GenerationProgressProps {
  step: number;
  total: number;
  message: string;
  elapsed?: number;
}

export default memo(function GenerationProgress({ step, total, message, elapsed = 0 }: GenerationProgressProps) {
  const percent = total > 0 ? Math.round((step / total) * 100) : 0;

  const min = Math.floor(elapsed / 60);
  const sec = elapsed % 60;
  const elapsedStr = min > 0 ? `${min}:${String(sec).padStart(2, '0')}` : `${sec}s`;

  // ETA calculation
  let etaStr = '';
  if (step > 0 && total > 0 && step < total && elapsed > 5) {
    const rate = elapsed / step;
    const remaining = Math.ceil(rate * (total - step));
    const etaMin = Math.floor(remaining / 60);
    const etaSec = remaining % 60;
    etaStr = etaMin > 0 ? `~${etaMin}:${String(etaSec).padStart(2, '0')}` : `~${etaSec}s`;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 text-foreground font-medium">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          {message || 'Generowanie...'}
        </span>
        <div className="flex items-center gap-2.5">
          {total > 0 && (
            <span className="font-mono text-xs text-muted-foreground tabular-nums">
              {step}/{total} ({percent}%){total - step > 0 ? ` · ${total - step} poz.` : ''}
            </span>
          )}
          <span className="font-mono text-[11px] text-muted-foreground/60 tabular-nums" role="timer" aria-label="Czas od rozpoczęcia">
            {elapsedStr}
          </span>
          {etaStr && (
            <span className="font-mono text-[10px] text-muted-foreground/40 tabular-nums" title="Szacowany czas do zakończenia" aria-label={`Szacowany czas: ${etaStr}`}>
              {etaStr}
            </span>
          )}
        </div>
      </div>
      <div className="relative overflow-hidden rounded-full">
        {total > 0 ? (
          <>
            <Progress value={percent} aria-label="Postęp generowania" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-2.5" />
            {percent > 0 && percent < 100 && (
              <div
                className="absolute inset-y-0 left-0 rounded-full animate-shimmer pointer-events-none"
                style={{ width: `${percent}%` }}
              />
            )}
          </>
        ) : (
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-secondary" role="progressbar" aria-label="Trwa generowanie" aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full w-1/3 rounded-full bg-primary/60 animate-indeterminate" />
          </div>
        )}
      </div>
    </div>
  );
});
