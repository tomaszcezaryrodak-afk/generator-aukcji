import { useEffect, useRef, lazy, Suspense, useState } from 'react';
import { toast } from 'sonner';
import { WizardProvider, useWizard } from '@/context/WizardContext';
import Header from '@/components/layout/Header';
import WizardStepper from '@/components/layout/WizardStepper';
import ErrorBoundary from '@/components/shared/ErrorBoundary';
import Step1Upload from '@/components/wizard/Step1Upload';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { isMac } from '@/lib/utils';
import { useFaviconProgress } from '@/hooks/useFaviconProgress';
import { useNotification } from '@/hooks/useNotification';
import { fireConfetti } from '@/lib/confetti';
import { ChevronLeft, ChevronRight, ArrowUp, WifiOff } from 'lucide-react';

const STEP_NAMES = ['', 'Zdjęcia', 'Analiza', 'Kolory', 'Cechy', 'Generowanie', 'Wyniki'] as const;

const PROCEED_HINTS: Record<number, string> = {
  1: 'Dodaj zdjęcia i wklej specyfikację',
  2: 'Poczekaj na zakończenie analizy',
  3: 'Potwierdź kolory produktu',
  4: 'Dodaj przynajmniej jedną cechę',
};

const PHASE_SHORT: Record<string, string> = {
  dna: 'Analiza DNA',
  phase1: 'Packshoty',
  phase1_approval: 'Akceptacja',
  phase2: 'Lifestyle',
  phase2_approval: 'Akceptacja',
  finalizing: 'Finalizacja',
};

const Step2Analysis = lazy(() => import('@/components/wizard/Step2Analysis'));
const Step3Colors = lazy(() => import('@/components/wizard/Step3Colors'));
const Step4Features = lazy(() => import('@/components/wizard/Step4Features'));
const Step5Generate = lazy(() => import('@/components/wizard/Step5Generate'));
const Step6Results = lazy(() => import('@/components/wizard/Step6Results'));
const KeyboardHelp = lazy(() => import('@/components/shared/KeyboardHelp'));

function StepFallback() {
  return (
    <div className="rounded-xl border border-border bg-card shadow-sm animate-fade-in-up">
      <div className="p-6 pb-3 space-y-2">
        <Skeleton className="h-6 w-44 rounded-md" />
        <Skeleton className="h-4 w-64 rounded-md" />
      </div>
      <div className="p-6 pt-3 space-y-4">
        <Skeleton className="h-28 w-full rounded-lg" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-24 rounded-full" />
          <Skeleton className="h-8 w-20 rounded-full" />
          <Skeleton className="h-8 w-28 rounded-full" />
        </div>
      </div>
    </div>
  );
}

function StepContent() {
  const { state } = useWizard();
  const prevStep = useRef(state.step);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prevStep.current !== state.step) {
      prevStep.current = state.step;
      // Scroll to top on step change
      window.scrollTo({ top: 0, behavior: 'smooth' });
      // Focus the step container for screen readers
      requestAnimationFrame(() => {
        containerRef.current?.focus();
      });
    }
  }, [state.step]);

  // Prefetch next step's chunk on idle
  useEffect(() => {
    const prefetchMap: Record<number, () => void> = {
      1: () => { import('@/components/wizard/Step2Analysis'); },
      2: () => { import('@/components/wizard/Step3Colors'); },
      3: () => { import('@/components/wizard/Step4Features'); },
      4: () => { import('@/components/wizard/Step5Generate'); },
      5: () => { import('@/components/wizard/Step6Results'); },
    };
    const prefetch = prefetchMap[state.step];
    if (!prefetch) return;
    if ('requestIdleCallback' in window) {
      const id = requestIdleCallback(prefetch);
      return () => cancelIdleCallback(id);
    } else {
      const timer = setTimeout(prefetch, 200);
      return () => clearTimeout(timer);
    }
  }, [state.step]);

  const renderStep = () => {
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
  };

  return (
    <div ref={containerRef} key={state.step} className="animate-step-enter outline-none" tabIndex={-1}>
      <div className="sr-only" role="status" aria-live="polite">
        Krok {state.step} z 6: {STEP_NAMES[state.step]}
      </div>
      <ErrorBoundary>
        <Suspense fallback={<StepFallback />}>
          {renderStep()}
        </Suspense>
      </ErrorBoundary>
    </div>
  );
}

function StepNavigation() {
  const { state, canProceed, goNext, goPrev } = useWizard();

  // Ctrl+Enter (or Cmd+Enter on Mac) to proceed to next step
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (state.step >= 5) return;
      const target = e.target as HTMLElement;
      if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') return;
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && canProceed()) {
        e.preventDefault();
        goNext();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [state.step, canProceed, goNext]);

  // Hide navigation during generation (step 5) and results (step 6)
  if (state.step >= 5) return null;

  const proceed = canProceed();

  return (
    <nav className="animate-fade-in-up sticky bottom-0 z-30 border-t border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80 pb-safe" aria-label="Nawigacja kroków">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
        <Button
          variant="outline"
          onClick={goPrev}
          disabled={state.step === 1}
          className="gap-1.5 transition-all duration-200"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="hidden sm:inline">Wstecz</span>
        </Button>
        <span className="text-xs font-medium text-muted-foreground tabular-nums sm:hidden">
          {state.step} / 6
        </span>
        <div className="flex flex-col items-end gap-1">
          <Button
            onClick={goNext}
            disabled={!proceed}
            className={`gap-1.5 transition-all duration-200 ${proceed ? 'animate-pulse-glow' : ''}`}
          >
            Dalej
            <ChevronRight className="h-4 w-4" />
          </Button>
          {!proceed && PROCEED_HINTS[state.step] && (
            <p className="text-[11px] text-muted-foreground animate-fade-in-up max-w-[200px] text-right">
              {PROCEED_HINTS[state.step]}
            </p>
          )}
          {proceed && (
            <p className="text-[10px] text-muted-foreground/40 hidden md:flex md:items-center md:gap-0.5">
              <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">{isMac ? '⌘' : 'Ctrl'}</kbd>
              <span>+</span>
              <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Enter</kbd>
            </p>
          )}
        </div>
      </div>
    </nav>
  );
}

function ScrollToTop() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const handleScroll = () => setShow(window.scrollY > 400);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  if (!show) return null;

  return (
    <Button
      variant="outline"
      size="icon"
      className="fixed bottom-20 right-4 z-40 h-9 w-9 rounded-full shadow-md bg-card/95 backdrop-blur animate-fade-in-up"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="Przewiń na górę"
    >
      <ArrowUp className="h-4 w-4" />
    </Button>
  );
}

function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(() => !navigator.onLine);

  useEffect(() => {
    const goOffline = () => setIsOffline(true);
    const goOnline = () => {
      setIsOffline(false);
      toast.success('Połączenie przywrócone', { id: 'online-status' });
    };
    window.addEventListener('offline', goOffline);
    window.addEventListener('online', goOnline);
    return () => {
      window.removeEventListener('offline', goOffline);
      window.removeEventListener('online', goOnline);
    };
  }, []);

  if (!isOffline) return null;
  return (
    <div className="bg-destructive text-white text-center text-sm py-2 px-4 animate-slide-down flex items-center justify-center gap-2" role="alert">
      <WifiOff className="h-4 w-4 shrink-0" />
      Brak połączenia z internetem. Sprawdź połączenie sieciowe.
    </div>
  );
}

function WizardLayout() {
  const { state } = useWizard();
  const completionNotified = useRef(false);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // Favicon progress donut during generation
  useFaviconProgress(state.isGenerating, state.progress.step, state.progress.total);

  // Browser notifications for background completion
  const { requestPermission, notify } = useNotification();

  // Request notification permission when entering generation step
  useEffect(() => {
    if (state.step === 5) requestPermission();
  }, [state.step, requestPermission]);

  // Notify when phase approval is needed while tab is in background
  const prevPhase = useRef(state.currentPhase);
  useEffect(() => {
    const prev = prevPhase.current;
    prevPhase.current = state.currentPhase;
    if (prev === state.currentPhase) return;
    if (state.currentPhase === 'phase1_approval') {
      notify('Packshoty gotowe', 'Sprawdź wyniki i zaakceptuj lub wskaż poprawki');
    } else if (state.currentPhase === 'phase2_approval') {
      notify('Sceny lifestyle gotowe', 'Sprawdź wyniki i zaakceptuj lub wskaż poprawki');
    }
  }, [state.currentPhase, notify]);

  // ? key toggles keyboard shortcuts overlay
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.isContentEditable) return;
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        setShowKeyboardHelp((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  // Dynamic page title per step (with percentage + phase during generation)
  const genPercent = state.progress.total > 0
    ? Math.round((state.progress.step / state.progress.total) * 100)
    : -1;

  useEffect(() => {
    const phaseName = PHASE_SHORT[state.currentPhase] || '';
    const genTitle = state.isGenerating
      ? genPercent >= 0
        ? `${genPercent}% ${phaseName || 'Generowanie'}`
        : phaseName || 'Generowanie...'
      : 'Generuj';
    const titles: Record<number, string> = {
      1: 'Zdjęcia',
      2: 'Analiza AI',
      3: 'Kolory',
      4: 'Cechy',
      5: genTitle,
      6: 'Wyniki',
    };
    document.title = `${state.step}. ${titles[state.step] || 'Generator'} · Generator Aukcji`;
  }, [state.step, state.isGenerating, state.resultImages.length, genPercent, state.currentPhase]);

  // Celebration + flash title when generation completes
  useEffect(() => {
    if (state.step === 6 && state.resultImages.length > 0 && !completionNotified.current) {
      completionNotified.current = true;
      // Fire confetti celebration (respects prefers-reduced-motion)
      fireConfetti();
      // Browser notification when tab is in background
      notify('Generowanie zakończone', `${state.resultImages.length} grafik gotowych do pobrania`);
      if (!document.hidden) return;
      let flash = true;
      const interval = setInterval(() => {
        document.title = flash ? 'Gotowe · Generator Aukcji' : '6. Wyniki · Generator Aukcji';
        flash = !flash;
      }, 1000);
      const stop = () => {
        if (!document.hidden) {
          clearInterval(interval);
          document.title = '6. Wyniki · Generator Aukcji';
          document.removeEventListener('visibilitychange', stop);
        }
      };
      document.addEventListener('visibilitychange', stop);
      return () => {
        clearInterval(interval);
        document.removeEventListener('visibilitychange', stop);
      };
    }
    if (state.step !== 6) completionNotified.current = false;
  }, [state.step, state.resultImages.length, notify]);

  // Session timeout warning (backend TTL = 24h, warn at 23h)
  useEffect(() => {
    const SESSION_KEY = 'session_start';
    const WARN_AT = 23 * 3600 * 1000; // 23h in ms
    const TTL = 24 * 3600 * 1000; // 24h in ms
    const CHECK_INTERVAL = 5 * 60 * 1000; // every 5 min

    if (!sessionStorage.getItem(SESSION_KEY)) {
      // Fallback: if login didn't set it (e.g. restored session), set now
      sessionStorage.setItem(SESSION_KEY, String(Date.now()));
    }
    const start = Number(sessionStorage.getItem(SESSION_KEY));

    const check = () => {
      const elapsed = Date.now() - start;
      if (elapsed >= TTL) {
        toast.error('Sesja wygasła. Zaloguj się ponownie.', { id: 'session-timeout', duration: Infinity });
      } else if (elapsed >= WARN_AT) {
        const remaining = Math.round((TTL - elapsed) / 60_000);
        toast.warning(`Sesja wygasa za ${remaining} min. Zapisz postęp.`, { id: 'session-timeout-warn', duration: 30_000 });
      }
    };
    check();
    const timer = setInterval(check, CHECK_INTERVAL);
    return () => clearInterval(timer);
  }, []);

  // Beforeunload guard during generation, phase gates, or when images are uploaded
  const hasUnsavedWork = state.isGenerating || state.images.length > 0 || (state.currentPhase !== 'idle' && state.currentPhase !== 'done');
  useEffect(() => {
    if (!hasUnsavedWork) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [hasUnsavedWork]);

  return (
    <div className="min-h-dvh bg-background">
      <OfflineBanner />
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[200] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Przejdź do treści
      </a>
      <Header />
      <WizardStepper />
      <main id="main-content" className="mx-auto max-w-3xl px-4 pb-24 pt-4">
        <StepContent />
      </main>
      <StepNavigation />
      <ScrollToTop />
      {showKeyboardHelp && (
        <Suspense fallback={null}>
          <KeyboardHelp onClose={() => setShowKeyboardHelp(false)} />
        </Suspense>
      )}
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
