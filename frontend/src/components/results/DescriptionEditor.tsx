import { useState, useCallback, useRef, useEffect, useMemo, memo } from 'react';
import { toast } from 'sonner';
import { useWizard } from '@/context/WizardContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ChatPanel from '@/components/results/ChatPanel';
import { copyToClipboard } from '@/lib/utils';
import { useCopyFeedback } from '@/hooks/useCopyFeedback';
import { FileText, Copy, Check, Code, Eye, FileDown } from 'lucide-react';

function stripHtmlTags(html: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  return doc.body.textContent || '';
}

export default memo(function DescriptionEditor() {
  const { state } = useWizard();
  const { copied, trigger: triggerCopy } = useCopyFeedback();
  const [showSource, setShowSource] = useState(false);

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const html = state.descriptionHtml || '';
  const hasContent = html.length > 0;
  const plainText = hasContent ? stripHtmlTags(html) : '';

  // Stable key to force iframe remount when content changes (fixes auto-resize after chat edits)
  const iframeKey = useMemo(() => {
    if (!html) return 0;
    let hash = 0;
    for (let i = 0; i < Math.min(html.length, 200); i++) {
      hash = ((hash << 5) - hash + html.charCodeAt(i)) | 0;
    }
    return hash ^ html.length;
  }, [html]);

  // Auto-resize iframe to content height
  useEffect(() => {
    if (!hasContent || showSource) return;
    const iframe = iframeRef.current;
    if (!iframe) return;

    const handleLoad = () => {
      try {
        const doc = iframe.contentDocument;
        if (doc?.body) {
          const height = Math.min(Math.max(doc.body.scrollHeight + 16, 120), 480);
          iframe.style.height = `${height}px`;
        }
      } catch {
        // sandbox restriction
      }
    };

    iframe.addEventListener('load', handleLoad);
    return () => iframe.removeEventListener('load', handleLoad);
  }, [iframeKey, hasContent, showSource]);

  const handleCopy = useCallback(async () => {
    if (!hasContent) return;
    try {
      if (showSource) {
        const ok = await copyToClipboard(html);
        toast[ok ? 'success' : 'error'](ok ? 'HTML skopiowany' : 'Nie udało się skopiować', { id: 'desc-copied' });
        if (!ok) return;
      } else {
        // Try rich HTML copy first, then fall back to plain text
        let success = false;
        try {
          if (navigator.clipboard?.write) {
            await navigator.clipboard.write([
              new ClipboardItem({
                'text/html': new Blob([html], { type: 'text/html' }),
                'text/plain': new Blob([plainText], { type: 'text/plain' }),
              }),
            ]);
            toast.success('Skopiowano z formatowaniem', { id: 'desc-copied' });
            success = true;
          }
        } catch {
          // Rich copy failed, fall through
        }
        if (!success) {
          const ok = await copyToClipboard(plainText);
          toast[ok ? 'success' : 'error'](ok ? 'Tekst skopiowany' : 'Nie udało się skopiować', { id: 'desc-copied' });
          if (!ok) return;
        }
      }
      triggerCopy();
    } catch {
      toast.error('Nie udało się skopiować', { id: 'desc-copy-error' });
    }
  }, [html, plainText, hasContent, showSource, triggerCopy]);

  const handleDownloadHtml = useCallback(() => {
    if (!hasContent) return;
    const fullHtml = `<!DOCTYPE html>\n<html lang="pl">\n<head><meta charset="utf-8"><title>Opis produktu</title></head>\n<body>\n${html}\n</body>\n</html>`;
    const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `opis-${new Date().toISOString().slice(0, 10)}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('HTML pobrany', { id: 'html-downloaded' });
  }, [html, hasContent]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4 text-primary" />
            Opis produktu
          </CardTitle>
          {hasContent && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-muted-foreground/50 tabular-nums flex items-center gap-1.5">
                <span className="hidden sm:inline">{plainText.split(/\s+/).filter(Boolean).length} słów · </span>{plainText.length} zn.
                {plainText.length > 0 && (
                  <span className={`hidden sm:inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                    plainText.length >= 1000 && plainText.length <= 4000
                      ? 'bg-green-500/10 text-green-600'
                      : plainText.length > 4000
                        ? 'bg-amber-500/10 text-amber-600'
                        : 'bg-muted/30 text-muted-foreground/60'
                  }`} title="Allegro rekomenduje 1000-4000 znaków opisu">
                    {plainText.length >= 1000 && plainText.length <= 4000 ? '✓ OK' : plainText.length > 4000 ? 'Długi' : `${Math.round(plainText.length / 10)}%`}
                  </span>
                )}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5 text-xs h-8"
                onClick={() => setShowSource(!showSource)}
                aria-label={showSource ? 'Pokaż podgląd' : 'Pokaż źródło HTML'}
              >
                {showSource ? (
                  <Eye className="h-3.5 w-3.5" />
                ) : (
                  <Code className="h-3.5 w-3.5" />
                )}
                {showSource ? 'Podgląd' : 'HTML'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5 text-xs h-8"
                onClick={handleDownloadHtml}
                aria-label="Pobierz opis jako plik HTML"
                title="Pobierz plik HTML"
              >
                <FileDown className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">.html</span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5 text-xs h-8"
                onClick={handleCopy}
                aria-label={showSource ? 'Kopiuj źródło HTML' : 'Kopiuj opis produktu'}
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-green-600" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                {copied ? 'Skopiowano' : showSource ? 'Kopiuj HTML' : 'Kopiuj'}
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {hasContent ? (
          showSource ? (
            <pre className="whitespace-pre-wrap rounded-lg border border-border bg-muted/30 p-4 text-xs leading-relaxed max-h-64 overflow-y-auto overscroll-contain font-mono text-muted-foreground">
              {html}
            </pre>
          ) : (
            <iframe
              key={iframeKey}
              ref={iframeRef}
              srcDoc={`<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data: https:;"><style>body{font-family:'Inter',system-ui,sans-serif;font-size:14px;line-height:1.7;color:#2d2520;margin:0;padding:16px 20px;background:#faf8f5}h1,h2,h3{margin:0.8em 0 0.4em;color:#1a1510}p{margin:0.5em 0}ul,ol{padding-left:1.5em}table{border-collapse:collapse;width:100%}td,th{border:1px solid #e0d9ce;padding:8px 10px;text-align:left}th{background:#f0ebe3;font-weight:600}a{color:#9a7d4a;text-decoration:underline}img{max-width:100%;height:auto;border-radius:4px}strong{color:#1a1510}</style></head><body>${html}</body></html>`}
              className="w-full rounded-lg border border-border bg-background transition-[height] duration-200"
              referrerPolicy="no-referrer"
              style={{ minHeight: '120px', maxHeight: '480px', height: '256px' }}
              sandbox="allow-same-origin"
              title="Podgląd opisu produktu"
            />
          )
        ) : (
          <div className="py-6 text-center">
            <FileText className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
            <p className="text-sm text-muted-foreground">
              Brak opisu. Wygeneruj opis za pomocą czatu
            </p>
          </div>
        )}
        <ChatPanel mode="description" />
      </CardContent>
    </Card>
  );
});
