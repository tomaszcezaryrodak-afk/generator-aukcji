import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
// Lock icon removed - using GZ monogram instead

const MAX_ATTEMPTS = 5;
const LOCKOUT_MS = 30_000;

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const attempts = useRef(0);

  if (isAuthenticated) {
    navigate('/wizard', { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim() || isLocked) return;

    setIsLoading(true);
    setError('');

    try {
      await login(password);
      attempts.current = 0;
      toast.success('Zalogowano');
      navigate('/wizard', { replace: true });
    } catch {
      attempts.current += 1;
      if (attempts.current >= MAX_ATTEMPTS) {
        setIsLocked(true);
        setError(`Zbyt wiele prób. Odczekaj 30 sekund.`);
        setTimeout(() => {
          setIsLocked(false);
          attempts.current = 0;
          setError('');
        }, LOCKOUT_MS);
      } else {
        setError('Nieprawidłowe hasło');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[radial-gradient(ellipse_at_top,oklch(0.95_0.02_75),oklch(0.97_0.012_85))]">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
            <span className="text-xl font-bold tracking-tight text-primary">GZ</span>
          </div>
          <CardTitle className="text-lg">Generator Aukcji</CardTitle>
          <p className="text-sm text-muted-foreground">Granitowe Zlewy</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">Hasło</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Wpisz hasło"
                autoFocus
              />
            </div>
            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" size="lg" disabled={isLoading || isLocked}>
              {isLoading ? 'Logowanie...' : 'Zaloguj'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
