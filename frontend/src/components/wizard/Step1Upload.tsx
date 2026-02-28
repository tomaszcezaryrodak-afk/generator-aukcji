import { useCallback, useEffect } from 'react';
import { useWizard } from '@/context/WizardContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import DropZone from '@/components/shared/DropZone';
import ImageGrid from '@/components/shared/ImageGrid';
import type { UploadedImage } from '@/lib/types';

export default function Step1Upload() {
  const { state, dispatch } = useWizard();

  // Cleanup Object URLs on unmount
  useEffect(() => {
    return () => {
      state.images.forEach((img) => URL.revokeObjectURL(img.preview));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFiles = useCallback(
    (files: File[]) => {
      const newImages: UploadedImage[] = files.map((file) => ({
        file,
        preview: URL.createObjectURL(file),
        name: file.name,
      }));
      dispatch({ type: 'SET_IMAGES', images: [...state.images, ...newImages].slice(0, 20) });
    },
    [state.images, dispatch],
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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Zdjęcia produktów</CardTitle>
          <p className="text-sm text-muted-foreground">
            Wgraj zdjęcia zlewu, baterii i akcesoriów. Kliknij, aby ustawić główne zdjęcie
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <DropZone onFiles={handleFiles} maxFiles={20 - state.images.length} />
          <ImageGrid
            images={state.images}
            mainIndex={state.mainImageIndex}
            onRemove={handleRemove}
            onSetMain={(i) => dispatch({ type: 'SET_MAIN_IMAGE', index: i })}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Specyfikacja produktu</CardTitle>
          <p className="text-sm text-muted-foreground">
            Wklej opis ze sklepu, dane techniczne lub notatki
          </p>
        </CardHeader>
        <CardContent>
          <Label htmlFor="spec-text" className="sr-only">
            Specyfikacja
          </Label>
          <Textarea
            id="spec-text"
            value={state.specText}
            onChange={(e) => dispatch({ type: 'SET_SPEC_TEXT', text: e.target.value })}
            placeholder="np. Zlew granitowy jednokomorowy z ociekaczem, kolor: czarny, wymiary: 78x50cm..."
            rows={6}
          />
        </CardContent>
      </Card>
    </div>
  );
}
