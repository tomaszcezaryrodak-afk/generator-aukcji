import { useWizard } from '@/context/WizardContext';
import { cn } from '@/lib/utils';
import { Upload, Search, Palette, SlidersHorizontal, Wand2, CheckCircle } from 'lucide-react';
import type { WizardStep } from '@/lib/types';

const steps: { step: WizardStep; label: string; icon: React.ReactNode }[] = [
  { step: 1, label: 'Zdjęcia', icon: <Upload className="h-4 w-4" /> },
  { step: 2, label: 'Analiza', icon: <Search className="h-4 w-4" /> },
  { step: 3, label: 'Kolory', icon: <Palette className="h-4 w-4" /> },
  { step: 4, label: 'Cechy', icon: <SlidersHorizontal className="h-4 w-4" /> },
  { step: 5, label: 'Generuj', icon: <Wand2 className="h-4 w-4" /> },
  { step: 6, label: 'Wyniki', icon: <CheckCircle className="h-4 w-4" /> },
];

export default function WizardStepper() {
  const { state, dispatch } = useWizard();

  return (
    <nav className="mx-auto max-w-3xl px-4 py-4" aria-label="Kroki wizarda">
      <ol className="flex items-center justify-between">
        {steps.map(({ step, label, icon }, i) => {
          const isCurrent = state.step === step;
          const isCompleted = state.step > step;
          const isClickable = isCompleted;

          return (
            <li key={step} className="flex items-center">
              <button
                type="button"
                className={cn(
                  'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  isCurrent && 'bg-primary/10 text-primary',
                  isCompleted && 'text-primary cursor-pointer hover:bg-primary/5',
                  !isCurrent && !isCompleted && 'text-muted-foreground',
                )}
                onClick={() => isClickable && dispatch({ type: 'SET_STEP', step })}
                disabled={!isClickable && !isCurrent}
                aria-current={isCurrent ? 'step' : undefined}
              >
                <span
                  className={cn(
                    'flex h-7 w-7 items-center justify-center rounded-full text-xs',
                    isCurrent && 'bg-primary text-white',
                    isCompleted && 'bg-primary/20 text-primary',
                    !isCurrent && !isCompleted && 'bg-muted/20 text-muted-foreground',
                  )}
                >
                  {isCompleted ? <CheckCircle className="h-3.5 w-3.5" /> : icon}
                </span>
                <span className="hidden sm:inline">{label}</span>
              </button>
              {i < steps.length - 1 && (
                <div
                  aria-hidden="true"
                  className={cn(
                    'mx-1 h-px w-6 sm:w-10',
                    isCompleted ? 'bg-primary' : 'bg-border',
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
