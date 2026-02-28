import { useState } from 'react';
import { useWizard } from '@/context/WizardContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import FeatureRow from '@/components/shared/FeatureRow';
import { Plus } from 'lucide-react';

export default function Step4Features() {
  const { state, dispatch } = useWizard();
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const handleChange = (index: number, value: string) => {
    const updated = [...state.confirmedFeatures];
    updated[index] = { ...updated[index], value };
    dispatch({ type: 'SET_CONFIRMED_FEATURES', features: updated });
  };

  const handleRemove = (index: number) => {
    dispatch({
      type: 'SET_CONFIRMED_FEATURES',
      features: state.confirmedFeatures.filter((_, i) => i !== index),
    });
  };

  const handleAdd = () => {
    if (!newKey.trim() || !newValue.trim()) return;
    dispatch({
      type: 'SET_CONFIRMED_FEATURES',
      features: [...state.confirmedFeatures, { key: newKey.trim(), value: newValue.trim() }],
    });
    setNewKey('');
    setNewValue('');
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cechy i parametry</CardTitle>
        <p className="text-sm text-muted-foreground">
          Edytuj lub dodaj cechy produktu. Te dane trafią do opisu aukcji
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {state.confirmedFeatures.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            Brak cech. Dodaj pierwszą cechę produktu poniżej
          </p>
        ) : (
          state.confirmedFeatures.map((f, i) => (
            <FeatureRow
              key={f.key + i}
              label={f.key}
              value={f.value}
              onChange={(v) => handleChange(i, v)}
              onRemove={() => handleRemove(i)}
            />
          ))
        )}

        <div className="flex items-center gap-2 border-t border-border pt-3">
          <Input
            placeholder="Nazwa cechy"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            className="w-40"
            aria-label="Nazwa nowej cechy"
          />
          <Input
            placeholder="Wartość"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            className="flex-1"
            aria-label="Wartość nowej cechy"
          />
          <Button
            variant="outline"
            size="icon"
            className="shrink-0"
            onClick={handleAdd}
            disabled={!newKey.trim() || !newValue.trim()}
            aria-label="Dodaj cechę"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {state.productDNA && (
          <div className="mt-4 rounded-lg bg-muted/10 p-4">
            <p className="mb-2 text-sm font-medium">Product DNA (podgląd)</p>
            <pre className="max-h-48 overflow-auto text-xs text-muted-foreground">
              {JSON.stringify(state.productDNA, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
