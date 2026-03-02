import { memo } from 'react';
import type { GeneratedImage } from '@/lib/types';
import { handleImgError, handleGridKeyDown } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface LiveGalleryProps {
  images: GeneratedImage[];
  expectedCount?: number;
  onImageClick?: (index: number) => void;
}

export default memo(function LiveGallery({ images, expectedCount = 8, onImageClick }: LiveGalleryProps) {
  const placeholders = Math.max(0, expectedCount - images.length);

  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4" role="group" aria-label={`Wygenerowane grafiki: ${images.length} z ${expectedCount || '?'}`}>
      {images.map((img, i) => (
        <div
          key={img.key}
          className={`group relative overflow-hidden rounded-lg border border-border shadow-sm animate-pop-in transition-all duration-200 hover:shadow-md ${onImageClick ? 'cursor-pointer hover:border-primary/30 hover:-translate-y-0.5' : ''}`}
          style={{ animationDelay: `${i * 0.08}s` }}
          role={onImageClick ? 'button' : undefined}
          tabIndex={onImageClick ? 0 : undefined}
          onClick={onImageClick ? () => onImageClick(i) : undefined}
          onKeyDown={onImageClick ? (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onImageClick(i); return; }
            handleGridKeyDown(e);
          } : undefined}
          aria-label={onImageClick ? `Powiększ: ${img.label || img.key}` : undefined}
        >
          <img
            src={img.url}
            alt={img.label || img.key}
            className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
            decoding="async"
            onError={handleImgError}
          />
          {img.type && (
            <span className={`absolute bottom-1 right-1 rounded-md px-1.5 py-0.5 text-[9px] font-medium shadow-sm ${
              img.type === 'packshot' ? 'bg-blue-500/80 text-white' : img.type === 'composite' ? 'bg-purple-500/80 text-white' : 'bg-emerald-500/80 text-white'
            }`}>
              {img.type === 'packshot' ? 'Pack' : img.type === 'composite' ? 'Komp' : 'Life'}
            </span>
          )}
          {img.label && (
            <Badge
              variant="secondary"
              className="absolute bottom-1 left-1 text-[10px] bg-card/90 shadow-sm truncate max-w-[calc(100%-3rem)]"
            >
              {img.label}
            </Badge>
          )}
          <span className="absolute top-1 left-1 rounded bg-black/40 px-1 py-0.5 text-[9px] text-white/70 font-mono tabular-nums">
            {i + 1}
          </span>
          {img.selfCheck && (
            <Badge
              variant={img.selfCheck.score >= 8 ? 'success' : img.selfCheck.score >= 5 ? 'warning' : 'destructive'}
              className="absolute top-1 right-1 text-[10px] shadow-sm"
            >
              {img.selfCheck.score}/10
            </Badge>
          )}
        </div>
      ))}
      {Array.from({ length: placeholders }).map((_, i) => (
        <div key={`ph-${i}`} className="relative aspect-square rounded-lg border border-dashed border-border/50 bg-muted/20 flex items-center justify-center" role="status" aria-label="Generowanie obrazu...">
          <div className="h-6 w-6 rounded-full border-2 border-muted-foreground/20 border-t-primary/40 animate-spin" />
        </div>
      ))}
    </div>
  );
});
