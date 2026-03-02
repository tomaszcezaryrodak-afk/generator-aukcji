import { useCallback, useMemo, memo } from 'react';
import { useWizard } from '@/context/WizardContext';
import { pluralPL } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import ColorChip from '@/components/shared/ColorChip';
import { Button } from '@/components/ui/button';
import { Palette, AlertCircle, ArrowLeft } from 'lucide-react';

export default memo(function Step3Colors() {
  const { state, dispatch } = useWizard();

  const handleToggle = useCallback((key: string, color: string) => {
    const updated = { ...state.confirmedColors };
    if (updated[key] === color) {
      delete updated[key];
    } else {
      updated[key] = color;
    }
    dispatch({ type: 'SET_CONFIRMED_COLORS', colors: updated });
  }, [state.confirmedColors, dispatch]);

  // Filtruj null/puste kolory
  const colorEntries = useMemo(
    () => Object.entries(state.suggestedColors).filter(
      ([, color]) => color && color !== 'null' && color.trim() !== '',
    ),
    [state.suggestedColors],
  );

  const selectedCount = Object.keys(state.confirmedColors).length;

  const handleToggleAll = useCallback(() => {
    if (selectedCount === colorEntries.length) {
      dispatch({ type: 'SET_CONFIRMED_COLORS', colors: {} });
    } else {
      const filtered = Object.fromEntries(colorEntries);
      dispatch({ type: 'SET_CONFIRMED_COLORS', colors: filtered });
    }
  }, [selectedCount, colorEntries, dispatch]);

  if (colorEntries.length === 0) {
    return (
      <Card className="animate-fade-in-up">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Kolory produktów</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            AI nie rozpoznała kolorów na zdjęciach. Spróbuj wgrać lepsze zdjęcia lub dodać opis kolorów w specyfikacji.
          </p>
          <Button
            variant="outline"
            className="gap-2"
            onClick={() => dispatch({ type: 'SET_STEP', step: 1 })}
          >
            <ArrowLeft className="h-4 w-4" />
            Wróć do zdjęć
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Palette className="h-5 w-5 text-primary" />
            <CardTitle>Potwierdź kolory</CardTitle>
          </div>
          <Badge variant={selectedCount > 0 ? 'default' : 'destructive'} className="font-mono tabular-nums">
            {selectedCount}/{colorEntries.length}
          </Badge>
        </div>
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Kliknij, aby odznaczyć błędnie rozpoznane kolory
          </p>
          {colorEntries.length > 2 && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7"
              onClick={handleToggleAll}
              aria-label={selectedCount === colorEntries.length ? `Odznacz wszystkie ${colorEntries.length} ${pluralPL(colorEntries.length, 'kolor', 'kolory', 'kolorów')}` : `Zaznacz wszystkie ${colorEntries.length} ${pluralPL(colorEntries.length, 'kolor', 'kolory', 'kolorów')}`}
            >
              {selectedCount === colorEntries.length ? 'Odznacz wszystkie' : 'Zaznacz wszystkie'}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {selectedCount === 0 && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 animate-fade-in-up" role="alert">
              <p className="text-sm text-destructive flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                Zaznacz co najmniej jeden kolor, aby przejść dalej
              </p>
            </div>
          )}
          <div className="divide-y divide-border/40">
            {colorEntries.map(([key, color], i) => (
              <div key={key} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0 animate-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }}>
                <span className="text-xs font-medium text-muted-foreground/60 tabular-nums w-5 shrink-0">{i + 1}.</span>
                <p className="text-sm font-medium capitalize text-muted-foreground min-w-[80px] shrink-0">{key}</p>
                <div className="flex flex-wrap gap-2">
                  <ColorChip
                    color={color}
                    label={color}
                    isSelected={state.confirmedColors[key] === color}
                    onClick={() => handleToggle(key, color)}
                  />
                </div>
              </div>
            ))}
          </div>
          {selectedCount > 0 && selectedCount < colorEntries.length && (
            <p className="text-[10px] text-muted-foreground/40 pt-2">
              {colorEntries.length - selectedCount} {pluralPL(colorEntries.length - selectedCount, 'kolor odznaczony', 'kolory odznaczone', 'kolorów odznaczonych')}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
});
