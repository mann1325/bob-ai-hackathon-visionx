import { ApiClient } from './client';
import { Signal, DocumentAnalysis, ExplanationResponse } from '../../shared-schemas/types';

// The actual backend URL would be configured in environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class RealAdapter implements ApiClient {
  private async fetchAs<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getSignals(): Promise<Signal[]> {
    return this.fetchAs<Signal[]>('/signals');
  }

  async getSignal(signalId: string): Promise<Signal | null> {
    return this.fetchAs<Signal>(`/signals/${signalId}`);
  }

  async getExplanation(signalId: string): Promise<ExplanationResponse> {
    return this.fetchAs<ExplanationResponse>(`/signals/${signalId}/explanation`, {
      method: 'POST'
    });
  }

  async uploadDocument(formData: FormData): Promise<{ document_id: string }> {
    // Note: FormData requires omitting 'Content-Type' so the browser can set the boundary automatically
    const response = await fetch(`${API_BASE_URL}/documents`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Document upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  async analyzeDocument(documentId: string): Promise<DocumentAnalysis> {
    return this.fetchAs<DocumentAnalysis>(`/documents/${documentId}/analysis`, {
      method: 'POST'
    });
  }

  async liveSearch(drug: string): Promise<any> {
    return this.fetchAs<any>(`/live-search?drug=${encodeURIComponent(drug)}`);
  }
}
