export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`API Error ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

class ApiClient {
  private token: string | null = null;
  private onUnauthorized: (() => void) | null = null;
  private pendingRequests = new Map<string, Promise<unknown>>();

  setToken(token: string | null) {
    this.token = token;
  }

  getToken() {
    return this.token;
  }

  setOnUnauthorized(cb: (() => void) | null) {
    this.onUnauthorized = cb;
  }

  /** Waliduje czy biezacy token jest wazny (GET /api/session/stats). */
  async validateSession(): Promise<boolean> {
    if (!this.token) return false;
    try {
      await this.request('/api/session/stats');
      return true;
    } catch {
      return false;
    }
  }

  private async request<T>(path: string, options?: RequestInit & { _retries?: number }): Promise<T> {
    // Deduplicate concurrent identical GET requests
    const isGet = !options?.method || options.method === 'GET';
    if (isGet) {
      const pending = this.pendingRequests.get(path);
      if (pending) return pending as Promise<T>;
    }

    const promise = this.executeRequest<T>(path, options);

    if (isGet) {
      this.pendingRequests.set(path, promise);
      promise.finally(() => this.pendingRequests.delete(path));
    }

    return promise;
  }

  private async fetchRaw(
    path: string,
    init?: RequestInit,
    timeoutMs = 30_000,
    timeoutMessage?: string,
  ): Promise<Response> {
    const headers: Record<string, string> = {
      ...((init?.headers as Record<string, string>) || {}),
      'X-Requested-With': 'XMLHttpRequest',
    };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    if (!(init?.body instanceof FormData)) headers['Content-Type'] = 'application/json';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(path, { ...init, headers, signal: controller.signal });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new ApiError(408, timeoutMessage ?? 'Upłynął limit czasu żądania. Spróbuj ponownie.');
      }
      if (err instanceof TypeError) {
        throw new ApiError(0, 'Brak połączenia z serwerem. Sprawdź połączenie sieciowe.');
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  }

  private async parseErrorDetail(res: Response): Promise<string> {
    const body = await res.text();
    try {
      const json = JSON.parse(body);
      if (json.detail) return typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail);
    } catch { /* not JSON */ }
    return body;
  }

  private async executeRequest<T>(path: string, options?: RequestInit & { _retries?: number }): Promise<T> {
    const res = await this.fetchRaw(path, options);

    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) this.onUnauthorized();

      // Auto-retry 5xx (max 2 retries z exponential backoff)
      const retries = options?._retries ?? 0;
      if (res.status >= 500 && retries < 2) {
        await new Promise((r) => setTimeout(r, 1000 * (retries + 1)));
        return this.executeRequest<T>(path, { ...options, _retries: retries + 1 });
      }

      const detail = await this.parseErrorDetail(res);
      let message: string;
      if (res.status === 401) {
        message = 'Sesja wygasła. Zaloguj się ponownie.';
      } else if (res.status === 403) {
        message = 'Brak uprawnień do tej operacji.';
      } else if (res.status === 429) {
        const retryAfter = res.headers.get('Retry-After');
        const secs = retryAfter ? parseInt(retryAfter, 10) : NaN;
        message = !isNaN(secs) && secs > 0
          ? `Zbyt wiele zapytań. Spróbuj za ${secs} s.`
          : 'Zbyt wiele zapytań. Spróbuj za chwilę.';
      } else if (res.status >= 500) {
        message = 'Błąd serwera. Spróbuj ponownie.';
      } else {
        message = detail;
      }
      throw new ApiError(res.status, message);
    }

    const contentType = res.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return res.json();
    }
    return res.text() as unknown as T;
  }

  // Auth
  async login(password: string) {
    return this.request<{ session_id: string; token: string }>('/api/auth', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  }

  // Upload & Analyze (timeout: 120s for large uploads)
  async uploadAndAnalyze(formData: FormData) {
    const res = await this.fetchRaw(
      '/api/analyze',
      { method: 'POST', body: formData },
      120_000,
      'Analiza trwa zbyt długo. Spróbuj z mniejszą liczbą zdjęć.',
    );

    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) this.onUnauthorized();
      const detail = await this.parseErrorDetail(res);
      let message: string;
      if (res.status === 401) message = 'Sesja wygasła. Zaloguj się ponownie.';
      else if (res.status === 413) message = 'Pliki są za duże. Zmniejsz rozmiar lub liczbę zdjęć.';
      else if (res.status === 429) message = 'Zbyt wiele zapytań. Spróbuj za chwilę.';
      else if (res.status >= 500) message = 'Błąd serwera podczas analizy. Spróbuj ponownie.';
      else message = detail;
      throw new ApiError(res.status, message);
    }
    return res.json();
  }

  // Generate (60s timeout - AI processing needs more time)
  async startGeneration(data: {
    session_id: string;
    catalog_key?: string;
    kategoria?: string;
    specyfikacja?: string;
    colors?: Record<string, string>;
    features?: Record<string, string>;
    corrections?: string;
  }) {
    const res = await this.fetchRaw(
      '/api/generate',
      { method: 'POST', body: JSON.stringify(data) },
      60_000,
      'Uruchamianie generowania trwa zbyt długo. Spróbuj ponownie.',
    );

    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) this.onUnauthorized();
      const detail = await this.parseErrorDetail(res);
      let message: string;
      if (res.status === 401) message = 'Sesja wygasła. Zaloguj się ponownie.';
      else if (res.status === 429) message = 'Zbyt wiele zapytań. Spróbuj za chwilę.';
      else if (res.status >= 500) message = 'Błąd serwera przy generowaniu. Spróbuj ponownie.';
      else message = detail;
      throw new ApiError(res.status, message);
    }
    return res.json() as Promise<{ job_id: string }>;
  }

  async approvePhase(sessionId: string) {
    return this.request('/api/generate/approve', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  async sendFeedback(sessionId: string, feedback: string) {
    return this.request('/api/generate/feedback', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, feedback }),
    });
  }

  async cancelGeneration(sessionId: string) {
    return this.request('/api/generate/cancel', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  async getStatus(sessionId: string) {
    return this.request<Record<string, unknown>>(
      `/api/generate/status?session_id=${encodeURIComponent(sessionId)}`,
    );
  }

  // Chat & Edit (45s timeout — AI processing needs time)
  async editImage(sessionId: string, imageKey: string, instruction: string) {
    const res = await this.fetchRaw(
      '/api/chat/image',
      { method: 'POST', body: JSON.stringify({ session_id: sessionId, image_key: imageKey, instruction }) },
      45_000,
      'Edycja obrazu trwa zbyt długo. Spróbuj ponownie z prostszą instrukcją.',
    );
    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) this.onUnauthorized();
      const detail = await this.parseErrorDetail(res);
      throw new ApiError(res.status, res.status >= 500 ? 'Błąd serwera przy edycji obrazu.' : detail);
    }
    return res.json();
  }

  async editDescription(sessionId: string, instruction: string) {
    const res = await this.fetchRaw(
      '/api/chat/description',
      { method: 'POST', body: JSON.stringify({ session_id: sessionId, instruction }) },
      45_000,
      'Edycja opisu trwa zbyt długo. Spróbuj ponownie z prostszą instrukcją.',
    );
    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) this.onUnauthorized();
      const detail = await this.parseErrorDetail(res);
      throw new ApiError(res.status, res.status >= 500 ? 'Błąd serwera przy edycji opisu.' : detail);
    }
    return res.json();
  }

  async undoDescription(sessionId: string) {
    return this.request('/api/chat/description/undo', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  // Results
  async getResults(jobId: string) {
    return this.request(`/api/results/${encodeURIComponent(jobId)}`);
  }

  async downloadZip(jobId: string) {
    const res = await this.fetchRaw(
      `/api/results/${encodeURIComponent(jobId)}/zip`,
      undefined,
      120_000,
      'Pobieranie trwa zbyt długo. Spróbuj ponownie.',
    );

    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) this.onUnauthorized();
      let message: string;
      if (res.status === 401) message = 'Sesja wygasła. Zaloguj się ponownie.';
      else if (res.status === 404) message = 'Plik nie został znaleziony. Spróbuj wygenerować ponownie.';
      else message = 'Nie udało się pobrać pliku';
      throw new ApiError(res.status, message);
    }
    return res.blob();
  }

  // Catalogs
  async getCatalogs() {
    return this.request<Record<string, unknown>>('/api/catalogs');
  }

  async getColors(catalogKey: string) {
    return this.request<Record<string, string[]>>(
      `/api/catalogs/${encodeURIComponent(catalogKey)}/colors`,
    );
  }

  // Providers
  async getProviderStatus() {
    return this.request<Record<string, unknown>>('/api/providers/status');
  }

  // SSE ticket (jednorazowy, token NIE w URL)
  async getSSETicket(): Promise<string> {
    const res = await this.request<{ ticket: string }>('/api/generate/stream-ticket', {
      method: 'POST',
    });
    return res.ticket;
  }

  createSSE(jobId: string, ticket: string): EventSource {
    return new EventSource(
      `/api/generate/stream/${encodeURIComponent(jobId)}?ticket=${encodeURIComponent(ticket)}`,
    );
  }
}

export const api = new ApiClient();
