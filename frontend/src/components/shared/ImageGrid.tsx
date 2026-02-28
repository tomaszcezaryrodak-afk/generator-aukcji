import type { UploadedImage } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Star } from 'lucide-react';

interface ImageGridProps {
  images: UploadedImage[];
  mainIndex: number;
  onRemove: (index: number) => void;
  onSetMain: (index: number) => void;
}

export default function ImageGrid({ images, mainIndex, onRemove, onSetMain }: ImageGridProps) {
  if (images.length === 0) return null;

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
      {images.map((img, i) => (
        <div
          key={img.name + i}
          className={cn(
            'group relative aspect-square overflow-hidden rounded-lg border-2 cursor-pointer transition-colors',
            i === mainIndex ? 'border-primary' : 'border-transparent hover:border-primary/30',
          )}
          onClick={() => onSetMain(i)}
        >
          <img
            src={img.preview}
            alt={img.name}
            className="h-full w-full object-cover"
            loading="lazy"
          />
          {i === mainIndex && (
            <Badge className="absolute bottom-1 left-1 gap-1 text-[10px]" variant="default">
              <Star className="h-3 w-3" /> Główne
            </Badge>
          )}
          <Button
            variant="destructive"
            size="icon"
            className="absolute right-0 top-0 h-10 w-10 opacity-100"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(i);
            }}
            aria-label={`Usuń ${img.name}`}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
    </div>
  );
}
