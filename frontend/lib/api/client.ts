import { Signal, DocumentAnalysis, ExplanationResponse } from '../../shared-schemas/types';

export interface ApiClient {
  getSignals(): Promise<Signal[]>;
  getSignal(signalId: string): Promise<Signal | null>;
  getExplanation(signalId: string): Promise<ExplanationResponse>;
  uploadDocument(formData: FormData): Promise<{ document_id: string }>;
  analyzeDocument(documentId: string): Promise<DocumentAnalysis>;
  liveSearch(drug: string): Promise<any>;
}
