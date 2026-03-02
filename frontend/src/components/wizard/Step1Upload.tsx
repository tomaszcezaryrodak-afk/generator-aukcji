import { useCallback, useEffect, useRef, useState, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { pluralPL, formatFileSize } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import DropZone from '@/components/shared/DropZone';
import ImageGrid from '@/components/shared/ImageGrid';
import type { UploadedImage } from '@/lib/types';
import { ImagePlus, FileText, Info, X } from 'lucide-react';

export default memo(function Step1Upload() {
  const { state, dispatch } = useWizard();

  const specRef = useRef<HTMLTextAreaElement>(null);

  // Track latest images for cleanup on unmount
  const imagesRef = useRef(state.images);

  useEffect(() => {
    imagesRef.current = state.images;
  });

  useEffect(() => {
    return () => {
      imagesRef.current.forEach((img) => URL.revokeObjectURL(img.preview));
    };
  }, []);

  const handleFiles = useCallback(
    (files: File[]) => {
      const spotsLeft = 20 - state.images.length;
      if (spotsLeft <= 0) {
        toast.warning('Limit 20 zdjęć osiągnięty', { id: 'image-limit' });
        return;
      }
      const filesToAdd = files.slice(0, spotsLeft);
      if (filesToAdd.length < files.length) {
        toast.info(`Dodano ${filesToAdd.length} z ${files.length} ${pluralPL(files.length, 'zdjęcia', 'zdjęć', 'zdjęć')} (limit 20)`, { id: 'image-limit' });
      }
      const newImages: UploadedImage[] = filesToAdd.map((file) => ({
        file,
        preview: URL.createObjectURL(file),
        name: file.name,
      }));
      dispatch({ type: 'SET_IMAGES', images: [...state.images, ...newImages] });

      // Auto-focus spec textarea when first images are added and spec is empty
      if (state.images.length === 0 && !state.specText.trim()) {
        requestAnimationFrame(() => specRef.current?.focus());
      }
    },
    [state.images, state.specText, dispatch],
  );

  const handleSetMain = useCallback(
    (i: number) => dispatch({ type: 'SET_MAIN_IMAGE', index: i }),
    [dispatch],
  );

  const handleRemove = useCallback(
    (index: number) => {
      const updated = state.images.filter((_, i) => i !== index);
      URL.revokeObjectURL(state.images[index].preview);
      dispatch({ type: 'SET_IMAGES', images: updated });
      if (state.mainImageIndex >= updated.length) {
        dispatch({ type: 'SET_MAIN_IMAGE', index: Math.max(0, updated.length - 1) });
      }
    },
    [state.images, state.mainImageIndex, dispatch],
  );

  // Auto-resize textarea
  const autoResize = useCallback(() => {
    const el = specRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 320)}px`;
  }, []);

  useEffect(() => {
    autoResize();
  }, [state.specText, autoResize]);

  const hasRestoredAnalysis = state.suggestedCategory && state.images.length === 0;
  const [showRestored, setShowRestored] = useState(true);

  return (
    <div className="space-y-6">
      {hasRestoredAnalysis && showRestored && (
        <div className="flex items-start gap-2.5 rounded-lg border border-primary/20 bg-primary/5 p-3 animate-fade-in-up" role="status">
          <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <p className="font-medium text-foreground">Przywrócono poprzednią analizę</p>
            <p className="text-muted-foreground mt-0.5">
              Kategoria: {state.suggestedCategory}. Wgraj zdjęcia ponownie, aby kontynuować od kroku 2.
            </p>
          </div>
          <button
            type="button"
            className="shrink-0 rounded p-0.5 text-primary/60 touch-manipulation hover:text-primary transition-colors"
            onClick={() => setShowRestored(false)}
            aria-label="Zamknij komunikat"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      <Card className="animate-fade-in-up">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ImagePlus className="h-5 w-5 text-primary" />
              <CardTitle>Zdjęcia produktów</CardTitle>
            </div>
            {state.images.length > 0 && (
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="font-mono">
                  {state.images.length}/20
                </Badge>
                <span className="text-[10px] text-muted-foreground/50 font-mono tabular-nums hidden sm:inline">
                  {formatFileSize(state.images.reduce((sum, img) => sum + img.file.size, 0))}
                </span>
              </div>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            Wgraj zdjęcia zlewu, baterii i akcesoriów. Kliknij zdjęcie, aby ustawić je jako główne
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {state.images.length < 20 && (
            <DropZone onFiles={handleFiles} maxFiles={20 - state.images.length} />
          )}
          <ImageGrid
            images={state.images}
            mainIndex={state.mainImageIndex}
            onRemove={handleRemove}
            onSetMain={handleSetMain}
          />
        </CardContent>
      </Card>

      <Card className={`animate-fade-in-up ${state.images.length > 0 && !state.specText.trim() ? 'border-primary/30 ring-1 ring-primary/10' : ''}`} style={{ animationDelay: '0.1s' }}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className={`h-5 w-5 ${state.images.length > 0 && !state.specText.trim() ? 'text-primary animate-pulse' : 'text-primary'}`} />
            <CardTitle>Specyfikacja produktu</CardTitle>
          </div>
          <p className="text-sm text-muted-foreground">
            {state.images.length > 0 && !state.specText.trim()
              ? 'Wklej specyfikację, aby przejść do analizy'
              : 'Wklej opis ze sklepu lub dane techniczne produktu'}
          </p>
        </CardHeader>
        <CardContent>
          <Label htmlFor="spec-text" className="sr-only">
            Specyfikacja
          </Label>
          <div className="relative">
            <Textarea
              ref={specRef}
              id="spec-text"
              value={state.specText}
              onChange={(e) => dispatch({ type: 'SET_SPEC_TEXT', text: e.target.value.slice(0, 5000) })}
              placeholder="np. Zlew granitowy jednokomorowy z ociekaczem, kolor: czarny, wymiary: 78x50cm, materiał: granit syntetyczny..."
              rows={3}
              maxLength={5000}
              className="resize-none pr-16 overflow-hidden transition-[height] duration-200"
              autoComplete="off"
            />
            {state.specText.length > 0 && (
              <span
                className={`absolute bottom-2 right-3 text-[10px] tabular-nums ${state.specText.length > 4500 ? 'text-destructive' : 'text-muted-foreground/60'}`}
                aria-live="polite"
              >
                {state.specText.split(/\s+/).filter(Boolean).length} słów · {state.specText.length}/5000
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
