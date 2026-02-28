import { Progress } from '@/components/ui/progress';
import { Loader2 } from 'lucide-react';

interface GenerationProgressProps {
  step: number;
  total: number;
  message: string;
}

export default function GenerationProgress({ step, total, message }: GenerationProgressProps) {
  const percent = total > 0 ? Math.round((step / total) * 100) : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {message || 'Generowanie...'}
        </span>
        {total > 0 && (
          <span className="font-mono text-xs">
            {step}/{total} ({percent}%)
          </span>
        )}
      </div>
      <Progress value={percent} aria-label="Postęp generowania" />
    </div>
  );
}
