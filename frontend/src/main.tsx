import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from '@/context/AuthContext';
import '@fontsource-variable/inter';
import App from './App';
import './globals.css';

// Global unhandled rejection handler — prevents silent failures in production
window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason;
  const message = reason instanceof Error ? reason.message : String(reason ?? 'Nieznany błąd');
  // Suppress benign rejections (aborted fetches, cancelled requests)
  if (message.includes('AbortError') || message.includes('abort') || message.includes('cancelled')) return;
  console.error('[unhandledrejection]', reason);
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename="/app">
      <AuthProvider>
        <App />
        <Toaster
          position="bottom-center"
          richColors
          closeButton
          expand
          visibleToasts={3}
          gap={8}
          theme="light"
          offset="60px"
          toastOptions={{ duration: 4000, className: 'text-sm' }}
        />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
