import { ApiClient } from './client';
import { SignalDetail, SignalListParams, SignalListResponse, DocumentAnalysis, DocumentUpload, GroqExplanation, CaseQualityReport, DuplicateCandidate, LiveSearchResponse, RegulatoryImpact } from './types';

// The actual backend URL would be configured in environment variables
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://signaltrace-backend.onrender.com';
const normalizedApiUrl = configuredApiUrl.replace(/\/+$/, '');
const API_BASE_URL = normalizedApiUrl.endsWith('/api/v1')
  ? normalizedApiUrl
  : `${normalizedApiUrl}/api/v1`;

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

  async listSignals(params: SignalListParams = {}): Promise<SignalListResponse> {
    const query = new URLSearchParams();
    if (params.drug !== undefined) query.set('drug', params.drug);
    if (params.event !== undefined) query.set('event', params.event);
    if (params.min_prr !== undefined) query.set('min_prr', String(params.min_prr));
    if (params.status !== undefined) query.set('status', params.status);
    if (params.release_id !== undefined) query.set('release_id', params.release_id);
    if (params.sort_by !== undefined) query.set('sort_by', params.sort_by);
    if (params.sort_order !== undefined) query.set('sort_order', params.sort_order);
    if (params.page !== undefined) query.set('page', String(params.page));
    if (params.page_size !== undefined) query.set('page_size', String(params.page_size));

    const queryString = query.toString();
    return this.fetchAs<SignalListResponse>(`/signals${queryString ? `?${queryString}` : ''}`);
  }

  async getSignal(signalId: string): Promise<SignalDetail | null> {
    return this.fetchAs<SignalDetail>(`/signals/${signalId}`);
  }

  async requestExplanation(signalId: string): Promise<GroqExplanation> {
    return this.fetchAs<GroqExplanation>(`/signals/${signalId}/explain`, {
      method: 'POST'
    });
  }

  async uploadDocument(formData: FormData): Promise<DocumentUpload> {
    // Note: FormData requires omitting 'Content-Type' so the browser can set the boundary automatically
    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Document upload failed: ${response.statusText}`);
    }

    return response.json() as Promise<DocumentUpload>;
  }

  async analyzeDocument(documentId: string, signalId: string): Promise<DocumentAnalysis> {
    void signalId;
    return this.fetchAs<DocumentAnalysis>(`/documents/${documentId}/analyze`, {
      method: 'POST'
    });
  }

  async getDocumentAnalysis(documentId: string): Promise<DocumentAnalysis> {
    return this.fetchAs<DocumentAnalysis>(`/documents/${documentId}/analysis`);
  }

  async getDocument(documentId: string): Promise<DocumentUpload> {
    return this.fetchAs<DocumentUpload>(`/documents/${documentId}`);
  }

  async listSignalDocuments(signalId: string): Promise<Array<Record<string, unknown>>> {
    return this.fetchAs<Array<Record<string, unknown>>>(`/signals/${signalId}/documents`);
  }

  async liveSearch(drug: string): Promise<LiveSearchResponse> {
    const query = new URLSearchParams({ q: drug, limit: '10' });
    return this.fetchAs<LiveSearchResponse>(`/openfda/drugs/search?${query.toString()}`);
  }

  async getCaseQuality(signalId: string): Promise<CaseQualityReport> {
    const response = await this.fetchAs<CaseQualityReport>(`/signals/${signalId}/case-quality`);
    return {
      signal_id: response.signal_id,
      total_reports: response.total_reports,
      missing_age_count: response.missing_age_count,
      missing_sex_count: response.missing_sex_count,
      missing_date_count: response.missing_date_count,
      quality_score: response.quality_score,
      quality_flags: response.quality_flags,
      indicators: response.indicators,
    };
  }

  async getPotentialDuplicates(signalId: string): Promise<DuplicateCandidate[]> {
    return this.fetchAs<DuplicateCandidate[]>(`/signals/${signalId}/duplicates`);
  }

  async getRegulatoryImpact(signalId: string): Promise<RegulatoryImpact> {
    return this.fetchAs<RegulatoryImpact>(`/signals/${signalId}/regulatory-impact`);
  }
}
