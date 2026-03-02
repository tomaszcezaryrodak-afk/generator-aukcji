import { useState, useRef, useEffect, useCallback, memo } from 'react';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';
import { Send, Undo2, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const SUGGESTIONS_DESCRIPTION_EMPTY = ['Wygeneruj opis produktu', 'Krótki opis pod Allegro', 'Opis z tabelą parametrów'] as const;
const SUGGESTIONS_DESCRIPTION = ['Dodaj więcej o materiale', 'Dodaj tabelę parametrów', 'Krótszy opis', 'Dodaj info o gwarancji'] as const;
const SUGGESTIONS_IMAGE = ['Jaśniejsze oświetlenie', 'Cieplejsze kolory', 'Usuń tło', 'Dodaj cień'] as const;

interface ChatPanelProps {
  mode: 'description' | 'image';
  imageKey?: string;
}

export default memo(function ChatPanel({ mode, imageKey }: ChatPanelProps) {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input on mount
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 200);
    return () => clearTimeout(timer);
  }, []);

  // Ctrl+Z to undo last description change (ref to avoid hook ordering issues)
  const handleUndoRef = useRef<() => void>(() => {});
  useEffect(() => {
    if (mode !== 'description') return;
    const handleKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        const target = e.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
        e.preventDefault();
        handleUndoRef.current();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [mode]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.chatMessages.length]);

  const handleSend = useCallback(async (directMessage?: string) => {
    const message = (directMessage ?? input).trim();
    if (!message || !sessionId || isBusy) return;

    setInput('');
    setIsBusy(true);

    dispatch({
      type: 'ADD_CHAT_MESSAGE',
      message: { role: 'user', content: message, timestamp: Date.now() },
    });

    try {
      let res: Record<string, unknown>;
      if (mode === 'description') {
        res = (await api.editDescription(sessionId, message)) as Record<string, unknown>;
        if (res.html) {
          dispatch({ type: 'SET_DESCRIPTION', html: res.html as string });
        }
      } else if (imageKey) {
        res = (await api.editImage(sessionId, imageKey, message)) as Record<string, unknown>;
        if (res.url) {
          const existing = state.resultImages.find((img) => img.key === imageKey);
          dispatch({
            type: 'UPDATE_RESULT_IMAGE',
            key: imageKey,
            image: {
              url: res.url as string,
              key: imageKey,
              type: existing?.type || 'lifestyle',
              label: (res.label as string) || existing?.label || '',
            },
          });
        }
      }

      dispatch({
        type: 'ADD_CHAT_MESSAGE',
        message: { role: 'assistant', content: 'Gotowe', timestamp: Date.now() },
      });
    } catch (err) {
      dispatch({
        type: 'ADD_CHAT_MESSAGE',
        message: {
          role: 'assistant',
          content: `Błąd: ${(err as Error).message}`,
          timestamp: Date.now(),
        },
      });
    } finally {
      setIsBusy(false);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [input, sessionId, isBusy, mode, imageKey, state.resultImages, dispatch]);

  const handleUndo = useCallback(async () => {
    if (!sessionId || mode !== 'description') return;
    setIsBusy(true);
    try {
      const res = (await api.undoDescription(sessionId)) as Record<string, unknown>;
      if (res.html) {
        dispatch({ type: 'SET_DESCRIPTION', html: res.html as string });
      }
    } catch (err) {
      dispatch({
        type: 'ADD_CHAT_MESSAGE',
        message: {
          role: 'assistant',
          content: `Błąd cofania: ${(err as Error).message}`,
          timestamp: Date.now(),
        },
      });
    } finally {
      setIsBusy(false);
    }
  }, [sessionId, mode, dispatch]);

  // Keep undo ref in sync for keyboard shortcut
  handleUndoRef.current = handleUndo;

  return (
    <div className="space-y-3" aria-busy={isBusy}>
      {state.chatMessages.length > 0 ? (
        <div className="relative max-h-48 space-y-2 overflow-y-auto overscroll-contain rounded-lg bg-muted/10 p-3" aria-live="polite" aria-label="Historia rozmowy">
          {state.chatMessages.length > 2 && (
            <button
              type="button"
              className="absolute top-2 right-2 z-10 rounded-md p-1 text-muted-foreground/40 touch-manipulation hover:text-muted-foreground hover:bg-muted/30 transition-colors"
              onClick={() => dispatch({ type: 'CLEAR_CHAT' })}
              aria-label="Wyczyść czat"
              title="Wyczyść historię"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
          {state.chatMessages.map((msg, i) => (
            <div
              key={`${msg.role}-${msg.timestamp}-${i}`}
              className={cn(
                'max-w-[85%] rounded-xl px-3 py-2 text-sm animate-fade-in-up',
                msg.role === 'user'
                  ? 'ml-auto bg-primary text-primary-foreground'
                  : 'mr-auto bg-card border border-border text-foreground',
              )}
            >
              {msg.content}
            </div>
          ))}
          {isBusy && (
            <div className="mr-auto flex items-center gap-2 rounded-xl bg-card border border-border px-3 py-2 text-sm text-muted-foreground">
              <div className="flex items-center gap-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-typing-dot" />
                <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-typing-dot" style={{ animationDelay: '0.15s' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-typing-dot" style={{ animationDelay: '0.3s' }} />
              </div>
              Przetwarzanie...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border/50 bg-muted/5 px-3 py-4 space-y-2.5">
          <p className="text-xs text-muted-foreground text-center">
            {mode === 'description'
              ? (state.descriptionHtml ? 'Opisz zmiany w opisie produktu' : 'Wygeneruj opis lub wybierz sugestię')
              : 'Opisz poprawki do obrazu'}
          </p>
          <div className="flex flex-wrap justify-center gap-1.5" role="group" aria-label="Szybkie sugestie">
            {(mode === 'description'
              ? (state.descriptionHtml ? SUGGESTIONS_DESCRIPTION : SUGGESTIONS_DESCRIPTION_EMPTY)
              : SUGGESTIONS_IMAGE
            ).map((suggestion, i) => (
              <button
                key={suggestion}
                type="button"
                className="rounded-md border border-border bg-card px-2 py-1 text-[11px] text-muted-foreground touch-manipulation hover:bg-primary/5 hover:text-foreground hover:border-primary/30 transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:pointer-events-none animate-chip-in"
                disabled={isBusy}
                onClick={() => { handleSend(suggestion); }}
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="space-y-1">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, 500))}
            placeholder={
              mode === 'description'
                ? (state.descriptionHtml
                    ? 'Zmień opis, np. dodaj więcej o materiale...'
                    : 'Napisz czego oczekujesz od opisu...')
                : 'Popraw obraz, np. jaśniejsze oświetlenie...'
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.nativeEvent.isComposing) handleSend();
              if (e.key === 'Escape' && input.trim()) {
                e.preventDefault();
                setInput('');
              }
            }}
            disabled={isBusy}
            className="h-10"
            autoComplete="off"
            enterKeyHint="send"
            aria-label="Wiadomość czatu"
            maxLength={500}
          />
          <Button
            size="icon"
            className="h-10 w-10 shrink-0"
            onClick={() => { handleSend(); }}
            disabled={isBusy || !input.trim()}
            aria-label="Wyślij"
          >
            <Send className="h-4 w-4" />
          </Button>
          {mode === 'description' && (
            <Button
              variant="outline"
              size="icon"
              className="h-10 w-10 shrink-0"
              onClick={handleUndo}
              disabled={isBusy}
              aria-label="Cofnij ostatnią zmianę"
            >
              <Undo2 className="h-4 w-4" />
            </Button>
          )}
        </div>
        <div className="flex items-center justify-between">
          {input.trim() ? (
            <p className="text-[10px] text-muted-foreground/40 hidden md:flex md:items-center md:gap-0.5">
              <kbd className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[9px]">Enter</kbd>
              <span>aby wysłać</span>
            </p>
          ) : <span />}
          {input.length > 300 && (
            <p className={`text-[10px] tabular-nums ${input.length >= 450 ? 'text-destructive' : 'text-muted-foreground/50'}`}>
              {input.length}/500
            </p>
          )}
        </div>
      </div>
    </div>
  );
});
