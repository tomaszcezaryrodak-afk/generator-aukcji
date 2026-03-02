import { useState, useRef, useCallback, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { pluralPL } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import FeatureRow from '@/components/shared/FeatureRow';
import { Plus, SlidersHorizontal, Download } from 'lucide-react';

export default memo(function Step4Features() {
  const { state, dispatch } = useWizard();
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const keyInputRef = useRef<HTMLInputElement>(null);

  const handleChange = useCallback((index: number, value: string) => {
    const updated = [...state.confirmedFeatures];
    updated[index] = { ...updated[index], value };
    dispatch({ type: 'SET_CONFIRMED_FEATURES', features: updated });
  }, [state.confirmedFeatures, dispatch]);

  const handleRemove = useCallback((index: number) => {
    dispatch({
      type: 'SET_CONFIRMED_FEATURES',
      features: state.confirmedFeatures.filter((_, i) => i !== index),
    });
  }, [state.confirmedFeatures, dispatch]);

  const handleMove = useCallback((index: number, direction: 'up' | 'down') => {
    const features = [...state.confirmedFeatures];
    const target = direction === 'up' ? index - 1 : index + 1;
    if (target < 0 || target >= features.length) return;
    [features[index], features[target]] = [features[target], features[index]];
    dispatch({ type: 'SET_CONFIRMED_FEATURES', features });
  }, [state.confirmedFeatures, dispatch]);

  const handleLabelChange = useCallback((index: number, label: string) => {
    const updated = [...state.confirmedFeatures];
    updated[index] = { ...updated[index], key: label };
    dispatch({ type: 'SET_CONFIRMED_FEATURES', features: updated });
  }, [state.confirmedFeatures, dispatch]);

  const handleAdd = () => {
    if (!newKey.trim() || !newValue.trim()) return;
    const normalizedKey = newKey.trim().toLowerCase();
    const duplicate = state.confirmedFeatures.find((f) => f.key.toLowerCase() === normalizedKey);
    if (duplicate) {
      toast.warning(`Cecha "${duplicate.key}" już istnieje`, { id: 'feature-duplicate' });
      return;
    }
    dispatch({
      type: 'SET_CONFIRMED_FEATURES',
      features: [...state.confirmedFeatures, { key: newKey.trim(), value: newValue.trim() }],
    });
    setNewKey('');
    setNewValue('');
    keyInputRef.current?.focus();
  };

  const featureCount = state.confirmedFeatures.length;
  const featureLabel = pluralPL(featureCount, 'cecha', 'cechy', 'cech');

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && newKey.trim() && newValue.trim()) {
      e.preventDefault();
      handleAdd();
    }
    if (e.key === 'Escape' && (newKey.trim() || newValue.trim())) {
      e.preventDefault();
      setNewKey('');
      setNewValue('');
    }
  };

  const handleImportDNA = useCallback(() => {
    if (!state.productDNA || typeof state.productDNA !== 'object') return;
    const dna = state.productDNA as Record<string, unknown>;
    const existingKeys = new Set(state.confirmedFeatures.map((f) => f.key.toLowerCase()));
    const newFeatures: Array<{ key: string; value: string }> = [];
    for (const [key, val] of Object.entries(dna)) {
      if (val == null || val === '' || existingKeys.has(key.toLowerCase())) continue;
      const strVal = typeof val === 'object' ? JSON.stringify(val) : String(val);
      if (strVal.trim()) newFeatures.push({ key, value: strVal });
    }
    if (newFeatures.length > 0) {
      dispatch({ type: 'SET_CONFIRMED_FEATURES', features: [...state.confirmedFeatures, ...newFeatures] });
    }
  }, [state.productDNA, state.confirmedFeatures, dispatch]);

  return (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-primary" />
            <CardTitle>Cechy i parametry</CardTitle>
          </div>
          <Badge variant="secondary" className="font-mono">
            {featureCount} {featureLabel}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Edytuj lub dodaj cechy produktu. Te dane trafią do opisu aukcji
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {state.confirmedFeatures.length === 0 ? (
          <div className="py-6 text-center animate-fade-in-up space-y-3">
            <SlidersHorizontal className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
            <p className="text-sm text-muted-foreground">
              {state.productDNA ? 'Importuj cechy z analizy DNA lub dodaj ręcznie' : 'Brak cech. Dodaj pierwszą cechę produktu poniżej'}
            </p>
            {state.productDNA && (
              <Button
                variant="outline"
                className="gap-2 border-primary/30 text-primary hover:bg-primary/5 animate-pulse-glow"
                onClick={handleImportDNA}
              >
                <Download className="h-4 w-4" />
                Importuj cechy z DNA
              </Button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {state.confirmedFeatures.map((f, i) => (
              <div key={f.key + i} className="py-1.5 first:pt-0 last:pb-0 animate-fade-in-up" style={{ animationDelay: `${i * 0.03}s` }}>
                <FeatureRow
                  label={f.key}
                  value={f.value}
                  onChange={(v) => handleChange(i, v)}
                  onRemove={() => handleRemove(i)}
                  onLabelChange={(label) => handleLabelChange(i, label)}
                  onMove={(dir) => handleMove(i, dir)}
                  canMoveUp={i > 0}
                  canMoveDown={i < state.confirmedFeatures.length - 1}
                />
              </div>
            ))}
          </div>
        )}

        <div className="space-y-1.5 border-t border-border pt-4">
          <div className="flex items-center gap-2" onKeyDown={handleKeyDown}>
            <Input
              ref={keyInputRef}
              placeholder="np. Materiał"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value.slice(0, 100))}
              maxLength={100}
              enterKeyHint="next"
              className="w-36 sm:w-40"
              aria-label="Nazwa nowej cechy"
              autoComplete="off"
            />
            <Input
              placeholder="np. Granit kompozytowy"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value.slice(0, 200))}
              maxLength={200}
              enterKeyHint="done"
              className="flex-1"
              aria-label="Wartość nowej cechy"
              autoComplete="off"
            />
            <Button
              variant="outline"
              size="icon"
              className="shrink-0 h-9 w-9"
              onClick={handleAdd}
              disabled={!newKey.trim() || !newValue.trim()}
              aria-label="Dodaj cechę"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          {newKey.trim() && newValue.trim() && (
            <p className="text-[10px] text-muted-foreground/40 pl-1 flex items-center gap-1">
              <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Enter</kbd>
              <span>aby dodać</span>
            </p>
          )}
        </div>

        {state.productDNA && (
          <details className="mt-4 rounded-lg border border-border">
            <summary className="cursor-pointer touch-manipulation px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors flex items-center justify-between">
              <span>Product DNA (dane techniczne)</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1.5 text-xs text-primary"
                onClick={(e) => { e.preventDefault(); handleImportDNA(); }}
                aria-label="Importuj cechy z analizy DNA"
              >
                <Download className="h-3 w-3" />
                Importuj
              </Button>
            </summary>
            <div className="border-t border-border">
              {typeof state.productDNA === 'object' && !Array.isArray(state.productDNA) ? (
                <div className="divide-y divide-border/30">
                  {Object.entries(state.productDNA as Record<string, unknown>).map(([key, val], i) => (
                    <div
                      key={key}
                      className={`flex items-start justify-between gap-3 px-4 py-2.5 text-xs ${i % 2 === 0 ? 'bg-muted/10' : ''}`}
                    >
                      <span className="text-muted-foreground/70 uppercase tracking-wide shrink-0">{key}</span>
                      <span className="font-medium text-foreground text-right break-words">
                        {typeof val === 'object' ? JSON.stringify(val) : String(val ?? '')}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <pre className="max-h-48 overflow-auto overscroll-contain text-xs text-muted-foreground font-mono p-4">
                  {JSON.stringify(state.productDNA, null, 2)}
                </pre>
              )}
            </div>
          </details>
        )}
      </CardContent>
    </Card>
  );
});
