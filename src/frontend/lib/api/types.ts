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

export type ReviewStatus = 'not_started' | 'in_review' | 'reviewed';

export interface EvidenceChecklist {
  supporting_reports_reviewed: boolean;
  case_quality_reviewed: boolean;
  reporting_trend_reviewed: boolean;
  duplicates_reviewed: boolean;
  ai_explanation_reviewed: boolean;
  regulatory_documents_reviewed: boolean;
}

export interface HumanReview {
  review_id: string | null;
  signal_id: string;
  review_status: ReviewStatus;
  evidence_checklist: EvidenceChecklist;
  reviewer_notes: string;
  reviewer_conclusion: string;
  created_at: string | null;
  updated_at: string | null;
}

export type HumanReviewUpdate = Omit<HumanReview, 'review_id' | 'signal_id' | 'created_at' | 'updated_at'>;

export interface InvestigationSummary {
  signal_id: string;
  drug_name: string;
  event_name: string;
  dataset_version: string | null;
  candidate_status: string;
  priority_level: string | null;
  supporting_report_count: number;
  prr: number;
  ror: number | null;
  chi_square: number | null;
  trend_score: number | null;
  trend_data: Array<Record<string, unknown>> | null;
  why_flagged: string;
  known_limitations: string[];
  case_quality: CaseQualityReport | null;
  duplicate_count: number;
  duplicates: Array<Pick<DuplicateCandidate, 'candidate_id' | 'report_id_a' | 'report_id_b' | 'status' | 'similarity_score' | 'matched_fields' | 'human_review_required'>>;
  ai_explanation: (Partial<GroqExplanation> & { advisory: boolean }) | null;
  regulatory_review_areas: ReviewArea[];
  regulatory_rule_matches: RuleMatch[];
  documents: Array<{
    document_id: string;
    filename: string;
    analysis_status: string | null;
    relevant_section_count: number;
    potential_coverage_gap: string | null;
    human_review_required: boolean;
  }>;
  human_review: HumanReview | null;
  human_review_required: boolean;
}

export interface ProcessedReport {
  report_id: string;
  drug_name: string;
  reactions: string[];
  patient_age: number | null;
  patient_sex: string | null;
  event_date: string | null;
  seriousness: 'Serious' | 'Non-serious' | 'Unknown';
  seriousness_codes: string[];
  report_quarter: string;
  source: string;
}

export interface SupportingReportList {
  reports: ProcessedReport[];
  total: number;
  page: number;
  page_size: number;
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
