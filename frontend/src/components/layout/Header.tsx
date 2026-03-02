import { useCallback, memo } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { useWizard } from '@/context/WizardContext';
import { formatPLN } from '@/lib/utils';
import { useConfirm } from '@/hooks/useConfirm';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import ProviderStatus from '@/components/generation/ProviderStatus';
import { LogOut, Upload, Search, Palette, SlidersHorizontal, Wand2, CheckCircle } from 'lucide-react';

const STEP_ICONS: Record<number, typeof Upload> = { 1: Upload, 2: Search, 3: Palette, 4: SlidersHorizontal, 5: Wand2, 6: CheckCircle };
const STEP_NAMES: Record<number, string> = { 1: 'Zdjęcia', 2: 'Analiza', 3: 'Kolory', 4: 'Cechy', 5: 'Generuj', 6: 'Wyniki' };

export default memo(function Header() {
  const { logout } = useAuth();
  const { state } = useWizard();
  const StepIcon = STEP_ICONS[state.step];
  const stepName = STEP_NAMES[state.step];

  const doLogout = useCallback(() => {
    logout();
    toast.info('Wylogowano', { id: 'logout' });
  }, [logout]);

  const { isConfirming: confirmLogout, handleClick: handleLogout, handleBlur: handleLogoutBlur } = useConfirm(doLogout);

  // Require 2-click confirm when there's active work (not just during generation)
  const hasActiveWork = state.isGenerating || state.images.length > 0 || (state.currentPhase !== 'idle' && state.currentPhase !== 'done');

  return (
    <header role="banner" className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80" style={{ borderImage: 'linear-gradient(to right, transparent, oklch(0.48 0.09 55 / 0.15), transparent) 1' }}>
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 transition-transform hover:scale-105" aria-hidden="true">
            <span className="text-sm font-bold tracking-tight text-primary select-none">GZ</span>
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <h1 className="text-sm font-semibold tracking-wide sm:text-base">Generator Aukcji</h1>
              <span className="text-[9px] font-mono text-muted-foreground/40 bg-muted/30 px-1 py-0.5 rounded">v4.3.3</span>
            </div>
            <span className="text-[10px] text-muted-foreground leading-none hidden sm:block">Granitowe Zlewy</span>
          </div>
          {state.totalCost > 0 && (
            <Badge
              variant="secondary"
              className="ml-1 font-mono text-xs hidden sm:inline-flex cursor-help animate-count-up"
              aria-label={`Koszt generowania: ${formatPLN(state.totalCost)}`}
              aria-live="polite"
              title={
                Object.keys(state.modelCosts).length > 0
                  ? Object.entries(state.modelCosts)
                      .filter(([, v]) => v > 0)
                      .map(([m, v]) => `${m}: ${formatPLN(v)}`)
                      .join('\n')
                  : undefined
              }
            >
              {formatPLN(state.totalCost)}
            </Badge>
          )}
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground/60 sm:hidden tabular-nums">
            {StepIcon && <StepIcon className="h-3 w-3" />}
            {stepName || state.step}/{6}
          </span>
          <div className="hidden md:block">
            <ProviderStatus />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <kbd className="hidden lg:inline-flex h-6 items-center rounded border border-border bg-muted/30 px-1.5 font-mono text-[10px] text-muted-foreground/40 cursor-help select-none" title="Pokaż skróty klawiszowe" aria-hidden="true">?</kbd>
        <Button
          variant={confirmLogout ? 'destructive' : 'ghost'}
          size="sm"
          className={`gap-1.5 ${confirmLogout ? '' : 'text-muted-foreground hover:text-foreground'}`}
          onClick={hasActiveWork ? handleLogout : doLogout}
          onBlur={handleLogoutBlur}
          aria-label={confirmLogout ? 'Potwierdź wylogowanie' : 'Wyloguj'}
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline text-xs">{confirmLogout ? 'Na pewno?' : 'Wyloguj'}</span>
        </Button>
        </div>
      </div>
    </header>
  );
});
