import { useState, useMemo, memo } from 'react';
import type { GeneratedImage } from '@/lib/types';
import { handleImgError, handleGridKeyDown } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import Lightbox from '@/components/shared/Lightbox';
import { Image } from 'lucide-react';

interface ResultGalleryProps {
  images: GeneratedImage[];
  onSelectForEdit?: (key: string) => void;
}

export default memo(function ResultGallery({ images, onSelectForEdit }: ResultGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [filter, setFilter] = useState<'all' | 'packshot' | 'composite' | 'lifestyle'>('all');

  const { packshotCount, compositeCount, lifestyleCount, hasMultipleTypes } = useMemo(() => {
    let p = 0, c = 0, l = 0;
    for (const img of images) {
      if (img.type === 'packshot') p++;
      else if (img.type === 'composite') c++;
      else if (img.type === 'lifestyle') l++;
    }
    const typesPresent = [p, c, l].filter(Boolean).length;
    return { packshotCount: p, compositeCount: c, lifestyleCount: l, hasMultipleTypes: typesPresent >= 2 };
  }, [images]);

  const filtered = useMemo(
    () => filter === 'all' ? images : images.filter((i) => i.type === filter),
    [images, filter],
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Image className="h-4 w-4 text-primary" />
            Galeria
          </CardTitle>
          <Badge variant="secondary" className="font-mono text-xs">
            {filtered.length}{filter !== 'all' ? `/${images.length}` : ''}
          </Badge>
        </div>
        {hasMultipleTypes && (
          <div
            className="flex items-center gap-1 pt-1"
            role="tablist"
            aria-label="Filtruj typ grafik"
            onKeyDown={(e) => {
              if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
              const tabs = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('[role="tab"]'));
              const current = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true');
              if (current < 0) return;
              e.preventDefault();
              const next = e.key === 'ArrowRight'
                ? (current + 1) % tabs.length
                : (current - 1 + tabs.length) % tabs.length;
              tabs[next].click();
              tabs[next].focus();
            }}
          >
            {([
              { key: 'all', label: 'Wszystkie' },
              ...(packshotCount > 0 ? [{ key: 'packshot', label: `Packshoty (${packshotCount})` }] : []),
              ...(compositeCount > 0 ? [{ key: 'composite', label: `Kompozycje (${compositeCount})` }] : []),
              ...(lifestyleCount > 0 ? [{ key: 'lifestyle', label: `Lifestyle (${lifestyleCount})` }] : []),
            ] as { key: typeof filter; label: string }[]).map((f) => (
              <button
                key={f.key}
                type="button"
                role="tab"
                tabIndex={filter === f.key ? 0 : -1}
                aria-selected={filter === f.key}
                aria-controls="result-gallery-grid"
                className={`rounded-md px-2.5 py-1 text-xs font-medium touch-manipulation transition-all duration-200 ${filter === f.key ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted/30 text-muted-foreground hover:bg-muted/50 hover:shadow-sm'}`}
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div id="result-gallery-grid" role="tabpanel" className="grid grid-cols-2 gap-2 sm:gap-2.5 sm:grid-cols-3 md:grid-cols-4">
          {filtered.length === 0 && (
            <div className="col-span-full py-8 text-center animate-fade-in-up">
              <Image className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
              <p className="text-sm text-muted-foreground">
                Brak grafik w tej kategorii
              </p>
            </div>
          )}
          {filtered.map((img, i) => (
            <div
              key={img.key}
              role="button"
              tabIndex={0}
              aria-label={`Podgląd: ${img.label || img.key}`}
              className="group relative cursor-pointer overflow-hidden rounded-lg border border-border touch-manipulation transition-all duration-200 hover:shadow-md hover:border-primary/30 hover:-translate-y-0.5 animate-pop-in"
              style={{ animationDelay: `${i * 0.06}s` }}
              onClick={() => setLightboxIndex(i)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setLightboxIndex(i);
                  return;
                }
                handleGridKeyDown(e);
              }}
            >
              <img
                src={img.url}
                alt={img.label || img.key}
                className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
                loading="lazy"
                decoding="async"
                onError={handleImgError}
              />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-100 sm:opacity-0 transition-opacity duration-200 sm:group-hover:opacity-100">
                <p className="text-xs text-white truncate">{img.label || img.type}</p>
              </div>
              {img.selfCheck && (
                <Badge
                  variant={img.selfCheck.score >= 8 ? 'success' : img.selfCheck.score >= 5 ? 'warning' : 'destructive'}
                  className="absolute right-1 top-1 text-[10px] shadow-sm"
                >
                  {img.selfCheck.score}/10
                </Badge>
              )}
              {onSelectForEdit && (
                <button
                  className="absolute left-1 top-1 rounded-md bg-card/90 px-1.5 py-0.5 text-[10px] font-medium touch-manipulation opacity-100 sm:opacity-0 transition-opacity duration-200 sm:group-hover:opacity-100 hover:bg-card shadow-sm border border-border/30"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectForEdit(img.key);
                  }}
                  aria-label={`Edytuj ${img.label || img.key}`}
                >
                  Edytuj
                </button>
              )}
            </div>
          ))}
        </div>
      </CardContent>
      {lightboxIndex !== null && (
        <Lightbox
          images={filtered}
          initialIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </Card>
  );
});
