export type CandidateStatus = 'candidate' | 'under_review' | 'closed';
export type PriorityLevel = 'low' | 'medium' | 'high' | 'critical' | null;
export type AnalysisStatus = 'completed' | 'needs_review' | 'failed';

export interface Signal {
  signal_id: string;
  drug_name: string;
  event_name: string;
  supporting_report_count: number;
  prr: number;
  candidate_status: CandidateStatus;
  ror?: number | null;
  trend_score?: number | null;
  risk_score?: number | null;
  priority_level?: PriorityLevel;
  dataset_version?: string | null;
}

export interface RelevantSection {
  section_name: string;
  relevance_reason: string;
}

export interface DocumentAnalysis {
  document_id: string;
  signal_id: string;
  relevant_sections: RelevantSection[];
  analysis_status: AnalysisStatus;
  human_review_required: true;
  existing_related_content?: string | null;
  potential_coverage_gap?: string | null;
}

export interface ExplanationResponse {
  explanation: string;
}
