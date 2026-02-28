import { useState } from 'react';
import { useWizard } from '@/context/WizardContext';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';
import { Send, Undo2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  mode: 'description' | 'image';
  imageKey?: string;
}

export default function ChatPanel({ mode, imageKey }: ChatPanelProps) {
  const { state, dispatch } = useWizard();
  const { sessionId } = useAuth();
  const [input, setInput] = useState('');
  const [isBusy, setIsBusy] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || isBusy) return;

    const message = input.trim();
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
        if (res.description_html) {
          dispatch({ type: 'SET_DESCRIPTION', html: res.description_html as string });
        }
      } else if (imageKey) {
        res = (await api.editImage(sessionId, imageKey, message)) as Record<string, unknown>;
        if (res.url) {
          dispatch({
            type: 'UPDATE_RESULT_IMAGE',
            key: imageKey,
            image: {
              url: res.url as string,
              key: imageKey,
              type: 'lifestyle',
              label: res.label as string || '',
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
    }
  };

  const handleUndo = async () => {
    if (!sessionId || mode !== 'description') return;
    setIsBusy(true);
    try {
      const res = (await api.undoDescription(sessionId)) as Record<string, unknown>;
      if (res.description_html) {
        dispatch({ type: 'SET_DESCRIPTION', html: res.description_html as string });
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
  };

  return (
    <div className="space-y-3">
      <div className="max-h-48 space-y-2 overflow-auto" aria-live="polite" aria-label="Historia rozmowy">
        {state.chatMessages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              'max-w-[85%] rounded-xl px-3 py-2 text-sm',
              msg.role === 'user'
                ? 'ml-auto bg-primary text-primary-foreground'
                : 'mr-auto bg-muted/30 text-foreground',
            )}
          >
            {msg.content}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            mode === 'description'
              ? 'Zmień opis, np. dodaj więcej o materiale...'
              : 'Popraw obraz, np. jaśniejsze oświetlenie...'
          }
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={isBusy}
          aria-label="Wiadomość czatu"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={isBusy || !input.trim()}
          aria-label="Wyślij"
        >
          <Send className="h-4 w-4" />
        </Button>
        {mode === 'description' && (
          <Button
            variant="outline"
            size="icon"
            onClick={handleUndo}
            disabled={isBusy}
            aria-label="Cofnij ostatnią zmianę"
          >
            <Undo2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
