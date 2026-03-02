import { useEffect, useRef, memo } from 'react';
import { isMac } from '@/lib/utils';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useBodyScrollLock } from '@/hooks/useBodyScrollLock';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const mod = isMac ? '⌘' : 'Ctrl';

const SHORTCUTS = [
  { keys: [`${mod}+Enter`], desc: 'Następny krok', context: 'Kroki 1-4' },
  { keys: ['1', '…', '6'], desc: 'Skocz do ukończonego kroku', context: 'Wszędzie' },
  { keys: ['Enter'], desc: 'Rozpocznij / zaakceptuj fazę', context: 'Krok 5' },
  { keys: [`${mod}+Enter`], desc: 'Wyślij poprawki', context: 'Akceptacja fazy' },
  { keys: [`${mod}+V`], desc: 'Wklej obraz ze schowka', context: 'Krok 1' },
  { keys: [`${mod}+Z`], desc: 'Cofnij zmianę opisu', context: 'Edytor opisu' },
  { keys: [`${mod}+D`], desc: 'Pobierz ZIP', context: 'Krok 6' },
  { keys: ['←', '→', '↑', '↓'], desc: 'Nawigacja w galerii / siatce', context: 'Galerie / Lightbox' },
  { keys: ['Esc'], desc: 'Zamknij podgląd / wyczyść', context: 'Lightbox / Czat' },
  { keys: ['Z'], desc: 'Powiększ/pomniejsz obraz', context: 'Lightbox' },
  { keys: ['D'], desc: 'Pobierz pojedynczy obraz', context: 'Lightbox' },
  { keys: ['?'], desc: 'Pokaż/ukryj skróty', context: 'Wszędzie' },
] as const;

interface KeyboardHelpProps {
  onClose: () => void;
}

export default memo(function KeyboardHelp({ onClose }: KeyboardHelpProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => { closeRef.current?.focus(); }, []);
  useBodyScrollLock();
  useFocusTrap(dialogRef);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === '?') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in-up"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Skróty klawiszowe"
    >
      <div
        className="relative w-full max-w-md mx-4 rounded-xl border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">Skróty klawiszowe</h2>
          <Button
            ref={closeRef}
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onClose}
            aria-label="Zamknij"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="divide-y divide-border/30">
          {SHORTCUTS.map((s, i) => (
            <div key={i} className="flex items-center justify-between gap-3 py-2.5 animate-fade-in-up" style={{ animationDelay: `${i * 0.03}s` }}>
              <div className="flex-1 min-w-0">
                <p className="text-sm">{s.desc}</p>
                <p className="text-[10px] text-muted-foreground/60">{s.context}</p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {s.keys.map((key) => (
                  <kbd
                    key={key}
                    className="rounded-md border border-border bg-muted/30 px-2 py-1 font-mono text-xs text-muted-foreground shadow-sm"
                  >
                    {key}
                  </kbd>
                ))}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-center text-[10px] text-muted-foreground/40">
          Naciśnij <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">?</kbd> lub <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Esc</kbd> aby zamknąć
        </p>
      </div>
    </div>
  );
});
