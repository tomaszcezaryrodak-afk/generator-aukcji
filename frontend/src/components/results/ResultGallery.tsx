import { useState } from 'react';
import type { GeneratedImage } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import Lightbox from '@/components/shared/Lightbox';

interface ResultGalleryProps {
  images: GeneratedImage[];
  onSelectForEdit?: (key: string) => void;
}

export default function ResultGallery({ images, onSelectForEdit }: ResultGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {images.map((img, i) => (
          <div
            key={img.key}
            role="button"
            tabIndex={0}
            aria-label={`Podgląd: ${img.label || img.key}`}
            className="group relative cursor-pointer overflow-hidden rounded-lg border border-border transition-shadow hover:shadow-md"
            onClick={() => setLightboxIndex(i)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setLightboxIndex(i);
              }
            }}
          >
            <img
              src={img.url}
              alt={img.label || img.key}
              className="aspect-square w-full object-cover"
              loading="lazy"
            />
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-100 sm:opacity-0 transition-opacity sm:group-hover:opacity-100">
              <p className="text-xs text-white">{img.label || img.type}</p>
            </div>
            {img.selfCheck && (
              <Badge
                variant={img.selfCheck.score >= 8 ? 'success' : 'warning'}
                className="absolute right-1 top-1 text-xs"
              >
                {img.selfCheck.score}/10
              </Badge>
            )}
            {onSelectForEdit && (
              <button
                className="absolute left-1 top-1 rounded bg-white/90 px-1.5 py-0.5 text-[10px] font-medium opacity-100 sm:opacity-0 transition-opacity sm:group-hover:opacity-100"
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
      {lightboxIndex !== null && (
        <Lightbox
          images={images}
          initialIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </>
  );
}
