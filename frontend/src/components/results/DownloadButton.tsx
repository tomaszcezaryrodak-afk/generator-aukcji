import { useState } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { useWizard } from '@/context/WizardContext';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Download, Loader2 } from 'lucide-react';

export default function DownloadButton() {
  const { sessionId } = useAuth();
  const { dispatch } = useWizard();
  const [isLoading, setIsLoading] = useState(false);

  const handleDownload = async () => {
    if (!sessionId || isLoading) return;

    setIsLoading(true);
    try {
      const blob = await api.downloadZip(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `grafiki-${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Plik ZIP pobrany');
    } catch {
      toast.error('Nie udało się pobrać pliku ZIP');
      dispatch({ type: 'SET_ERROR', error: 'Nie udało się pobrać pliku ZIP. Spróbuj ponownie.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      size="lg"
      className="w-full gap-2"
      onClick={handleDownload}
      disabled={isLoading || !sessionId}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Download className="h-4 w-4" />
      )}
      {isLoading ? 'Pobieranie...' : 'Pobierz wszystko (ZIP)'}
    </Button>
  );
}
