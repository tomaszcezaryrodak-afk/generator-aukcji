import { memo } from 'react';
import { AlertCircle, X } from 'lucide-react';

interface InlineAlertProps {
  message: string;
  onDismiss?: () => void;
}

export default memo(function InlineAlert({ message, onDismiss }: InlineAlertProps) {
  return (
    <div
      className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive animate-fade-in-up"
      role="alert"
    >
      <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button
          type="button"
          className="shrink-0 rounded p-0.5 text-destructive/60 touch-manipulation hover:text-destructive transition-colors"
          onClick={onDismiss}
          aria-label="Zamknij komunikat"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
});
