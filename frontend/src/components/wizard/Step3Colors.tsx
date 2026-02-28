import { useWizard } from '@/context/WizardContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import ColorChip from '@/components/shared/ColorChip';

export default function Step3Colors() {
  const { state, dispatch } = useWizard();

  const handleToggle = (key: string, color: string) => {
    const updated = { ...state.confirmedColors };
    if (updated[key] === color) {
      delete updated[key];
    } else {
      updated[key] = color;
    }
    dispatch({ type: 'SET_CONFIRMED_COLORS', colors: updated });
  };

  const colorEntries = Object.entries(state.suggestedColors);

  if (colorEntries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Kolory produktów</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Brak rozpoznanych kolorów. Wróć do poprzedniego kroku i spróbuj ponownie.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Potwierdź kolory</CardTitle>
        <p className="text-sm text-muted-foreground">
          Sprawdź rozpoznane kolory. Kliknij, aby odznaczyć błędy
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Object.keys(state.confirmedColors).length === 0 && (
            <p className="text-sm text-destructive" role="alert">
              Zaznacz co najmniej jeden kolor, aby przejść dalej.
            </p>
          )}
          {colorEntries.map(([key, color]) => (
            <div key={key}>
              <p className="mb-2 text-sm font-medium capitalize">{key}</p>
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
      </CardContent>
    </Card>
  );
}
