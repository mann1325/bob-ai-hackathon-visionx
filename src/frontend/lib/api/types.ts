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
  ror: number | null;
  trend_score: number | null;
  risk_score: number | null;
  priority_level: PriorityLevel;
  dataset_version: string | null;
  dataset_source?: string | null;
  processing_version?: string | null;
  import_date?: string | null;
  rank: number | null;
}

export interface SignalMetrics {
  signal_id: string;
  prr: number;
  ror: number | null;
  report_count: number;
  contingency_table: Record<string, number> | null;
  trend_data: Array<Record<string, unknown>> | null;
  chi_square: number | null;
}

export interface SignalDetail extends Signal {
  metrics?: SignalMetrics | null;
  known_limitations?: string[];
  human_review_required?: boolean;
  disclaimer?: string;
}

export interface SignalListParams {
  drug?: string;
  event?: string;
  min_prr?: number;
  status?: CandidateStatus;
  release_id?: string;
  sort_by?: 'rank' | 'prr' | 'supporting_report_count' | 'drug_name';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface SignalListResponse {
  items: Signal[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
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
  disclaimer: string;
}

export interface DocumentUpload {
  document_id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  signal_id: string | null;
  uploaded_at: string | null;
  extracted_text_preview: string | null;
  status: string;
}

export interface GroqExplanation {
  signal_id: string;
  why_flagged: string;
  evidence_summary: string;
  limitations: string[];
  suggested_questions: string[];
  generated_at: string | null;
  model_used: string | null;
  human_review_required: boolean;
  disclaimer: string;
}

export type ExplanationResponse = GroqExplanation;

export interface LiveSearchResponse {
  query: string;
  total: number;
  results: Array<{
    brand_name: string[];
    generic_name: string[];
    manufacturer_name: string[];
    product_type: string | null;
    route: string[];
    substance_name: string[];
    purpose: string | null;
    warnings: string | null;
  }>;
  source: string;
  is_auxiliary_lookup: boolean;
  disclaimer: string;
}

export interface CaseQualityIndicator {
  flag: string;
  description: string;
  impact_level: string;
}

export interface CaseQualityReport {
  signal_id: string;
  total_reports: number;
  missing_age_count: number;
  missing_sex_count: number;
  missing_date_count: number;
  quality_score: number;
  quality_flags: string[];
  indicators: CaseQualityIndicator[];
}

export interface DuplicateCandidate {
  candidate_id: string;
  report_id_a: string;
  report_id_b: string;
  rationale: string;
  status: string;
  similarity_score: number | null;
  drug_similarity: number | null;
  event_similarity: number | null;
  date_proximity_days: number | null;
  matched_fields: string[];
  human_review_required: boolean;
  disclaimer: string;
}

export type PotentialDuplicateCandidate = DuplicateCandidate;

export interface ReviewArea {
  document_type: string;
  section_hint: string | null;
  rationale: string | null;
  priority: string | null;
}

export interface RuleMatch {
  rule_id: string;
  rule_name: string;
  condition_matched: string;
  review_area: ReviewArea;
  confidence_rationale: string | null;
}

export interface RegulatoryImpact {
  signal_id: string;
  review_areas: ReviewArea[];
  rule_matches: RuleMatch[];
  human_review_required: boolean;
  disclaimer: string;
}
