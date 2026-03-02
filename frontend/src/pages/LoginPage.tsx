import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { pluralPL } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Loader2, Eye, EyeOff } from 'lucide-react';

const MAX_ATTEMPTS = 5;
const LOCKOUT_MS = 30_000;

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const [lockoutSeconds, setLockoutSeconds] = useState(0);
  const lockoutTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  // Persistent lockout state (survives F5)
  const getAttempts = () => Number(sessionStorage.getItem('login_attempts') || '0');
  const setAttempts = (n: number) => sessionStorage.setItem('login_attempts', String(n));
  const getLockoutUntil = () => Number(sessionStorage.getItem('lockout_until') || '0');
  const setLockoutUntil = (ts: number) => sessionStorage.setItem('lockout_until', String(ts));
  const clearLockout = () => {
    sessionStorage.removeItem('login_attempts');
    sessionStorage.removeItem('lockout_until');
  };

  const isLocked = lockoutSeconds > 0;

  // Restore lockout state on mount (handles F5 during lockout)
  useEffect(() => {
    const until = getLockoutUntil();
    if (until > Date.now()) {
      const remainMs = until - Date.now();
      setLockoutSeconds(Math.ceil(remainMs / 1000));
      setError('Zbyt wiele prób');
      countdownTimer.current = setInterval(() => {
        const left = getLockoutUntil() - Date.now();
        if (left <= 0) {
          if (countdownTimer.current) clearInterval(countdownTimer.current);
          setLockoutSeconds(0);
          clearLockout();
          setError('');
          setPassword('');
          requestAnimationFrame(() => passwordRef.current?.focus());
          return;
        }
        setLockoutSeconds(Math.ceil(left / 1000));
      }, 1000);
    } else if (until > 0) {
      clearLockout();
    }
    return () => {
      if (lockoutTimer.current) clearTimeout(lockoutTimer.current);
      if (countdownTimer.current) clearInterval(countdownTimer.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- only on mount
  }, []);

  useEffect(() => {
    document.title = 'Logowanie · Generator Aukcji';
  }, []);

  useEffect(() => {
    if (isAuthenticated) navigate('/wizard', { replace: true });
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) {
    return (
      <div className="min-h-dvh flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!password.trim() || isLocked) return;

    setIsLoading(true);
    setError('');

    try {
      await login(password);
      clearLockout();
      toast.success('Zalogowano', { id: 'login-success' });
      navigate('/wizard', { replace: true });
    } catch {
      const current = getAttempts() + 1;
      setAttempts(current);
      setShakeKey((k) => k + 1);
      if (current >= MAX_ATTEMPTS) {
        const until = Date.now() + LOCKOUT_MS;
        setLockoutUntil(until);
        setLockoutSeconds(Math.ceil(LOCKOUT_MS / 1000));
        setError('Zbyt wiele prób');
        if (countdownTimer.current) clearInterval(countdownTimer.current);
        countdownTimer.current = setInterval(() => {
          const left = getLockoutUntil() - Date.now();
          if (left <= 0) {
            if (countdownTimer.current) clearInterval(countdownTimer.current);
            setLockoutSeconds(0);
            clearLockout();
            setError('');
            setPassword('');
            requestAnimationFrame(() => passwordRef.current?.focus());
            return;
          }
          setLockoutSeconds(Math.ceil(left / 1000));
        }, 1000);
      } else {
        const remaining = MAX_ATTEMPTS - current;
        setError(remaining <= 2 ? `Nieprawidłowe hasło (${remaining} ${pluralPL(remaining, 'próba', 'próby', 'prób')})` : 'Nieprawidłowe hasło');
        setPassword('');
        requestAnimationFrame(() => passwordRef.current?.focus());
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex flex-col items-center justify-center p-4" style={{ backgroundImage: "radial-gradient(ellipse at top, oklch(0.95 0.02 75), oklch(0.97 0.012 85)), url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23a0855a' fill-opacity='0.02'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }}>
      <Card key={shakeKey} className={`w-full max-w-sm shadow-lg ${shakeKey > 0 && error ? 'animate-shake' : 'animate-fade-in-up'}`}>
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 shadow-sm transition-all duration-300 hover:scale-105 hover:shadow-md hover:bg-primary/15 animate-gentle-float">
            <span className="text-xl font-bold tracking-tight text-primary select-none">GZ</span>
          </div>
          <CardTitle className="text-lg">Generator Aukcji</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">Granitowe Zlewy</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="password">Hasło</Label>
              <div className="relative">
                <Input
                  ref={passwordRef}
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  autoCapitalize="off"
                  spellCheck={false}
                  enterKeyHint="go"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Wpisz hasło"
                  autoFocus
                  maxLength={128}
                  className="h-11 pr-10"
                  aria-invalid={!!error}
                  aria-describedby={error ? 'login-error' : undefined}
                />
                <button
                  type="button"
                  className="absolute right-0 top-0 flex h-11 w-10 items-center justify-center text-muted-foreground touch-manipulation hover:text-foreground transition-colors"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ukryj hasło' : 'Pokaż hasło'}
                  aria-pressed={showPassword}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            {error && (
              <p id="login-error" className="text-sm text-destructive animate-fade-in-up" role="alert">
                {error}{isLocked && lockoutSeconds > 0 && (
                  <span className="font-mono tabular-nums"> · {lockoutSeconds}s</span>
                )}
              </p>
            )}
            <Button
              type="submit"
              className="w-full h-11 gap-2"
              disabled={isLoading || isLocked || !password.trim()}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? 'Logowanie...' : 'Zaloguj'}
            </Button>
          </form>
        </CardContent>
      </Card>
      <p className="mt-6 text-[11px] text-muted-foreground/50 select-none" aria-hidden="true">
        Wewnętrzne narzędzie · v4.3.3 · Dostęp tylko dla uprawnionych
      </p>
    </div>
  );
}
