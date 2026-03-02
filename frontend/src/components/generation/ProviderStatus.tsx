import { useEffect, useState, useRef, memo } from 'react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { Badge } from '@/components/ui/badge';

interface ProviderData {
  configured: boolean;
  status: string;
  models: string[];
}

export default memo(function ProviderStatus() {
  const [providers, setProviders] = useState<Record<string, ProviderData> | null>(null);
  const [error, setError] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const prevProviders = useRef<Record<string, ProviderData> | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retryCount = 0;

    const fetchStatus = async () => {
      try {
        const data = (await api.getProviderStatus()) as Record<string, ProviderData>;
        if (!cancelled) {
          // Notify on provider status changes (only after initial load)
          if (prevProviders.current) {
            for (const [name, provider] of Object.entries(data)) {
              const prev = prevProviders.current[name];
              if (prev && prev.status === 'active' && provider.status !== 'active') {
                toast.warning(`${name}: usługa niedostępna`, { id: `provider-${name}` });
              } else if (prev && prev.status !== 'active' && provider.status === 'active') {
                toast.success(`${name}: usługa przywrócona`, { id: `provider-${name}` });
              }
            }
          }
          prevProviders.current = data;
          setProviders(data);
          setLastChecked(new Date());
          setError(false);
          retryCount = 0;
        }
      } catch {
        if (!cancelled) {
          retryCount++;
          // Auto-recover: hide error after 3 failed attempts, retry continues
          if (retryCount >= 3) setError(true);
        }
      }
    };

    fetchStatus();
    const interval = setInterval(() => {
      // Skip polling when tab is hidden to save bandwidth
      if (!document.hidden) fetchStatus();
    }, 30_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (error) return null;

  if (!providers) {
    return (
      <div className="flex items-center gap-1.5" aria-label="Sprawdzanie statusu dostawców">
        <div className="flex gap-1">
          <span className="h-5 w-14 rounded-full bg-muted/40 animate-pulse" />
          <span className="h-5 w-14 rounded-full bg-muted/40 animate-pulse" style={{ animationDelay: '0.1s' }} />
        </div>
      </div>
    );
  }

  const entries = Object.entries(providers);
  const allActive = entries.every(([, p]) => p.status === 'active');

  return (
    <div
      className="flex items-center gap-1.5 animate-fade-in-up"
      role="status"
      aria-label="Status dostawców API"
      title={lastChecked ? `Ostatnie sprawdzenie: ${lastChecked.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })}` : undefined}
    >
      <div className="flex gap-1">
        {entries.map(([name, provider]) => (
          <Badge
            key={name}
            variant={provider.status === 'active' ? 'outline' : 'destructive'}
            className="text-[10px] px-1.5 py-0 font-normal"
            title={provider.models.length > 0 ? `Modele: ${provider.models.join(', ')}` : name}
          >
            <span className={`mr-1 inline-block h-1.5 w-1.5 rounded-full transition-colors ${provider.status === 'active' ? 'bg-green-500 shadow-[0_0_4px_oklch(0.52_0.14_155/0.4)]' : 'bg-red-500 animate-pulse'}`} />
            {name}
          </Badge>
        ))}
      </div>
      {!allActive && (
        <span className="text-[10px] text-destructive">
          Część usług niedostępna
        </span>
      )}
    </div>
  );
});
