import { SignalDetail, SignalListParams, SignalListResponse, DocumentAnalysis, ExplanationResponse, CaseQualityReport, PotentialDuplicateCandidate, LiveSearchResponse, RegulatoryImpact } from './types';

export interface ApiClient {
  listSignals(params?: SignalListParams): Promise<SignalListResponse>;
  getSignal(signalId: string): Promise<SignalDetail | null>;
  requestExplanation(signalId: string): Promise<ExplanationResponse>;
  uploadDocument(formData: FormData): Promise<{ document_id: string }>;
  analyzeDocument(documentId: string, signalId: string): Promise<DocumentAnalysis>;
  liveSearch(drug: string): Promise<LiveSearchResponse>;
  getCaseQuality(signalId: string): Promise<CaseQualityReport>;
  getPotentialDuplicates(signalId: string): Promise<PotentialDuplicateCandidate[]>;
  getRegulatoryImpact(signalId: string): Promise<RegulatoryImpact>;
}
