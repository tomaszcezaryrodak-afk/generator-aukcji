import { useCallback, useRef, useState } from 'react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Upload } from 'lucide-react';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB (sync z backend)

function processFiles(files: File[], maxFiles: number): { valid: File[]; rejectedCount: number } {
  const all = files.filter((f) => f.type.startsWith('image/'));
  const tooLarge = all.filter((f) => f.size > MAX_FILE_SIZE);
  const nonImage = files.length - all.length;
  const valid = all.filter((f) => f.size <= MAX_FILE_SIZE).slice(0, maxFiles);
  return { valid, rejectedCount: nonImage + tooLarge.length };
}

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  maxFiles?: number;
  disabled?: boolean;
}

export default function DropZone({ onFiles, accept = 'image/*', maxFiles = 20, disabled }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;

      const { valid, rejectedCount } = processFiles(Array.from(e.dataTransfer.files), maxFiles);
      if (rejectedCount > 0) toast.warning(`Pominięto ${rejectedCount} plików (max 10 MB, tylko obrazy)`);
      if (valid.length > 0) onFiles(valid);
    },
    [onFiles, maxFiles, disabled],
  );

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const { valid, rejectedCount } = processFiles(Array.from(e.target.files || []), maxFiles);
      if (rejectedCount > 0) toast.warning(`Pominięto ${rejectedCount} plików (max 10 MB, tylko obrazy)`);
      if (valid.length > 0) onFiles(valid);
      e.target.value = '';
    },
    [onFiles, maxFiles],
  );

  return (
    <div
      className={cn(
        'relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors',
        isDragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
        disabled && 'pointer-events-none opacity-50',
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label="Przeciągnij zdjęcia lub kliknij, aby wybrać"
    >
      <Upload className="mb-3 h-10 w-10 text-muted-foreground" />
      <p className="text-sm font-medium">Przeciągnij zdjęcia tutaj</p>
      <p className="mt-1 text-xs text-muted-foreground">
        lub kliknij, aby wybrać (max {maxFiles} plików)
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={handleInput}
      />
    </div>
  );
}
