import { useEffect, useRef } from 'react';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';

export default function Step2Analysis() {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const hasStarted = useRef(false);

  useEffect(() => {
    if (hasStarted.current || state.suggestedCategory) return;
    if (state.images.length === 0) return;

    let cancelled = false;
    hasStarted.current = true;
    dispatch({ type: 'SET_ANALYZING', isAnalyzing: true });

    const formData = new FormData();
    state.images.forEach((img, i) => {
      formData.append('images', img.file);
      if (i === state.mainImageIndex) formData.append('main_image_index', String(i));
    });
    if (state.specText) formData.append('spec_text', state.specText);
    if (sessionId) formData.append('session_id', sessionId);

    api
      .uploadAndAnalyze(formData)
      .then((res: Record<string, unknown>) => {
        if (cancelled) return;
        if (res.session_id) {
          dispatch({ type: 'SET_SESSION_ID', sessionId: res.session_id as string });
        }

        const colors = (res.suggested_colors || res.colors || {}) as Record<string, string>;
        const features = Array.isArray(res.features)
          ? (res.features as Array<{ key: string; value: string }>)
          : Object.entries((res.features || {}) as Record<string, string>).map(([key, value]) => ({
              key,
              value,
            }));

        dispatch({
          type: 'SET_ANALYSIS',
          data: {
            category: (res.category || res.suggested_category || '') as string,
            colors,
            features,
          },
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        hasStarted.current = false;
        dispatch({ type: 'SET_ERROR', error: `Błąd analizy: ${err.message}` });
        dispatch({ type: 'SET_ANALYZING', isAnalyzing: false });
      });

    return () => { cancelled = true; };
  }, [state.images, state.mainImageIndex, state.specText, state.suggestedCategory, sessionId, dispatch]);

  if (state.error && !state.isAnalyzing) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Błąd analizy
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive" role="alert">{state.error}</p>
          <Button
            className="mt-3"
            onClick={() => {
              dispatch({ type: 'SET_ERROR', error: null });
              hasStarted.current = false;
            }}
          >
            Spróbuj ponownie
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (state.isAnalyzing) {
    return (
      <Card>
        <CardHeader>
          <div aria-live="polite" aria-busy={true}>
            <CardTitle className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              Analizuję zdjęcia...
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Gemini rozpoznaje produkty, kolory i cechy
            </p>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-6 w-64" />
          <Skeleton className="h-6 w-56" />
          <div className="grid grid-cols-3 gap-3 pt-2">
            <Skeleton className="aspect-square rounded-lg" />
            <Skeleton className="aspect-square rounded-lg" />
            <Skeleton className="aspect-square rounded-lg" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-600" />
          Analiza zakończona
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Kategoria</p>
          <Badge variant="secondary" className="mt-1">
            {state.suggestedCategory || 'Nierozpoznana'}
          </Badge>
        </div>

        {Object.keys(state.suggestedColors).length > 0 && (
          <div>
            <p className="text-sm font-medium text-muted-foreground">Rozpoznane kolory</p>
            <div className="mt-1 flex flex-wrap gap-2">
              {Object.entries(state.suggestedColors).map(([key, color]) => (
                <Badge key={key} variant="outline" className="gap-1.5">
                  <span
                    className="h-3 w-3 rounded-full border"
                    style={{ backgroundColor: color }}
                  />
                  {key}: {color}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {state.suggestedFeatures.length > 0 && (
          <div>
            <p className="text-sm font-medium text-muted-foreground">Rozpoznane cechy</p>
            <div className="mt-1 space-y-1">
              {state.suggestedFeatures.slice(0, 8).map((f) => (
                <div key={f.key} className="flex gap-2 text-sm">
                  <span className="font-medium">{f.key}:</span>
                  <span>{f.value}</span>
                </div>
              ))}
              {state.suggestedFeatures.length > 8 && (
                <p className="text-xs text-muted-foreground">
                  +{state.suggestedFeatures.length - 8} więcej (widoczne w kroku Cechy)
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
