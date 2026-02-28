import { useEffect, useRef } from 'react';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import ResultGallery from '@/components/results/ResultGallery';
import DescriptionEditor from '@/components/results/DescriptionEditor';
import ImageEditor from '@/components/results/ImageEditor';
import CostSummary from '@/components/results/CostSummary';
import DownloadButton from '@/components/results/DownloadButton';
import { Skeleton } from '@/components/ui/skeleton';
import { CheckCircle } from 'lucide-react';
import type { GeneratedImage, ResultSections } from '@/lib/types';

export default function Step6Results() {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const hasFetched = useRef(false);

  useEffect(() => {
    if (hasFetched.current || !sessionId || state.resultImages.length > 0) return;
    hasFetched.current = true;

    const fetchResults = async () => {
      try {
        const data = (await api.getResults(sessionId)) as Record<string, unknown>;

        const images = (data.images as GeneratedImage[]) || [];
        const sections: ResultSections = {
          title: (data.title as string) || '',
          description: (data.description_text as string) || '',
          features: (data.features as Record<string, string>) || {},
          category: (data.category as string) || state.suggestedCategory,
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
      } catch {
        dispatch({ type: 'SET_ERROR', error: 'Nie udało się pobrać wyników' });
      }
    };

    fetchResults();
  }, [sessionId]);

  // Loading state
  if (state.resultImages.length === 0 && !state.error) {
    return (
      <Card>
        <CardHeader>
          <p role="status" aria-live="polite" className="text-lg font-semibold">Ładowanie wyników...</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-square w-full rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-32 w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="border-primary/20 bg-primary/3">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15">
              <CheckCircle className="h-5 w-5 text-primary" />
            </div>
            Generowanie zakończone
          </CardTitle>
          {state.resultSections && (
            <div className="space-y-2 pt-3">
              {state.resultSections.title && (
                <div className="rounded-lg border border-border bg-card p-3">
                  <p className="text-sm font-semibold">{state.resultSections.title}</p>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Kategoria: {state.resultSections.category}
              </p>
            </div>
          )}
        </CardHeader>
      </Card>

      {/* Error */}
      {state.error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive" role="alert">
          {state.error}
        </div>
      )}

      {/* Gallery */}
      {state.resultImages.length > 0 && (
        <ResultGallery images={state.resultImages} />
      )}

      {/* Description editor */}
      <DescriptionEditor />

      {/* Image editor */}
      {state.resultImages.length > 0 && <ImageEditor />}

      {/* Features summary */}
      {state.resultSections && Object.keys(state.resultSections.features).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cechy produktu</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {Object.entries(state.resultSections.features).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{key}</span>
                  <span>{val}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Costs */}
      <CostSummary />

      {/* Download */}
      <DownloadButton />
    </div>
  );
}
