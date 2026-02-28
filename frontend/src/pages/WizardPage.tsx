import { useEffect } from 'react';
import { WizardProvider, useWizard } from '@/context/WizardContext';
import Header from '@/components/layout/Header';
import WizardStepper from '@/components/layout/WizardStepper';
import Step1Upload from '@/components/wizard/Step1Upload';
import Step2Analysis from '@/components/wizard/Step2Analysis';
import Step3Colors from '@/components/wizard/Step3Colors';
import Step4Features from '@/components/wizard/Step4Features';
import Step5Generate from '@/components/wizard/Step5Generate';
import Step6Results from '@/components/wizard/Step6Results';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

function StepContent() {
  const { state } = useWizard();

  switch (state.step) {
    case 1:
      return <Step1Upload />;
    case 2:
      return <Step2Analysis />;
    case 3:
      return <Step3Colors />;
    case 4:
      return <Step4Features />;
    case 5:
      return <Step5Generate />;
    case 6:
      return <Step6Results />;
    default:
      return null;
  }
}

function StepNavigation() {
  const { state, canProceed, goNext, goPrev } = useWizard();

  // Hide navigation during generation (step 5) and results (step 6)
  if (state.step >= 5) return null;

  const proceed = canProceed();
  const hintMap: Record<number, string> = {
    1: 'Dodaj przynajmniej jedno zdjęcie',
    2: 'Poczekaj na zakończenie analizy',
    3: 'Potwierdź kolory produktu',
  };

  return (
    <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-6">
      <Button
        variant="outline"
        onClick={goPrev}
        disabled={state.step === 1}
        className="gap-1"
      >
        <ChevronLeft className="h-4 w-4" />
        Wstecz
      </Button>
      <div className="flex flex-col items-end gap-1">
        <Button
          onClick={goNext}
          disabled={!proceed}
          className="gap-1"
        >
          Dalej
          <ChevronRight className="h-4 w-4" />
        </Button>
        {!proceed && hintMap[state.step] && (
          <p className="text-xs text-muted-foreground">{hintMap[state.step]}</p>
        )}
      </div>
    </div>
  );
}

function WizardLayout() {
  const { state } = useWizard();

  // Beforeunload guard during generation (UX P0)
  useEffect(() => {
    if (!state.isGenerating) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [state.isGenerating]);

  return (
    <div className="min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[200] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Przejdź do treści
      </a>
      <Header />
      <WizardStepper />
      <main id="main-content" className="mx-auto max-w-3xl px-4 pb-8">
        <StepContent />
      </main>
      <StepNavigation />
    </div>
  );
}

export default function WizardPage() {
  return (
    <WizardProvider>
      <WizardLayout />
    </WizardProvider>
  );
}
