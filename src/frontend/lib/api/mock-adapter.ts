import { ApiClient } from './client';
import { Signal, SignalListParams, SignalListResponse, DocumentAnalysis, DocumentUpload, ExplanationResponse, CaseQualityReport, DuplicateCandidate, LiveSearchResponse, RegulatoryImpact } from './types';

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
