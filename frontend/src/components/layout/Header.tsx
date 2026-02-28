import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { useWizard } from '@/context/WizardContext';
import { formatPLN } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import ProviderStatus from '@/components/generation/ProviderStatus';
import { LogOut } from 'lucide-react';

export default function Header() {
  const { logout } = useAuth();
  const { state } = useWizard();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold">Generator Aukcji</h1>
          {state.totalCost > 0 && (
            <Badge
              variant="secondary"
              className="font-mono text-xs"
              aria-label={`Koszt generowania: ${formatPLN(state.totalCost)}`}
            >
              {formatPLN(state.totalCost)}
            </Badge>
          )}
          <ProviderStatus />
        </div>
        <Button variant="ghost" size="icon" onClick={() => { logout(); toast.info('Wylogowano'); }} aria-label="Wyloguj">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
