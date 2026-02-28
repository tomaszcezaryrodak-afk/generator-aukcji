import type { SelfCheck } from '@/lib/types';
import { Badge } from '@/components/ui/badge';

interface SelfCheckBadgeProps {
  check: SelfCheck;
}

export default function SelfCheckBadge({ check }: SelfCheckBadgeProps) {
  const variant = check.score >= 8 ? 'success' : check.score >= 5 ? 'warning' : 'destructive';

  return (
    <div className="flex items-center gap-2">
      <Badge variant={variant} title="Wynik kontroli jakości (1-10). 8+ = dobra jakość.">
        Score: {check.score}/10
      </Badge>
      {check.differences.length > 0 && (
        <span className="text-xs text-muted-foreground">
          {check.differences.slice(0, 2).join(', ')}
        </span>
      )}
    </div>
  );
}
