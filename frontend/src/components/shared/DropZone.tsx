import { useCallback, useEffect, useRef, useState, memo } from 'react';
import { toast } from 'sonner';
import { cn, isMac, pluralPL, compressImages } from '@/lib/utils';
import { Upload, CheckCircle, Camera } from 'lucide-react';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB (sync z backend)

function processFiles(files: File[], maxFiles: number): { valid: File[]; rejectedCount: number; overflowCount: number } {
  const all = files.filter((f) => f.type.startsWith('image/'));
  const tooLarge = all.filter((f) => f.size > MAX_FILE_SIZE);
  const nonImage = files.length - all.length;
  const eligible = all.filter((f) => f.size <= MAX_FILE_SIZE);
  const overflowCount = Math.max(0, eligible.length - maxFiles);
  const valid = eligible.slice(0, maxFiles);
  return { valid, rejectedCount: nonImage + tooLarge.length, overflowCount };
}

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  maxFiles?: number;
  disabled?: boolean;
}

/** Detect touch-capable device (mobile/tablet) */
const isTouchDevice = typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0);

export default memo(function DropZone({ onFiles, accept = 'image/*', maxFiles = 20, disabled }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const cameraRef = useRef<HTMLInputElement | null>(null);
  const successTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dragCounter = useRef(0);

  // Cleanup success timer on unmount
  useEffect(() => {
    return () => {
      if (successTimer.current) clearTimeout(successTimer.current);
    };
  }, []);

  const handleSuccess = (count: number) => {
    setShowSuccess(true);
    toast.success(`Dodano ${count} ${pluralPL(count, 'zdjęcie', 'zdjęcia', 'zdjęć')}`, { id: 'dropzone-success' });
    if (successTimer.current) clearTimeout(successTimer.current);
    successTimer.current = setTimeout(() => setShowSuccess(false), 1500);
  };

  const [isCompressing, setIsCompressing] = useState(false);

  const processAndNotify = useCallback(async (files: File[]) => {
    const { valid, rejectedCount, overflowCount } = processFiles(files, maxFiles);
    if (rejectedCount > 0) toast.warning(`Pominięto ${rejectedCount} ${pluralPL(rejectedCount, 'plik', 'pliki', 'plików')} (max 10 MB, tylko obrazy)`, { id: 'dropzone-rejected' });
    if (overflowCount > 0) toast.info(`Dodano ${valid.length} z ${valid.length + overflowCount} (limit: ${maxFiles})`, { id: 'dropzone-overflow' });
    if (valid.length === 0) return;

    // Compress large images client-side (>2MB → resize to max 2048px, strip EXIF)
    const needsCompression = valid.some((f) => f.size > 2 * 1024 * 1024);
    let processed = valid;
    if (needsCompression) {
      setIsCompressing(true);
      try {
        processed = await compressImages(valid);
        const savedBytes = valid.reduce((s, f) => s + f.size, 0) - processed.reduce((s, f) => s + f.size, 0);
        if (savedBytes > 100_000) {
          toast.info(`Zoptymalizowano: -${(savedBytes / (1024 * 1024)).toFixed(1)} MB`, { id: 'compression-info', duration: 3000 });
        }
      } finally {
        setIsCompressing(false);
      }
    }

    onFiles(processed);
    handleSuccess(processed.length);
  }, [onFiles, maxFiles]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;
      void processAndNotify(Array.from(e.dataTransfer.files));
    },
    [processAndNotify, disabled],
  );

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      void processAndNotify(Array.from(e.target.files || []));
      e.target.value = '';
    },
    [processAndNotify],
  );

  // Clipboard paste support (Ctrl+V)
  useEffect(() => {
    if (disabled) return;
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const files: File[] = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) files.push(file);
        }
      }
      if (files.length === 0) return;
      e.preventDefault();
      void processAndNotify(files);
    };
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [processAndNotify, disabled]);

  return (
    <div
      className={cn(
        'relative flex min-h-[180px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 touch-manipulation transition-all duration-300',
        isDragOver && 'border-primary bg-primary/5 scale-[1.02] shadow-lg ring-4 ring-primary/10',
        showSuccess && 'border-green-500 bg-green-500/10',
        !isDragOver && !showSuccess && 'border-border hover:border-primary/40 hover:bg-primary/[0.02]',
        disabled && 'pointer-events-none opacity-50',
      )}
      onDragEnter={(e) => {
        e.preventDefault();
        dragCounter.current += 1;
        setIsDragOver(true);
      }}
      onDragOver={(e) => {
        e.preventDefault();
      }}
      onDragLeave={() => {
        dragCounter.current -= 1;
        if (dragCounter.current <= 0) {
          dragCounter.current = 0;
          setIsDragOver(false);
        }
      }}
      onDrop={(e) => {
        dragCounter.current = 0;
        handleDrop(e);
      }}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="Przeciągnij zdjęcia lub kliknij, aby wybrać"
      aria-disabled={disabled || undefined}
    >
      <div className={cn(
        'mb-3 flex h-12 w-12 items-center justify-center rounded-xl transition-all duration-300',
        showSuccess ? 'bg-green-500/15' : 'bg-primary/8',
        isDragOver && 'scale-110',
      )}>
        {showSuccess ? (
          <CheckCircle className="h-6 w-6 text-green-600 animate-check-bounce" />
        ) : (
          <Upload className={cn('h-6 w-6 text-primary transition-transform', isDragOver && 'animate-bounce')} />
        )}
      </div>
      <p className="text-sm font-medium" aria-live="polite">
        {isCompressing ? 'Optymalizuję zdjęcia...' : showSuccess ? 'Dodano' : isDragOver ? 'Upuść tutaj' : 'Przeciągnij zdjęcia tutaj'}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        lub kliknij, aby wybrać {maxFiles > 1 ? `(max ${maxFiles} ${pluralPL(maxFiles, 'plik', 'pliki', 'plików')})` : ''}
      </p>
      <p className="mt-2 text-[11px] text-muted-foreground/60">
        JPG, PNG, WebP · max 10 MB
      </p>
      <p className="mt-1 text-[10px] text-muted-foreground/40 hidden sm:flex sm:items-center sm:gap-1">
        <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">{isMac ? '⌘' : 'Ctrl'}</kbd>
        <span>+</span>
        <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">V</kbd>
        <span>wkleja ze schowka</span>
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={handleInput}
      />
      {/* Hidden camera input for mobile */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleInput}
      />
      {/* Camera button visible only on touch devices */}
      {isTouchDevice && (
        <button
          type="button"
          className="absolute bottom-3 right-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary touch-manipulation transition-all hover:bg-primary/20 hover:scale-110 active:scale-95"
          onClick={(e) => {
            e.stopPropagation();
            cameraRef.current?.click();
          }}
          aria-label="Zrób zdjęcie aparatem"
          tabIndex={disabled ? -1 : 0}
        >
          <Camera className="h-5 w-5" />
        </button>
      )}
    </div>
  );
});
