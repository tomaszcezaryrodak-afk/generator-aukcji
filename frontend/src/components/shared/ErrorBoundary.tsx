import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { copyToClipboard } from '@/lib/utils';
import { AlertTriangle, RotateCcw, RefreshCw, Copy, Check } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  copied: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, copied: false };
  private copyTimer: ReturnType<typeof setTimeout> | null = null;

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, copied: false };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  componentWillUnmount() {
    if (this.copyTimer) clearTimeout(this.copyTimer);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, copied: false });
  };

  handleCopyError = async () => {
    const msg = this.state.error?.message || 'Unknown error';
    const stack = this.state.error?.stack || '';
    const text = `Error: ${msg}\n\n${stack}`;
    const ok = await copyToClipboard(text);
    if (ok) {
      this.setState({ copied: true });
      if (this.copyTimer) clearTimeout(this.copyTimer);
      this.copyTimer = setTimeout(() => this.setState({ copied: false }), 2000);
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-5 p-8" role="alert">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 animate-check-bounce">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
          <div className="text-center">
            <h2 className="text-lg font-semibold">Coś poszło nie tak</h2>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Aplikacja napotkała nieoczekiwany błąd. Spróbuj odświeżyć stronę.
            </p>
          </div>
          {this.state.error?.message && (
            <details className="w-full max-w-md rounded-lg border border-border">
              <summary className="cursor-pointer px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">
                Szczegóły błędu
              </summary>
              <div className="border-t border-border p-4">
                <pre className="overflow-auto text-xs text-muted-foreground font-mono whitespace-pre-wrap">
                  {this.state.error.message}
                </pre>
              </div>
            </details>
          )}
          <div className="flex gap-3">
            <Button onClick={this.handleReset} className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Spróbuj ponownie
            </Button>
            <Button variant="outline" onClick={() => window.location.reload()} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Odśwież stronę
            </Button>
            {this.state.error?.message && (
              <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-muted-foreground" onClick={this.handleCopyError} aria-label="Kopiuj szczegóły błędu">
                {this.state.copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
                {this.state.copied ? 'Skopiowano' : 'Kopiuj błąd'}
              </Button>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground/40 max-w-md text-center">
            Jeśli problem się powtarza, odśwież stronę lub skontaktuj się z administratorem.
            Postęp analizy jest zapisany automatycznie.
          </p>
          <p className="text-[9px] text-muted-foreground/30 font-mono">v4.3.3</p>
        </div>
      );
    }

    return this.props.children;
  }
}
