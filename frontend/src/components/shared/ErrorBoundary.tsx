import { Component, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8">
          <AlertTriangle className="h-12 w-12 text-destructive" />
          <h2 className="text-lg font-semibold">Coś poszło nie tak</h2>
          <p className="max-w-md text-center text-sm text-muted-foreground">
            {this.state.error?.message || 'Nieoczekiwany błąd aplikacji.'}
          </p>
          <div className="flex gap-3">
            <Button onClick={this.handleReset}>Spróbuj ponownie</Button>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Odśwież stronę
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
