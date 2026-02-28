import type { GeneratedImage } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface LiveGalleryProps {
  images: GeneratedImage[];
  expectedCount?: number;
}

export default function LiveGallery({ images, expectedCount = 8 }: LiveGalleryProps) {
  const placeholders = Math.max(0, expectedCount - images.length);

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
      {images.map((img) => (
        <div key={img.key} className="relative overflow-hidden rounded-lg border border-border">
          <img
            src={img.url}
            alt={img.label || img.key}
            className="aspect-square w-full object-cover"
            loading="lazy"
          />
          {img.label && (
            <Badge
              variant="secondary"
              className="absolute bottom-1 left-1 text-[10px] bg-white/90"
            >
              {img.label}
            </Badge>
          )}
          {img.selfCheck && (
            <Badge
              variant={img.selfCheck.score >= 8 ? 'success' : img.selfCheck.score >= 5 ? 'warning' : 'destructive'}
              className="absolute top-1 right-1 text-[10px]"
            >
              {img.selfCheck.score}/10
            </Badge>
          )}
        </div>
      ))}
      {Array.from({ length: placeholders }).map((_, i) => (
        <Skeleton key={`ph-${i}`} className="aspect-square rounded-lg" />
      ))}
    </div>
  );
}
