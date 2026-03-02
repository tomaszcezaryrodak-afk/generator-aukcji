import { memo } from 'react';
import type { UploadedImage } from '@/lib/types';
import { cn, pluralPL, handleGridKeyDown, formatFileSize } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Star } from 'lucide-react';

interface ImageGridProps {
  images: UploadedImage[];
  mainIndex: number;
  onRemove: (index: number) => void;
  onSetMain: (index: number) => void;
}

export default memo(function ImageGrid({ images, mainIndex, onRemove, onSetMain }: ImageGridProps) {
  if (images.length === 0) return null;

  return (
    <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4 md:grid-cols-5" role="group" aria-label={`${images.length} ${pluralPL(images.length, 'zdjęcie', 'zdjęcia', 'zdjęć')}, główne: ${images[mainIndex]?.name || ''}`}>
      {images.map((img, i) => (
        <div
          key={img.name + i}
          className={cn(
            'group relative aspect-square overflow-hidden rounded-lg border-2 cursor-pointer touch-manipulation transition-all duration-200 animate-pop-in',
            i === mainIndex
              ? 'border-primary shadow-md ring-2 ring-primary/15 ring-offset-1'
              : 'border-transparent hover:border-primary/30 hover:shadow-sm hover:-translate-y-0.5',
          )}
          style={{ animationDelay: `${i * 0.03}s` }}
          onClick={() => onSetMain(i)}
          role="button"
          tabIndex={0}
          aria-label={`${img.name}${i === mainIndex ? ' (główne)' : ''}`}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onSetMain(i);
            }
            if (e.key === 'Delete' || e.key === 'Backspace') {
              e.preventDefault();
              onRemove(i);
            }
            handleGridKeyDown(e);
          }}
        >
          <img
            src={img.preview}
            alt={img.name}
            className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
            decoding="async"
            loading={i < 5 ? 'eager' : 'lazy'}
          />
          {i === mainIndex ? (
            <Badge className="absolute bottom-1 left-1 gap-1 text-[10px] shadow-sm" variant="default">
              <Star className="h-2.5 w-2.5" /> Główne
            </Badge>
          ) : (
            <span className="absolute bottom-1 left-1 rounded bg-black/50 px-1 py-0.5 text-[9px] text-white/80 opacity-0 transition-opacity group-hover:opacity-100">
              {formatFileSize(img.file.size)}
            </span>
          )}
          <Button
            variant="destructive"
            size="icon"
            className="absolute right-1 top-1 h-8 w-8 sm:h-6 sm:w-6 opacity-100 sm:opacity-0 transition-all duration-200 sm:group-hover:opacity-100 focus-visible:opacity-100 shadow-sm"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(i);
            }}
            aria-label={`Usuń ${img.name}`}
          >
            <X className="h-3 w-3" />
          </Button>
          {/* Image number (subtle) */}
          {i !== mainIndex && (
            <span className="absolute top-1 left-1 rounded bg-black/40 px-1 py-0.5 text-[9px] text-white/70 font-mono opacity-0 transition-opacity group-hover:opacity-100 sm:group-hover:opacity-100">
              {i + 1}
            </span>
          )}
        </div>
      ))}
    </div>
  );
});
