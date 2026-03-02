import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { api } from '@/lib/api';
import { isMac, pluralPL } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Loader2, CheckCircle } from 'lucide-react';

export default memo(function DownloadButton() {
  const { state, dispatch } = useWizard();
  const [isLoading, setIsLoading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const blobUrlRef = useRef<string | null>(null);
  const handleDownloadRef = useRef<() => void>(() => {});

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  // Ctrl/Cmd+D shortcut to download
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        handleDownloadRef.current();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  const handleDownload = useCallback(async () => {
    if (!state.jobId || isLoading) return;

    setIsLoading(true);
    try {
      const blob = await api.downloadZip(state.jobId);
      // Revoke previous blob URL before creating new one
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;
      const category = state.resultSections?.category?.toLowerCase().replace(/\s+/g, '-') || 'produkt';
      const dateStr = new Date().toISOString().slice(0, 10);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${category}-${dateStr}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setDownloaded(true);
      toast.success('Plik ZIP pobrany', { id: 'zip-downloaded' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Nie udało się pobrać pliku ZIP';
      toast.error(message, { id: 'zip-error' });
      dispatch({ type: 'SET_ERROR', error: message });
    } finally {
      setIsLoading(false);
    }
  }, [state.jobId, isLoading, state.resultSections, dispatch]);

  // Keep ref in sync for keyboard shortcut
  handleDownloadRef.current = handleDownload;

  const imageCount = state.resultImages.length;
  const shortcutKey = isMac ? '⌘D' : 'Ctrl+D';

  return (
    <Card className={`transition-colors duration-300 ${downloaded ? 'border-green-500/20 bg-green-500/5' : 'border-primary/20 hover:border-primary/40'}`}>
      <CardContent className="pt-6 space-y-3">
        <Button
          size="lg"
          className={`w-full gap-2 h-12 text-base ${downloaded ? 'bg-green-600 hover:bg-green-700' : 'animate-pulse-glow'}`}
          onClick={handleDownload}
          disabled={isLoading || !state.jobId}
          aria-busy={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : downloaded ? (
            <CheckCircle className="h-5 w-5" />
          ) : (
            <Download className="h-5 w-5" />
          )}
          {isLoading ? 'Pobieranie...' : downloaded ? 'Pobierz ponownie' : `Pobierz wszystko (ZIP)`}
        </Button>
        <div className="flex items-center justify-center gap-2 text-[11px] text-muted-foreground/60 flex-wrap" aria-label="Zawartość paczki ZIP" role="group">
          {imageCount > 0 && (
            <>
              <span>{imageCount} {pluralPL(imageCount, 'grafika', 'grafiki', 'grafik')} (PNG/WebP)</span>
              <span className="h-3 w-px bg-border hidden sm:block" aria-hidden="true" />
            </>
          )}
          <span>Opis HTML</span>
          <span className="h-3 w-px bg-border hidden sm:block" aria-hidden="true" />
          <span>Cechy CSV</span>
          <span className="h-3 w-px bg-border hidden sm:block" aria-hidden="true" />
          <span>Allegro-ready</span>
          <span className="h-3 w-px bg-border hidden sm:block" aria-hidden="true" />
          <kbd className="hidden sm:inline px-1.5 py-0.5 rounded bg-muted/50 border border-border/30 font-mono text-[10px] text-muted-foreground/50">{shortcutKey}</kbd>
        </div>
      </CardContent>
    </Card>
  );
});
