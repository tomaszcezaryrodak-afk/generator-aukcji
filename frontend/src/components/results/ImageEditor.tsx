import { useState, useEffect, memo } from 'react';
import { useWizard } from '@/context/WizardContext';
import { handleImgError, handleGridKeyDown } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ChatPanel from '@/components/results/ChatPanel';
import SelfCheckBadge from '@/components/generation/SelfCheckBadge';
import { ImageIcon, X } from 'lucide-react';

interface ImageEditorProps {
  preselectedKey?: string | null;
}

export default memo(function ImageEditor({ preselectedKey }: ImageEditorProps) {
  const { state } = useWizard();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [prevPreselected, setPrevPreselected] = useState(preselectedKey);

  // Sync external preselection (derived state pattern)
  if (preselectedKey !== prevPreselected) {
    setPrevPreselected(preselectedKey);
    if (preselectedKey) setSelectedKey(preselectedKey);
  }

  const selectedImage = state.resultImages.find((img) => img.key === selectedKey);

  // Keyboard navigation: Escape to deselect, ArrowLeft/Right to navigate
  useEffect(() => {
    if (!selectedKey) return;
    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      if (e.key === 'Escape') {
        setSelectedKey(null);
        return;
      }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const idx = state.resultImages.findIndex((img) => img.key === selectedKey);
        if (idx < 0) return;
        const next = e.key === 'ArrowRight'
          ? (idx + 1) % state.resultImages.length
          : (idx - 1 + state.resultImages.length) % state.resultImages.length;
        setSelectedKey(state.resultImages[next].key);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [selectedKey, state.resultImages]);

  if (!selectedKey || !selectedImage) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ImageIcon className="h-4 w-4 text-primary" />
            Edycja obrazu
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Wybierz obraz poniżej lub kliknij &quot;Edytuj&quot; w galerii
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-6" role="group" aria-label="Wybierz obraz do edycji">
            {state.resultImages.map((img, i) => (
              <button
                key={img.key}
                type="button"
                aria-label={`Edytuj obraz: ${img.label || img.key}`}
                className="group relative cursor-pointer overflow-hidden rounded-lg border border-border touch-manipulation transition-all duration-200 hover:shadow-md hover:border-primary/30 hover:-translate-y-0.5 animate-pop-in"
                style={{ animationDelay: `${i * 0.05}s` }}
                onClick={() => setSelectedKey(img.key)}
                onKeyDown={(e) => handleGridKeyDown(e, { selector: 'button' })}
              >
                <img
                  src={img.url}
                  alt={img.label || img.key}
                  className="aspect-square w-full object-cover transition-transform duration-200 group-hover:scale-105"
                  loading="lazy"
                  decoding="async"
                  onError={handleImgError}
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/30">
                  <span className="text-[10px] font-medium text-white opacity-0 transition-opacity group-hover:opacity-100">
                    Edytuj
                  </span>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/20 animate-fade-in-up">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <ImageIcon className="h-4 w-4 text-primary" />
            Edycja: {selectedImage.label || selectedImage.key}
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted-foreground/50 tabular-nums hidden sm:inline">
              {state.resultImages.findIndex((img) => img.key === selectedKey) + 1}/{state.resultImages.length}
            </span>
            <kbd className="rounded bg-muted/50 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground/40 hidden md:inline" title="← → nawigacja, Esc zamknij">Esc</kbd>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setSelectedKey(null)}
              aria-label="Zamknij edytor"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="overflow-hidden rounded-lg border-2 border-primary/30 bg-muted/10 shadow-sm ring-2 ring-primary/10 ring-offset-1">
          <img
            key={selectedKey}
            src={selectedImage.url}
            alt={selectedImage.label || selectedImage.key}
            className="max-h-80 w-full object-contain animate-lightbox-fade"
            decoding="async"
            onError={handleImgError}
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{selectedImage.type}</span>
          {selectedImage.selfCheck && (
            <SelfCheckBadge check={selectedImage.selfCheck} />
          )}
        </div>
        <ChatPanel mode="image" imageKey={selectedKey} />
      </CardContent>
    </Card>
  );
});
