import { Signal, DocumentAnalysis, ExplanationResponse, CaseQualityMetrics, PotentialDuplicateCandidate } from './types';

export interface ApiClient {
  listSignals(): Promise<Signal[]>;
  getSignal(signalId: string): Promise<Signal | null>;
  requestExplanation(signalId: string): Promise<ExplanationResponse>;
  uploadDocument(formData: FormData): Promise<{ document_id: string }>;
  analyzeDocument(documentId: string, signalId: string): Promise<DocumentAnalysis>;
  liveSearch(drug: string): Promise<any>;
  getCaseQuality(signalId: string): Promise<CaseQualityMetrics>;
  getPotentialDuplicates(signalId: string): Promise<PotentialDuplicateCandidate[]>;
}
