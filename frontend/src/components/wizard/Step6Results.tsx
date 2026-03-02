import { useEffect, useRef, useState, useCallback, useMemo, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { api } from '@/lib/api';
import { copyToClipboard, pluralPL, formatPLN } from '@/lib/utils';
import { useConfirm } from '@/hooks/useConfirm';
import { useCopyFeedback } from '@/hooks/useCopyFeedback';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ResultGallery from '@/components/results/ResultGallery';
import DescriptionEditor from '@/components/results/DescriptionEditor';
import ImageEditor from '@/components/results/ImageEditor';
import CostSummary from '@/components/results/CostSummary';
import DownloadButton from '@/components/results/DownloadButton';
import InlineAlert from '@/components/shared/InlineAlert';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, Loader2, RotateCcw, Copy, AlertCircle, Check, SlidersHorizontal, FileDown, Clock, ClipboardList } from 'lucide-react';
import type { GeneratedImage, ResultSections } from '@/lib/types';

function NewAuctionButton() {
  const { dispatch } = useWizard();

  const doReset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, [dispatch]);

  const { isConfirming, handleClick, handleBlur } = useConfirm(doReset);

  return (
    <Card className="group border-dashed border-border/60 hover:border-primary/30 transition-all duration-300 hover:shadow-sm">
      <CardContent className="pt-6 text-center space-y-3">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-primary/5 transition-transform group-hover:scale-110">
          <RotateCcw className="h-5 w-5 text-primary/40 transition-transform duration-500 group-hover:rotate-[-180deg]" />
        </div>
        <p className="text-sm text-muted-foreground">
          Chcesz wygenerować kolejny produkt?
        </p>
        <Button
          variant={isConfirming ? 'destructive' : 'outline'}
          size="lg"
          className="gap-2"
          onClick={handleClick}
          onBlur={handleBlur}
          aria-label={isConfirming ? 'Potwierdź reset i rozpocznij nową aukcję' : 'Rozpocznij nową aukcję'}
        >
          <RotateCcw className="h-4 w-4" />
          {isConfirming ? 'Potwierdź reset' : 'Nowa aukcja'}
        </Button>
      </CardContent>
    </Card>
  );
}

export default memo(function Step6Results() {
  const { state, dispatch } = useWizard();
  const hasFetched = useRef(false);
  const editorRef = useRef<HTMLDivElement>(null);
  const [retryCount, setRetryCount] = useState(0);
  const { copied: titleCopied, trigger: triggerTitleCopy } = useCopyFeedback();
  const { copied: featuresCopied, trigger: triggerFeaturesCopy } = useCopyFeedback();
  const { copied: allCopied, trigger: triggerAllCopy } = useCopyFeedback();
  const [editImageKey, setEditImageKey] = useState<string | null>(null);
  const { copied: editorFlash, trigger: triggerEditorFlash } = useCopyFeedback(1500);

  const copyTitle = useCallback(async () => {
    if (!state.resultSections?.title) return;
    const ok = await copyToClipboard(state.resultSections.title);
    if (ok) {
      toast.success('Tytuł skopiowany', { id: 'title-copied' });
      triggerTitleCopy();
    } else {
      toast.error('Nie udało się skopiować', { id: 'copy-error' });
    }
  }, [state.resultSections?.title, triggerTitleCopy]);

  const handleCsvDownload = useCallback(() => {
    if (!state.resultSections) return;
    const entries = Object.entries(state.resultSections.features);
    const bom = '\uFEFF';
    const csv = bom + 'Cecha;Wartość\n' + entries.map(([k, v]) => `"${k.replace(/"/g, '""')}";"${String(v).replace(/"/g, '""')}"`).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cechy-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('CSV pobrany', { id: 'csv-downloaded' });
  }, [state.resultSections]);

  const handleFeaturesCopy = useCallback(async () => {
    if (!state.resultSections) return;
    const entries = Object.entries(state.resultSections.features);
    const text = entries.map(([k, v]) => `${k}: ${v}`).join('\n');
    const ok = await copyToClipboard(text);
    toast[ok ? 'success' : 'error'](ok ? `${entries.length} ${pluralPL(entries.length, 'cecha skopiowana', 'cechy skopiowane', 'cech skopiowanych')}` : 'Nie udało się skopiować', { id: 'features-copied' });
    if (ok) triggerFeaturesCopy();
  }, [state.resultSections, triggerFeaturesCopy]);

  const handleCopyAll = useCallback(async () => {
    if (!state.resultSections) return;
    const parts: string[] = [];
    if (state.resultSections.title) {
      parts.push(`TYTUŁ:\n${state.resultSections.title}`);
    }
    if (state.descriptionHtml) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(state.descriptionHtml, 'text/html');
      const plainDesc = doc.body.textContent || '';
      if (plainDesc.trim()) {
        parts.push(`OPIS:\n${plainDesc.trim()}`);
      }
    }
    const featureEntries = Object.entries(state.resultSections.features);
    if (featureEntries.length > 0) {
      parts.push(`CECHY:\n${featureEntries.map(([k, v]) => `${k}: ${v}`).join('\n')}`);
    }
    if (parts.length === 0) return;
    const ok = await copyToClipboard(parts.join('\n\n'));
    toast[ok ? 'success' : 'error'](ok ? 'Skopiowano tytuł, opis i cechy' : 'Nie udało się skopiować', { id: 'all-copied' });
    if (ok) triggerAllCopy();
  }, [state.resultSections, state.descriptionHtml, triggerAllCopy]);

  const handleSelectForEdit = useCallback((key: string) => {
    setEditImageKey(key);
    editorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    triggerEditorFlash();
  }, [triggerEditorFlash]);

  // Type breakdown for result header (extracted from JSX IIFE)
  const typeBreakdown = useMemo(() => {
    if (state.resultImages.length === 0) return null;
    const counts = state.resultImages.reduce((acc, img) => {
      acc[img.type] = (acc[img.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    const parts: string[] = [];
    if (counts.packshot) parts.push(`${counts.packshot} pack`);
    if (counts.composite) parts.push(`${counts.composite} komp`);
    if (counts.lifestyle) parts.push(`${counts.lifestyle} life`);
    return parts.length > 1 ? parts.join(' · ') : null;
  }, [state.resultImages]);

  // Format generatedAt timestamp (extracted from JSX IIFE)
  const generatedAtFormatted = useMemo(() => {
    if (!state.generatedAt) return '';
    try {
      const d = new Date(state.generatedAt);
      return d.toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }, [state.generatedAt]);

  // Fetch results once on mount - deps intentionally limited to jobId and retryCount
  useEffect(() => {
    const jobId = state.jobId;
    if (hasFetched.current || !jobId || state.resultImages.length > 0) return;
    hasFetched.current = true;
    let cancelled = false;

    const fetchResults = async () => {
      try {
        const data = (await api.getResults(jobId)) as Record<string, unknown>;
        if (cancelled) return;

        const images = (data.images as GeneratedImage[]) || [];
        const rawSections = (data.sections || {}) as Record<string, string>;
        const sections: ResultSections = {
          title: rawSections.title || '',
          description: rawSections.description || '',
          features: (rawSections.features as unknown as Record<string, string>) || {},
          category: rawSections.category || state.suggestedCategory,
        };
        const descHtml = (data.description_html as string) || '';

        dispatch({ type: 'SET_RESULTS', images, sections, description: descHtml });

        if (data.total_cost !== undefined) {
          dispatch({
            type: 'SET_COST',
            total: data.total_cost as number,
            perModel: (data.model_costs as Record<string, number>) || {},
          });
        }
        if (data.elapsed_sec !== undefined) {
          dispatch({
            type: 'SET_ELAPSED',
            seconds: data.elapsed_sec as number,
            timestamp: (data.timestamp as string) || '',
          });
        }
      } catch (err) {
        if (cancelled) return;
        dispatch({ type: 'SET_ERROR', error: `Nie udało się pobrać wyników: ${(err as Error).message}` });
      }
    };

    fetchResults();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- fetch once on mount, deps intentionally limited
  }, [state.jobId, retryCount]);

  // Error state with retry
  if (state.resultImages.length === 0 && state.error) {
    return (
      <Card className="animate-fade-in-up border-destructive/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Błąd ładowania wyników
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-destructive" role="alert">{state.error}</p>
          <Button
            onClick={() => {
              dispatch({ type: 'SET_ERROR', error: null });
              hasFetched.current = false;
              setRetryCount((c) => c + 1);
            }}
            className="gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Spróbuj ponownie
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Loading state
  if (state.resultImages.length === 0 && !state.error) {
    return (
      <Card className="animate-fade-in-up" aria-busy="true">
        <CardHeader>
          <div className="flex items-center gap-2" role="status" aria-live="polite">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <p className="text-lg font-semibold">Ładowanie wyników...</p>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-square w-full rounded-lg animate-pop-in" style={{ animationDelay: `${i * 0.06}s` }} />
            ))}
          </div>
          <Skeleton className="h-6 w-48 rounded-full" />
          <Skeleton className="h-32 w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success header */}
      <Card className="relative border-green-500/20 bg-gradient-to-br from-green-500/5 to-green-500/[0.02] animate-fade-in-up animate-success-glow overflow-hidden shadow-sm shadow-green-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-500/10 shadow-sm animate-check-bounce">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <span className="text-lg animate-text-shimmer">Generowanie zakończone</span>
              {state.resultImages.length > 0 && (
                <p className="text-sm font-normal text-muted-foreground">
                  {state.resultImages.length} {pluralPL(state.resultImages.length, 'grafika gotowa', 'grafiki gotowe', 'grafik gotowych')} do pobrania
                  {typeBreakdown && (
                    <span className="text-muted-foreground/40 text-xs ml-1">({typeBreakdown})</span>
                  )}
                  {state.elapsedSeconds > 0 && (
                    <span className="inline-flex items-center gap-1 ml-2 text-muted-foreground/60">
                      <Clock className="h-3 w-3" />
                      {Math.floor(state.elapsedSeconds / 60) > 0
                        ? `${Math.floor(state.elapsedSeconds / 60)}m ${Math.round(state.elapsedSeconds % 60)}s`
                        : `${Math.round(state.elapsedSeconds)}s`
                      }
                    </span>
                  )}
                  {generatedAtFormatted && (
                    <span className="inline-flex items-center gap-1 ml-2 text-muted-foreground/40 text-xs">
                      {generatedAtFormatted}
                    </span>
                  )}
                  {state.totalCost > 0 && (
                    <span className="inline-flex items-center gap-1 ml-2 text-muted-foreground/40 text-xs font-mono tabular-nums">
                      {formatPLN(state.totalCost)}
                    </span>
                  )}
                </p>
              )}
            </div>
          </CardTitle>
          {state.resultSections && (
            <div className="space-y-2 pt-2">
              {state.resultSections.title && (
                <div
                  className="group flex items-center gap-2 rounded-lg border border-border bg-card p-3 cursor-pointer touch-manipulation hover:bg-muted/20 transition-colors focus-visible:ring-2 focus-visible:ring-ring outline-none"
                  onClick={copyTitle}
                  role="button"
                  tabIndex={0}
                  aria-label={`Skopiuj tytuł: ${state.resultSections.title}`}
                  title="Kliknij, aby skopiować tytuł"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      copyTitle();
                    }
                  }}
                >
                  <div className="flex-1">
                    <p className="text-sm font-semibold">{state.resultSections.title}</p>
                    <p className={`text-[10px] mt-0.5 tabular-nums flex items-center gap-1.5 ${state.resultSections.title.length > 75 ? 'text-destructive' : 'text-muted-foreground/40'}`}>
                      {state.resultSections.title.length}/75 zn.
                      {state.resultSections.title.length > 75
                        ? <span className="inline-flex items-center gap-0.5 text-destructive"><AlertCircle className="h-2.5 w-2.5" /> przekroczony limit Allegro</span>
                        : <span className="inline-flex items-center gap-0.5 text-green-600"><CheckCircle className="h-2.5 w-2.5" /> Allegro OK</span>
                      }
                    </p>
                  </div>
                  {titleCopied ? (
                    <Check className="h-3.5 w-3.5 text-green-600 shrink-0" />
                  ) : (
                    <Copy className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors shrink-0" />
                  )}
                </div>
              )}
              <div className="flex items-center gap-2 flex-wrap">
                {state.resultSections.category && (
                  <Badge variant="secondary">
                    {state.resultSections.category}
                  </Badge>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-xs h-7"
                  onClick={handleCopyAll}
                  aria-label="Kopiuj tytuł, opis i cechy do schowka"
                  title="Kopiuj tytuł + opis + cechy"
                >
                  {allCopied ? (
                    <Check className="h-3 w-3 text-green-600" />
                  ) : (
                    <ClipboardList className="h-3 w-3" />
                  )}
                  {allCopied ? 'Skopiowano' : 'Kopiuj wszystko'}
                </Button>
              </div>
            </div>
          )}
        </CardHeader>
      </Card>

      {/* Error */}
      {state.error && (
        <InlineAlert message={state.error} onDismiss={() => dispatch({ type: 'SET_ERROR', error: null })} />
      )}

      {/* Gallery */}
      {state.resultImages.length > 0 && (
        <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <ResultGallery images={state.resultImages} onSelectForEdit={handleSelectForEdit} />
        </div>
      )}

      {/* Description editor */}
      <div className="animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
        <DescriptionEditor />
      </div>

      {/* Image editor */}
      {state.resultImages.length > 0 && (
        <div ref={editorRef} className={`animate-fade-in-up rounded-xl transition-all duration-500 ${editorFlash ? 'ring-2 ring-primary/40' : ''}`} style={{ animationDelay: '0.2s' }}>
          <ImageEditor preselectedKey={editImageKey} />
        </div>
      )}

      {/* Features summary */}
      {state.resultSections && Object.keys(state.resultSections.features).length > 0 && (
        <Card className="animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <SlidersHorizontal className="h-4 w-4 text-primary" />
                Cechy produktu
              </CardTitle>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 text-xs h-8"
                  onClick={handleCsvDownload}
                  aria-label="Pobierz cechy jako CSV"
                  title="Pobierz cechy jako CSV"
                >
                  <FileDown className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">CSV</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 text-xs h-8"
                  onClick={handleFeaturesCopy}
                  aria-label="Kopiuj wszystkie cechy"
                >
                  {featuresCopied ? (
                    <Check className="h-3.5 w-3.5 text-green-600" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                  {featuresCopied ? 'Skopiowano' : 'Kopiuj'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border/30">
              {Object.entries(state.resultSections.features).map(([key, val], i) => (
                <div
                  key={key}
                  className={`flex items-center justify-between text-sm py-2.5 px-3 rounded-md touch-manipulation transition-colors cursor-pointer animate-fade-in-up ${i % 2 === 0 ? 'bg-muted/15' : ''} hover:bg-muted/25 focus-visible:ring-2 focus-visible:ring-ring outline-none`}
                  style={{ animationDelay: `${i * 0.04}s` }}
                  title={`Kliknij, aby skopiować: ${key}: ${val}`}
                  role="button"
                  tabIndex={0}
                  onClick={async () => {
                    const ok = await copyToClipboard(`${key}: ${val}`);
                    toast[ok ? 'success' : 'error'](ok ? `Skopiowano: ${key}` : 'Nie udało się skopiować', { id: 'feature-copied' });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      (e.target as HTMLElement).click();
                    }
                  }}
                >
                  <span className="text-muted-foreground text-xs uppercase tracking-wide">{key}</span>
                  <span className="font-medium text-right ml-4 text-foreground">{val}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Costs */}
      <div className="animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
        <CostSummary />
      </div>

      {/* Download */}
      <div className="animate-fade-in-up pb-4" style={{ animationDelay: '0.35s' }}>
        <DownloadButton />
      </div>

      {/* New auction */}
      <div className="animate-fade-in-up pb-8" style={{ animationDelay: '0.4s' }}>
        <NewAuctionButton />
      </div>
    </div>
  );
});
