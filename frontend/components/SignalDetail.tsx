'use client';

import React, { useState, useEffect } from 'react';
import apiClient from '../lib/api';
import { Signal, DocumentAnalysis, ExplanationResponse } from '../shared-schemas/types';
import { AILabel } from './ui/AILabel';
import styles from './SignalDetail.module.css';

interface SignalDetailProps {
  signal: Signal;
  onBack: () => void;
}

export function SignalDetail({ signal, onBack }: SignalDetailProps) {
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(true);

  useEffect(() => {
    // Load explanation on mount
    apiClient.getExplanation(signal.signal_id)
      .then(setExplanation)
      .catch(console.error)
      .finally(() => setIsLoadingExplanation(false));
  }, [signal.signal_id]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const { document_id } = await apiClient.uploadDocument(formData);
      const docAnalysis = await apiClient.analyzeDocument(document_id);
      setAnalysis(docAnalysis);
    } catch (err) {
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={styles.detailContainer}>
      <header className={styles.header}>
        <button onClick={onBack} className={styles.backBtn}>← Back to Dashboard</button>
        <div className={styles.titleSection}>
          <h1 className={styles.drugName}>{signal.drug_name}</h1>
          <span className={styles.eventName}>{signal.event_name}</span>
        </div>
        <span className={`${styles.statusBadge} ${styles[signal.candidate_status]}`}>
          {signal.candidate_status.replace('_', ' ')}
        </span>
      </header>

      <div className={styles.gridLayout}>
        {/* Left Column: Metrics & Risk */}
        <div className={styles.leftColumn}>
          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Hard Metrics</h2>
            <div className={styles.metricsGrid}>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Reports</span>
                <span className={styles.metricValue}>{signal.supporting_report_count}</span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>PRR</span>
                <span className={styles.metricValue}>{signal.prr.toFixed(1)}</span>
              </div>
              {signal.ror !== null && signal.ror !== undefined && (
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>ROR</span>
                  <span className={styles.metricValue}>{signal.ror.toFixed(1)}</span>
                </div>
              )}
            </div>
          </section>

          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Priority & Risk Assessment</h2>
            <div className={styles.aiFieldGroup}>
              {signal.priority_level && (
                <AILabel 
                  label="Priority Level" 
                  value={<span className={`${styles.priorityIndicator} ${styles[signal.priority_level]}`}>{signal.priority_level}</span>} 
                  inline
                />
              )}
              {signal.risk_score && (
                <AILabel 
                  label="Risk Score" 
                  value={
                    <div className={styles.riskBarContainer}>
                      <div className={styles.riskBarItem} style={{ width: `${signal.risk_score}%` }}></div>
                      <span className={styles.riskScoreText}>{signal.risk_score} / 100</span>
                    </div>
                  } 
                />
              )}
            </div>
          </section>
        </div>

        {/* Right Column: AI Explanations & Documents */}
        <div className={styles.rightColumn}>
          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Evidence Synthesis</h2>
            {isLoadingExplanation ? (
              <div className={styles.loadingPulse}>Generating synthesis...</div>
            ) : explanation ? (
              <AILabel 
                label="Groq Evidence Explanation" 
                value={<p className={styles.paragraphText}>{explanation.explanation}</p>} 
              />
            ) : (
              <p className={styles.errorText}>No explanation available.</p>
            )}
          </section>

          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Regulatory Document Analysis</h2>
            
            <div className={styles.uploadSection}>
              <label className={styles.uploadBtn}>
                {isUploading ? 'Analyzing Document...' : 'Upload Document for Analysis'}
                <input type="file" onChange={handleFileUpload} className={styles.hiddenInput} disabled={isUploading} />
              </label>
            </div>

            {analysis && (
              <div className={styles.analysisResults}>
                <h3 className={styles.subTitle}>Analysis Results</h3>
                <div className={styles.statusIndicator}>
                  Status: <strong>{analysis.analysis_status}</strong>
                </div>
                
                <div className={styles.sectionsList}>
                  {analysis.relevant_sections.map((sec, idx) => (
                    <div key={idx} className={styles.sectionItem}>
                      <h4>{sec.section_name}</h4>
                      <p>{sec.relevance_reason}</p>
                    </div>
                  ))}
                </div>

                {analysis.potential_coverage_gap && (
                  <div className={styles.gapWarning}>
                    <AILabel 
                      label="Potential Coverage Gap" 
                      value={<p>{analysis.potential_coverage_gap}</p>} 
                    />
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
