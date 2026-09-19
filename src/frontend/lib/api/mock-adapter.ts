import { ApiClient } from './client';
import { Signal, SignalListParams, SignalListResponse, DocumentAnalysis, DocumentUpload, ExplanationResponse, CaseQualityReport, DuplicateCandidate, LiveSearchResponse, RegulatoryImpact, ProcessedReport, SupportingReportList, HumanReview, HumanReviewUpdate, InvestigationSummary } from './types';

const MOCK_SIGNALS: Signal[] = [
  {
    signal_id: 'SIG-1001',
    drug_name: 'Paxlovid',
    event_name: 'Hepatotoxicity',
    supporting_report_count: 142,
    prr: 4.2,
    candidate_status: 'under_review',
    ror: 5.1,
    trend_score: 0.85,
    risk_score: 82,
    priority_level: 'critical',
    dataset_version: 'v2.1',
    rank: 1,
  },
  {
    signal_id: 'SIG-1002',
    drug_name: 'Semaglutide',
    event_name: 'Gastroparesis',
    supporting_report_count: 85,
    prr: 2.1,
    candidate_status: 'candidate',
    ror: null, // Null to test UI resilience
    trend_score: null, 
    risk_score: null,
    priority_level: null,
    dataset_version: 'v2.1',
    rank: 2,
  },
  {
    signal_id: 'SIG-1003',
    drug_name: 'Atorvastatin',
    event_name: 'Myopathy',
    supporting_report_count: 310,
    prr: 1.5,
    candidate_status: 'closed',
    ror: 1.6,
    trend_score: -0.12,
    risk_score: 15,
    priority_level: 'low',
    dataset_version: 'v2.0',
    rank: 3,
  }
];

const MOCK_REPORTS: Record<string, ProcessedReport[]> = {
  'SIG-1001': [
    {
      report_id: 'FAERS-1001',
      drug_name: 'Paxlovid',
      reactions: ['Hepatotoxicity', 'Nausea'],
      patient_age: 62,
      patient_sex: 'M',
      event_date: '2024-01-15',
      seriousness: 'Serious',
      seriousness_codes: ['DE'],
      report_quarter: 'v2.1',
      source: 'FDA_FAERS',
    },
    {
      report_id: 'FAERS-1002',
      drug_name: 'Paxlovid',
      reactions: ['Hepatotoxicity'],
      patient_age: null,
      patient_sex: null,
      event_date: null,
      seriousness: 'Unknown',
      seriousness_codes: [],
      report_quarter: 'v2.1',
      source: 'FDA_FAERS',
    },
  ],
};

const MOCK_REVIEWS: Record<string, HumanReview> = {};

const emptyReview = (signalId: string): HumanReview => ({
  review_id: null,
  signal_id: signalId,
  review_status: 'not_started',
  evidence_checklist: {
    supporting_reports_reviewed: false,
    case_quality_reviewed: false,
    reporting_trend_reviewed: false,
    duplicates_reviewed: false,
    ai_explanation_reviewed: false,
    regulatory_documents_reviewed: false,
  },
  reviewer_notes: '',
  reviewer_conclusion: '',
  created_at: null,
  updated_at: null,
});

export class MockAdapter implements ApiClient {
  async listSignals(params?: SignalListParams): Promise<SignalListResponse> {
    void params;
    return new Promise(resolve => setTimeout(() => resolve({
      items: MOCK_SIGNALS,
      total: MOCK_SIGNALS.length,
      page: 1,
      page_size: MOCK_SIGNALS.length,
      pages: 1,
    }), 800));
  }

  async getSignal(signalId: string): Promise<Signal | null> {
    return new Promise(resolve => {
      setTimeout(() => {
        const signal = MOCK_SIGNALS.find(s => s.signal_id === signalId);
        resolve(signal || null);
      }, 500);
    });
  }

  async getInvestigationSummary(signalId: string): Promise<InvestigationSummary> {
    return new Promise(resolve => setTimeout(() => {
      const signal = MOCK_SIGNALS.find(item => item.signal_id === signalId) || MOCK_SIGNALS[0];
      resolve({
        signal_id: signal.signal_id,
        drug_name: signal.drug_name,
        event_name: signal.event_name,
        dataset_version: signal.dataset_version,
        candidate_status: signal.candidate_status,
        priority_level: signal.priority_level,
        supporting_report_count: signal.supporting_report_count,
        prr: signal.prr,
        ror: signal.ror,
        chi_square: null,
        trend_score: signal.trend_score,
        trend_data: null,
        why_flagged: `The signal is supported by ${signal.supporting_report_count} reports with a PRR of ${signal.prr.toFixed(2)}.`,
        known_limitations: ['Spontaneous reporting bias.'],
        case_quality: null,
        duplicate_count: 0,
        duplicates: [],
        ai_explanation: null,
        regulatory_review_areas: [],
        regulatory_rule_matches: [],
        documents: [],
        human_review: MOCK_REVIEWS[signalId] || emptyReview(signalId),
        human_review_required: true,
      });
    }, 250));
  }

  async getReview(signalId: string): Promise<HumanReview> {
    return new Promise(resolve => setTimeout(() => resolve(MOCK_REVIEWS[signalId] || emptyReview(signalId)), 250));
  }

  async saveReview(signalId: string, review: HumanReviewUpdate): Promise<HumanReview> {
    return new Promise(resolve => setTimeout(() => {
      const now = new Date().toISOString();
      const saved = {
        ...emptyReview(signalId),
        ...review,
        review_id: MOCK_REVIEWS[signalId]?.review_id || `MOCK-REV-${signalId}`,
        created_at: MOCK_REVIEWS[signalId]?.created_at || now,
        updated_at: now,
      };
      MOCK_REVIEWS[signalId] = saved;
      resolve(saved);
    }, 350));
  }

  async listSupportingReports(signalId: string, page = 1, pageSize = 10): Promise<SupportingReportList> {
    return new Promise(resolve => {
      setTimeout(() => {
        const reports = MOCK_REPORTS[signalId] || [];
        const offset = (page - 1) * pageSize;
        resolve({
          reports: reports.slice(offset, offset + pageSize),
          total: reports.length,
          page,
          page_size: pageSize,
        });
      }, 500);
    });
  }

  async getReport(reportId: string): Promise<ProcessedReport> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const report = Object.values(MOCK_REPORTS).flat().find(item => item.report_id === reportId);
        if (report) {
          resolve(report);
        } else {
          reject(new Error('Report not found.'));
        }
      }, 400);
    });
  }

  async requestExplanation(signalId: string): Promise<ExplanationResponse> {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve({
          signal_id: signalId,
          why_flagged: 'The signal exceeded deterministic reporting thresholds in spontaneous reports.',
          evidence_summary: 'The available evidence suggests a potential safety signal requiring further investigation.',
          limitations: ['Spontaneous reports do not establish causality.'],
          suggested_questions: ['Review the underlying cases and assess alternative explanations.'],
          generated_at: new Date().toISOString(),
          model_used: 'mock-groq',
          human_review_required: true,
          disclaimer: 'AI-generated explanation for decision support. Does not establish causality or replace human review.',
        });
      }, 1200);
    });
  }

  async uploadDocument(formData: FormData): Promise<DocumentUpload> {
    void formData;
    return new Promise(resolve => {
      setTimeout(() => {
        // Return a stable mock id
        resolve({
          document_id: 'DOC-5005',
          filename: 'uploaded-document.txt',
          file_type: 'txt',
          file_size_bytes: 1024,
          signal_id: null,
          uploaded_at: new Date().toISOString(),
          extracted_text_preview: 'Mock uploaded document preview.',
          status: 'extracted',
        });
      }, 1000);
    });
  }

  async analyzeDocument(documentId: string, signalId: string): Promise<DocumentAnalysis> {
    return new Promise(resolve => {
      setTimeout(() => {
        resolve({
          document_id: documentId,
          signal_id: signalId,
          relevant_sections: [
            { section_name: 'Adverse Reactions', relevance_reason: 'Mentions elevated liver enzymes.' }
          ],
          analysis_status: 'completed',
          human_review_required: true,
          existing_related_content: 'We already have reports of liver toxicity.',
          potential_coverage_gap: 'Limited data on pediatric patients.'
          ,disclaimer: 'AI-assisted document analysis. Identified potential coverage gaps require professional human review.'
        });
      }, 2000);
    });
  }

  async liveSearch(drug: string): Promise<LiveSearchResponse> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (drug.toLowerCase() === 'fail') {
          reject(new Error('openFDA search failed'));
        } else {
          resolve({
            query: drug,
            total: 1,
            results: [{
              brand_name: [drug],
              generic_name: [],
              manufacturer_name: [],
              product_type: null,
              route: [],
              substance_name: [],
              purpose: null,
              warnings: null,
            }],
            source: 'openFDA',
            is_auxiliary_lookup: true,
            disclaimer: 'Auxiliary openFDA drug lookup data. Does not represent SignalTrace-computed signal statistics, PRR/ROR calculations, or regulatory determinations.',
          });
        }
      }, 1500);
    });
  }

  async getCaseQuality(signalId: string): Promise<CaseQualityReport> {
    void signalId;
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          signal_id: signalId,
          total_reports: 142,
          missing_age_count: 12,
          missing_sex_count: 5,
          missing_date_count: 8,
          quality_score: 0.82,
          quality_flags: ['missing_patient_baseline_liver_enzymes', 'missing_concomitant_herbal_supplements'],
          indicators: [
            {
              flag: 'missing_patient_baseline_liver_enzymes',
              description: 'Patient baseline liver enzymes are missing.',
              impact_level: 'medium',
            },
            {
              flag: 'missing_concomitant_herbal_supplements',
              description: 'Concomitant herbal supplements are missing.',
              impact_level: 'medium',
            },
          ],
        });
      }, 700);
    });
  }

  async getPotentialDuplicates(signalId: string): Promise<DuplicateCandidate[]> {
    void signalId;
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          {
            candidate_id: 'DUP-1044',
            report_id_a: 'RPT-1044-A',
            report_id_b: 'RPT-1044-B',
            rationale: 'Matching temporal onset and exact patient demographics across two sites.',
            status: 'potential_duplicate',
            similarity_score: 0.89,
            drug_similarity: 1,
            event_similarity: 1,
            date_proximity_days: 3,
            matched_fields: ['drug', 'event', 'age', 'sex'],
            human_review_required: true,
            disclaimer: 'Candidate duplicate flagged for human triage only. Automated deletion is strictly prohibited.',
          },
          {
            candidate_id: 'DUP-1048',
            report_id_a: 'RPT-1048-A',
            report_id_b: 'RPT-1048-B',
            rationale: 'Same adverse event reported by same physician, but different timeframe.',
            status: 'potential_duplicate',
            similarity_score: 0.42,
            drug_similarity: 1,
            event_similarity: 1,
            date_proximity_days: null,
            matched_fields: ['drug', 'event'],
            human_review_required: true,
            disclaimer: 'Candidate duplicate flagged for human triage only. Automated deletion is strictly prohibited.',
          }
        ]);
      }, 900);
    });
  }

  async getRegulatoryImpact(signalId: string): Promise<RegulatoryImpact> {
    return new Promise(resolve => {
      setTimeout(() => resolve({
        signal_id: signalId,
        review_areas: [],
        rule_matches: [],
        human_review_required: true,
        disclaimer: 'Deterministic regulatory mapping for triage guidance only. Final regulatory determinations require qualified professional review.',
      }), 700);
    });
  }
}
