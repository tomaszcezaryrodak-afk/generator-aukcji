import { memo } from 'react';
import { useWizard } from '@/context/WizardContext';
import { formatPLN, formatUSD, pluralPL } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Receipt } from 'lucide-react';

export default memo(function CostSummary() {
  const { state } = useWizard();
  const entries = Object.entries(state.modelCosts).filter(([, v]) => v > 0);

  if (state.totalCost <= 0 && entries.length === 0) return null;

  return (
    <Card className="animate-fade-in-up border-border/60">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Receipt className="h-4 w-4 text-primary" />
            Koszty generowania
          </CardTitle>
          {entries.length > 0 && (
            <Badge variant="outline" className="text-[10px] font-mono tabular-nums">
              {entries.length} {pluralPL(entries.length, 'model', 'modele', 'modeli')}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.length > 0 && (
          <div className="divide-y divide-border/30" role="table" aria-label="Koszty per model">
            {entries.map(([model, cost], i) => {
              const pct = state.totalCost > 0 ? Math.round((cost / state.totalCost) * 100) : 0;
              return (
                <div key={model} role="row" className={`flex items-center gap-2 text-sm py-2.5 px-2 rounded-md animate-fade-in-up ${i % 2 === 0 ? 'bg-muted/15' : ''}`} style={{ animationDelay: `${i * 0.05}s` }}>
                  <span role="rowheader" className="text-muted-foreground truncate text-xs flex-1 min-w-0">{model}</span>
                  <div className="w-16 h-1.5 rounded-full bg-border/40 overflow-hidden shrink-0 hidden sm:block" aria-hidden="true">
                    <div className="h-full rounded-full bg-primary/40 transition-all duration-500" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-[10px] text-muted-foreground/40 tabular-nums w-8 text-right shrink-0">{pct}%</span>
                  <span role="cell" className="font-mono text-xs tabular-nums shrink-0 text-foreground">
                    {formatPLN(cost)} <span className="text-muted-foreground/50">({formatUSD(cost)})</span>
                  </span>
                </div>
              );
            })}
          </div>
        )}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="font-semibold">Razem</span>
          <div className="flex items-center gap-2 animate-count-up">
            <Badge variant="secondary" className="font-mono tabular-nums text-sm">
              {formatPLN(state.totalCost)}
            </Badge>
            <span className="text-sm text-muted-foreground/60 tabular-nums">
              ({formatUSD(state.totalCost)})
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
});
