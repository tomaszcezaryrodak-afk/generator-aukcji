import { useState, useEffect, useCallback, useRef, memo } from 'react';
import { toast } from 'sonner';
import type { GeneratedImage } from '@/lib/types';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useBodyScrollLock } from '@/hooks/useBodyScrollLock';
import { Button } from '@/components/ui/button';
import { X, ChevronLeft, ChevronRight, ImageOff, Download } from 'lucide-react';

interface LightboxProps {
  images: GeneratedImage[];
  initialIndex: number;
  onClose: () => void;
}

export default memo(function Lightbox({ images, initialIndex, onClose }: LightboxProps) {
  const [index, setIndex] = useState(initialIndex);
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const handleDownloadRef = useRef<() => void>(() => {});

  const goPrev = useCallback(() => setIndex((i) => (i > 0 ? i - 1 : images.length - 1)), [images.length]);
  const goNext = useCallback(() => setIndex((i) => (i < images.length - 1 ? i + 1 : 0)), [images.length]);

  // Auto-focus close button on mount
  useEffect(() => { closeRef.current?.focus(); }, []);
  useBodyScrollLock();
  useFocusTrap(dialogRef);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
      if (e.key === 'd' || e.key === 'D') handleDownloadRef.current();
      if (e.key === 'z' || e.key === 'Z') setIsZoomed((z) => !z);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose, goPrev, goNext]);

  // Touch/swipe support for mobile
  const touchStartX = useRef<number | null>(null);
  const touchStartY = useRef<number | null>(null);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  }, []);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (touchStartX.current === null || touchStartY.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    const dy = e.changedTouches[0].clientY - touchStartY.current;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);

    // Only handle horizontal swipes (min 50px, more horizontal than vertical)
    if (absDx > 50 && absDx > absDy * 1.5) {
      if (dx > 0) goPrev();
      else goNext();
    }
    touchStartX.current = null;
    touchStartY.current = null;
  }, [goPrev, goNext]);

  const [imgError, setImgError] = useState(false);
  const [imgLoading, setImgLoading] = useState(true);
  const [isZoomed, setIsZoomed] = useState(false);
  const [imgRetry, setImgRetry] = useState(0);

  // Reset error, loading, zoom, and retry on index change
  useEffect(() => { setImgError(false); setImgLoading(true); setIsZoomed(false); setImgRetry(0); }, [index]);

  // Retry once with cache-bust before showing error
  const handleImgErrorLightbox = useCallback(() => {
    setImgRetry((prev) => {
      if (prev === 0) {
        setImgLoading(true);
        return 1;
      }
      setImgError(true);
      setImgLoading(false);
      return prev;
    });
  }, []);

  // Preload adjacent images for smoother navigation
  useEffect(() => {
    if (images.length <= 1) return;
    const preload = (idx: number) => {
      const img = new Image();
      img.src = images[idx].url;
    };
    const prevIdx = index > 0 ? index - 1 : images.length - 1;
    const nextIdx = index < images.length - 1 ? index + 1 : 0;
    preload(prevIdx);
    preload(nextIdx);
  }, [index, images]);

  const current = images[index];
  if (!current) return null;

  const handleDownload = async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30_000);
      let response: Response;
      try {
        response = await fetch(current.url, { signal: controller.signal });
      } finally {
        clearTimeout(timeout);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      try {
        const ext = blob.type.includes('png') ? '.png' : blob.type.includes('webp') ? '.webp' : '.jpg';
        const baseName = (current.label || current.key || 'image').replace(/\.[^.]+$/, '');
        const a = document.createElement('a');
        a.href = url;
        a.download = `${baseName}${ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        toast.success(`Pobrano: ${baseName}${ext}`, { id: 'lightbox-downloaded' });
      } finally {
        URL.revokeObjectURL(url);
      }
    } catch {
      window.open(current.url, '_blank', 'noopener');
    }
  };
  handleDownloadRef.current = handleDownload;

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm animate-fade-in-up touch-pan-x"
      onClick={onClose}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      role="dialog"
      aria-modal="true"
      aria-roledescription="podgląd galerii"
      aria-label={`Podgląd: ${current.label || current.key} (${index + 1} z ${images.length})`}
    >
      <div className="relative max-h-[90vh] max-w-[90vw]" onClick={(e) => e.stopPropagation()} onDoubleClick={() => setIsZoomed((z) => !z)}>
        {imgError ? (
          <div className="flex h-64 w-64 flex-col items-center justify-center gap-3 rounded-lg bg-card/10">
            <ImageOff className="h-12 w-12 text-white/40" />
            <p className="text-sm text-white/60">Nie udało się załadować obrazu</p>
          </div>
        ) : (
          <>
            {imgLoading && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white/80 animate-spin" />
              </div>
            )}
            <img
              key={imgRetry > 0 ? `${current.key}-r${imgRetry}` : current.key}
              src={imgRetry > 0 ? `${current.url}${current.url.includes('?') ? '&' : '?'}_r=${imgRetry}` : current.url}
              alt={current.label || current.key}
              className={`rounded-lg object-contain animate-lightbox-fade transition-all duration-300 cursor-zoom-in ${imgLoading ? 'opacity-0' : 'opacity-100'} ${isZoomed ? 'max-h-none max-w-none scale-150 cursor-zoom-out' : 'max-h-[85vh] max-w-[85vw]'}`}
              fetchPriority="high"
              onLoad={() => setImgLoading(false)}
              onError={handleImgErrorLightbox}
            />
          </>
        )}
        <div className="mt-2 flex items-center justify-center gap-2 text-sm text-white/80" aria-live="polite" aria-atomic="true">
          <span>{current.label || current.type}</span>
          <span className="text-white/30">({index + 1}/{images.length})</span>
          {current.type && (
            <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${current.type === 'packshot' ? 'bg-blue-500/20 text-blue-300' : current.type === 'composite' ? 'bg-purple-500/20 text-purple-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
              {current.type === 'packshot' ? 'Packshot' : current.type === 'composite' ? 'Kompozycja' : 'Lifestyle'}
            </span>
          )}
          {current.selfCheck && (
            <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium tabular-nums ${current.selfCheck.score >= 8 ? 'bg-green-500/20 text-green-300' : current.selfCheck.score >= 5 ? 'bg-amber-500/20 text-amber-300' : 'bg-red-500/20 text-red-300'}`}>
              {current.selfCheck.score}/10
            </span>
          )}
        </div>
      </div>

      {/* Dot indicators */}
      {images.length > 1 && images.length <= 12 && (
        <div className="absolute bottom-12 md:bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-1.5">
          {images.map((_, i) => (
            <button
              key={i}
              type="button"
              className={`h-1.5 rounded-full touch-manipulation transition-all duration-200 ${i === index ? 'w-4 bg-white' : 'w-1.5 bg-white/30 hover:bg-white/50'}`}
              onClick={(e) => { e.stopPropagation(); setIndex(i); }}
              aria-label={`Obraz ${i + 1}`}
            />
          ))}
        </div>
      )}

      {/* Swipe hint for mobile */}
      {images.length > 1 && (
        <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-[11px] text-white/20 md:hidden">
          Przesuń w lewo lub prawo
        </p>
      )}

      {/* Keyboard hints */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 hidden md:flex items-center gap-3 text-[11px] text-white/25">
        <span className="flex items-center gap-1">
          <kbd className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px]">Esc</kbd>
          zamknij
        </span>
        {images.length > 1 && (
          <span className="flex items-center gap-1">
            <kbd className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px]">←</kbd>
            <kbd className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px]">→</kbd>
            nawigacja
          </span>
        )}
        <span className="flex items-center gap-1">
          <kbd className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px]">Z</kbd>
          powiększ
        </span>
        <span className="flex items-center gap-1">
          <kbd className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px]">D</kbd>
          pobierz
        </span>
      </div>

      <div className="absolute right-4 top-4 flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:bg-white/20"
          onClick={(e) => { e.stopPropagation(); handleDownload(); }}
          aria-label={`Pobierz: ${current.label || current.key}`}
        >
          <Download className="h-5 w-5" />
        </Button>
        <Button
          ref={closeRef}
          variant="ghost"
          size="icon"
          className="text-white hover:bg-white/20"
          onClick={onClose}
          aria-label="Zamknij podgląd"
        >
          <X className="h-6 w-6" />
        </Button>
      </div>

      {images.length > 1 && (
        <>
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-4 top-1/2 -translate-y-1/2 text-white hover:bg-white/20 h-12 w-12 rounded-full transition-all duration-200 hover:scale-110"
            onClick={(e) => {
              e.stopPropagation();
              goPrev();
            }}
            aria-label="Poprzedni obraz"
          >
            <ChevronLeft className="h-8 w-8" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-4 top-1/2 -translate-y-1/2 text-white hover:bg-white/20 h-12 w-12 rounded-full transition-all duration-200 hover:scale-110"
            onClick={(e) => {
              e.stopPropagation();
              goNext();
            }}
            aria-label="Następny obraz"
          >
            <ChevronRight className="h-8 w-8" />
          </Button>
        </>
      )}
    </div>
  );
});
