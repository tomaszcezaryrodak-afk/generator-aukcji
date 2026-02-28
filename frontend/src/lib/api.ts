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

  setToken(token: string | null) {
    this.token = token;
  }

  getToken() {
    return this.token;
  }

  setOnUnauthorized(cb: (() => void) | null) {
    this.onUnauthorized = cb;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
      ...((options?.headers as Record<string, string>) || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (!(options?.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(path, { ...options, headers });

    if (!res.ok) {
      if (res.status === 401 && this.onUnauthorized) {
        this.onUnauthorized();
      }
      const body = await res.text();
      const message = res.status === 401
        ? 'Sesja wygasła. Zaloguj się ponownie.'
        : res.status === 429
          ? 'Zbyt wiele zapytań. Spróbuj za chwilę.'
          : res.status >= 500
            ? 'Błąd serwera. Spróbuj ponownie.'
            : body;
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

  // Upload & Analyze
  async uploadAndAnalyze(formData: FormData) {
    const headers: Record<string, string> = {};
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const res = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
      headers,
    });

    if (!res.ok) throw new ApiError(res.status, await res.text());
    return res.json();
  }

  // Generate
  async startGeneration(data: {
    session_id: string;
    colors?: Record<string, string>;
    features?: Record<string, string>;
    corrections?: string;
  }) {
    return this.request<{ job_id: string }>('/api/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
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
      `/api/generate/status?session_id=${sessionId}`,
    );
  }

  // Chat & Edit
  async editImage(sessionId: string, imageKey: string, instruction: string) {
    return this.request('/api/chat/image', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        image_key: imageKey,
        instruction,
      }),
    });
  }

  async editDescription(sessionId: string, instruction: string) {
    return this.request('/api/chat/description', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, instruction }),
    });
  }

  async undoDescription(sessionId: string) {
    return this.request('/api/chat/description/undo', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  // Results
  async getResults(sessionId: string) {
    return this.request(`/api/results/${sessionId}`);
  }

  async downloadZip(sessionId: string) {
    const headers: Record<string, string> = {};
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const res = await fetch(`/api/results/${sessionId}/zip`, { headers });
    if (!res.ok) throw new ApiError(res.status, 'Download failed');
    return res.blob();
  }

  // Catalogs
  async getCatalogs() {
    return this.request<Record<string, unknown>>('/api/catalogs');
  }

  async getColors(catalogKey: string) {
    return this.request<Record<string, string[]>>(
      `/api/catalogs/${catalogKey}/colors`,
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
    return new EventSource(`/api/generate/stream/${jobId}?ticket=${ticket}`);
  }
}

export const api = new ApiClient();
