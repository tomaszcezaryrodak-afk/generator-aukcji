import { useWizard } from '@/context/WizardContext';
import { formatPLN } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DollarSign } from 'lucide-react';

function formatUSD(val: number) {
  return `$${val.toFixed(3)}`;
}

export default function CostSummary() {
  const { state } = useWizard();
  const entries = Object.entries(state.modelCosts).filter(([, v]) => v > 0);

  if (state.totalCost <= 0 && entries.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <DollarSign className="h-4 w-4 text-primary" />
          Koszty generowania
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.length > 0 && (
          <div className="space-y-1.5">
            {entries.map(([model, cost]) => (
              <div key={model} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{model}</span>
                <span className="font-mono">{formatUSD(cost)}</span>
              </div>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="font-medium">Razem</span>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="font-mono">
              {formatUSD(state.totalCost)}
            </Badge>
            <span className="text-sm text-muted-foreground">
              ({formatPLN(state.totalCost)})
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
