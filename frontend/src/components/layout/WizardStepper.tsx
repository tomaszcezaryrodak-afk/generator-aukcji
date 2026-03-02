import { memo, useEffect } from 'react';
import { useWizard } from '@/context/WizardContext';
import { cn } from '@/lib/utils';
import { Upload, Search, Palette, SlidersHorizontal, Wand2, CheckCircle } from 'lucide-react';
import type { WizardStep } from '@/lib/types';
import type { LucideIcon } from 'lucide-react';

const steps: { step: WizardStep; label: string; Icon: LucideIcon }[] = [
  { step: 1, label: 'Zdjęcia', Icon: Upload },
  { step: 2, label: 'Analiza', Icon: Search },
  { step: 3, label: 'Kolory', Icon: Palette },
  { step: 4, label: 'Cechy', Icon: SlidersHorizontal },
  { step: 5, label: 'Generuj', Icon: Wand2 },
  { step: 6, label: 'Wyniki', Icon: CheckCircle },
];

export default memo(function WizardStepper() {
  const { state, dispatch } = useWizard();

  // Number key shortcuts (1-6) to jump to completed steps
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const num = parseInt(e.key, 10);
      if (num >= 1 && num <= 6 && num < state.step) {
        e.preventDefault();
        dispatch({ type: 'SET_STEP', step: num as WizardStep });
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [state.step, dispatch]);

  return (
    <nav className="sticky top-14 z-40 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80" aria-label="Kroki wizarda">
      <div className="mx-auto max-w-3xl px-4 py-3">
        <p className="mb-2 text-center text-[11px] font-medium text-muted-foreground tabular-nums sm:hidden">
          Krok {state.step}/6 · {steps.find((s) => s.step === state.step)?.label}
        </p>
        <ol className="flex items-center justify-between gap-1">
          {steps.map(({ step, label, Icon }, i) => {
            const isCurrent = state.step === step;
            const isCompleted = state.step > step;
            const isClickable = isCompleted;

            return (
              <li key={step} className="flex flex-1 items-center">
                <button
                  type="button"
                  className={cn(
                    'group flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium touch-manipulation transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:px-3 sm:py-2',
                    isCurrent && 'bg-primary/10 text-primary',
                    isCompleted && 'text-primary cursor-pointer hover:bg-primary/5',
                    !isCurrent && !isCompleted && 'text-muted-foreground/60',
                  )}
                  onClick={() => isClickable && dispatch({ type: 'SET_STEP', step })}
                  disabled={!isClickable && !isCurrent}
                  aria-current={isCurrent ? 'step' : undefined}
                  aria-label={`${label}${isCompleted ? ' (ukończone)' : isCurrent ? ' (aktualny krok)' : ' (niedostępny)'}`}
                >
                  <span
                    className={cn(
                      'flex h-7 w-7 items-center justify-center rounded-full text-xs transition-all duration-300 sm:h-8 sm:w-8',
                      isCurrent && 'bg-primary text-white shadow-sm ring-2 ring-primary/20 ring-offset-1 animate-pulse-glow',
                      isCompleted && 'bg-primary/15 text-primary',
                      !isCurrent && !isCompleted && 'bg-muted/40 text-muted-foreground/50',
                    )}
                  >
                    {isCompleted ? (
                      <CheckCircle className="h-4 w-4 animate-check-bounce" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </span>
                  <span className="hidden text-xs sm:inline sm:text-sm">{label}</span>
                </button>
                {i < steps.length - 1 && (
                  <div
                    aria-hidden="true"
                    className="mx-0.5 h-[2px] flex-1 rounded-full bg-border sm:mx-1 overflow-hidden"
                  >
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-700 ease-out',
                        isCompleted ? 'w-full bg-primary/50' : 'w-0 bg-primary/40',
                        isCurrent && !isCompleted && 'w-1/2 bg-primary/25',
                      )}
                      style={{ transitionDelay: isCompleted ? `${i * 0.1}s` : '0s' }}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
});
