import { memo } from 'react';
import type { SelfCheck } from '@/lib/types';
import { Badge } from '@/components/ui/badge';

interface SelfCheckBadgeProps {
  check: SelfCheck;
}

export default memo(function SelfCheckBadge({ check }: SelfCheckBadgeProps) {
  const variant = check.score >= 8 ? 'success' : check.score >= 5 ? 'warning' : 'destructive';
  const label = check.score >= 8 ? 'Dobra jakość' : check.score >= 5 ? 'Akceptowalna jakość' : 'Niska jakość';

  return (
    <div className="flex items-center gap-2 animate-fade-in-up" role="status" aria-label={`${label}: ${check.score} na 10`}>
      <Badge variant={variant} title="Wynik kontroli jakości (1-10). 8+ = dobra jakość.">
        Jakość: {check.score}/10
      </Badge>
      {check.differences.length > 0 && (
        <span
          className="text-xs text-muted-foreground max-w-[200px] truncate"
          title={check.differences.join(', ')}
        >
          {check.differences.slice(0, 2).join(', ')}
        </span>
      )}
    </div>
  );
});
