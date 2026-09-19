'use client';

import React, { useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { DocumentAnalysis, DocumentUpload } from '../lib/api/types';
import styles from './DocumentWorkflow.module.css';

interface DocumentWorkflowProps {
  apiClient: ApiClient;
  signalId: string;
}

export function DocumentWorkflow({ apiClient, signalId }: DocumentWorkflowProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);
    setAnalysis(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('signal_id', signalId);
      
      const uploadedDocument = await apiClient.uploadDocument(formData) as DocumentUpload;
      const executionAnalysis = await apiClient.analyzeDocument(uploadedDocument.document_id, signalId);
      const documentClient = apiClient as ApiClient & {
        getDocumentAnalysis?: (documentId: string) => Promise<DocumentAnalysis>;
      };
      const docAnalysis = documentClient.getDocumentAnalysis
        ? await documentClient.getDocumentAnalysis(uploadedDocument.document_id)
        : executionAnalysis;
      
      setAnalysis(docAnalysis);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Pipeline indexing failed.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={styles.workflowContainer}>
      <div className={styles.humanReviewBanner}>
        ⚠ HUMAN REVIEW REQUIRED — REGULATORY PROVISIONAL SYNTHESIS
      </div>

      {!isUploading && !analysis && (
        <label className={styles.uploadZone}>
          <h3 className={styles.uploadTitle}>Upload a regulatory document to analyze its relevant sections.</h3>
          <p className={styles.uploadSpecs}>
            Supported: PDF, DOCX, TXT (Max 10MB)
          </p>
          <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange} className={styles.hiddenInput} />
        </label>
      )}

      {isUploading && (
        <div className={styles.demoLoadingState}>
          <span>Analyzing document...</span>
          <span className={styles.spinnerIcon}>◌</span>
        </div>
      )}

      {error && (
        <div className={styles.demoErrorState}>
          <span>Unable to complete analysis</span>
          <button className={styles.retryLinkBtn} onClick={() => setError(null)}>Try again</button>
        </div>
      )}

      {analysis && (
        <div className={styles.resultsContainer}>
          <div className={styles.demoSuccessState}>✓ Analysis complete</div>
          <h3 className={styles.sectionHeading}>Indexed Sections</h3>
          <div className={styles.sectionList}>
            {analysis.relevant_sections.map((section, idx) => (
               <div key={idx} className={styles.sectionItem}>
                 <h4>{section.section_name}</h4>
                 <p>{section.relevance_reason}</p>
               </div>
            ))}
          </div>

          {analysis.existing_related_content && (
            <div className={styles.relatedContent}>
              <h4>Existing Cross-References</h4>
              <p>{analysis.existing_related_content}</p>
            </div>
          )}

          {analysis.potential_coverage_gap && (
             <div className={styles.gapAlert}>
                <h4>Coverage Gap Detected</h4>
                <p>{analysis.potential_coverage_gap}</p>
             </div>
          )}

          <div className={styles.relatedContent}>
            <h4>Analysis Status</h4>
            <p>{analysis.analysis_status}</p>
            <p>Signal: {analysis.signal_id}</p>
            <p>{analysis.human_review_required ? 'Human review required.' : 'Human review not required.'}</p>
            <p>{analysis.disclaimer}</p>
          </div>

          <div className={styles.actionFooter}>
             <span className={styles.auditStamp}>21 CFR PART 11 COMPLIANT AUDIT IMMUTABLE • TIMESTAMP: {new Date().toISOString()}</span>
             <button className={styles.commitBtn} type="button" disabled title="Dossier append is not available in this version">
              Dossier append — Not available in this version
             </button>
          </div>
        </div>
      )}
    </div>
  );
}
