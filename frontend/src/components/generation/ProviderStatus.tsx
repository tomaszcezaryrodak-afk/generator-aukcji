import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Activity } from 'lucide-react';

interface ProviderData {
  configured: boolean;
  status: string;
  models: string[];
}

export default function ProviderStatus() {
  const [providers, setProviders] = useState<Record<string, ProviderData> | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const fetchStatus = async () => {
      try {
        const data = (await api.getProviderStatus()) as Record<string, ProviderData>;
        if (!cancelled) setProviders(data);
      } catch {
        if (!cancelled) setError(true);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (error || !providers) return null;

  const entries = Object.entries(providers);
  const allActive = entries.every(([, p]) => p.status === 'active');

  return (
    <div className="flex items-center gap-2">
      <Activity className="h-3.5 w-3.5 text-muted-foreground" />
      <div className="flex gap-1.5">
        {entries.map(([name, provider]) => (
          <Badge
            key={name}
            variant={provider.status === 'active' ? 'success' : 'destructive'}
            className="text-[10px] px-1.5 py-0"
          >
            {name}
          </Badge>
        ))}
      </div>
      {!allActive && (
        <span className="text-[10px] text-destructive">
          Niektóre usługi niedostępne
        </span>
      )}
    </div>
  );
}
