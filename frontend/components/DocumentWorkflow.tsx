'use client';

import React, { useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { DocumentAnalysis } from '../lib/api/types';
import styles from './DocumentWorkflow.module.css';

interface DocumentWorkflowProps {
  apiClient: ApiClient;
  signalId: string;
}

export function DocumentWorkflow({ apiClient, signalId }: DocumentWorkflowProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setIsUploading(true);
    setError(null);
    setAnalysis(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const { document_id } = await apiClient.uploadDocument(formData);
      const docAnalysis = await apiClient.analyzeDocument(document_id, signalId);
      
      setAnalysis(docAnalysis);
    } catch (err: any) {
      setError(err.message || 'Pipeline indexing failed.');
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
          <h3 className={styles.uploadTitle}>Click or drag document to begin Gemini analysis</h3>
          <p className={styles.uploadSpecs}>
            Supported: PDF, XML (ICH E2B R3), DOCX, eCTD Module 2/5 (Max 128MB) • Checksum sha256 computed on drop
          </p>
          <input type="file" onChange={handleFileChange} className={styles.hiddenInput} />
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
          <button className={styles.retryLinkBtn} onClick={() => {setError(null); setFile(null);}}>Try again</button>
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

          <div className={styles.actionFooter}>
             <span className={styles.auditStamp}>21 CFR PART 11 COMPLIANT AUDIT IMMUTABLE • TIMESTAMP: {new Date().toISOString()}</span>
             <button className={styles.commitBtn}>Affirm & Append to Regulatory Dossier</button>
          </div>
        </div>
      )}
    </div>
  );
}
