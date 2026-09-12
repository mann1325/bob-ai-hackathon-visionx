import { ApiClient } from './client';
import { Signal, DocumentAnalysis, ExplanationResponse, CaseQualityMetrics, PotentialDuplicateCandidate } from './types';

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
  }
];

export class MockAdapter implements ApiClient {
  async listSignals(): Promise<Signal[]> {
    return new Promise(resolve => setTimeout(() => resolve(MOCK_SIGNALS), 800));
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
          explanation: `This is an AI-generated explanation for signal ${signalId}. The evidence suggests a potential correlation based on spontaneous reports. This assessment requires human review.`
        });
      }, 1200);
    });
  }

  async uploadDocument(formData: FormData): Promise<{ document_id: string }> {
    return new Promise(resolve => {
      setTimeout(() => {
        // Return a stable mock id
        resolve({ document_id: 'DOC-5005' });
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
        });
      }, 2000);
    });
  }

  async liveSearch(drug: string): Promise<any> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (drug.toLowerCase() === 'fail') {
          reject(new Error('openFDA search failed'));
        } else {
          resolve({
            meta: { results: { skip: 0, limit: 1, total: 1 } },
            results: [{ safety_reports: 120, brand_name: drug }]
          });
        }
      }, 1500);
    });
  }

  async getCaseQuality(signalId: string): Promise<CaseQualityMetrics> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          status: 'Medium',
          completeness_score: 82,
          missing_information: ['Patient baseline liver enzymes', 'Concomitant herbal supplements'],
          explanation: 'While temporal association is present, confounder data requires manual chart extraction.'
        });
      }, 700);
    });
  }

  async getPotentialDuplicates(signalId: string): Promise<PotentialDuplicateCandidate[]> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          {
            candidate_signal_id: 'SIG-1044',
            similarity_match: 'High (89%)',
            overlap_reason: 'Matching temporal onset and exact patient demographics across two sites.'
          },
          {
            candidate_signal_id: 'SIG-1048',
            similarity_match: 'Low (42%)',
            overlap_reason: 'Same adverse event reported by same physician, but different timeframe.'
          }
        ]);
      }, 900);
    });
  }
}
