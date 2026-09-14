'use client';

import React, { useState, useEffect } from 'react';
import { ApiClient } from '../lib/api/client';
import { Signal, CaseQualityMetrics, PotentialDuplicateCandidate } from '../lib/api/types';
import styles from './SignalMetricsDetail.module.css';

interface SignalMetricsDetailProps {
  apiClient: ApiClient;
  signalId: string;
}

export function SignalMetricsDetail({ apiClient, signalId }: SignalMetricsDetailProps) {
  const [signal, setSignal] = useState<Signal | null>(null);
  
  const [qualityOpen, setQualityOpen] = useState(false);
  const [qualityData, setQualityData] = useState<CaseQualityMetrics | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualityError, setQualityError] = useState<string | null>(null);

  const [dupesOpen, setDupesOpen] = useState(false);
  const [dupesData, setDupesData] = useState<PotentialDuplicateCandidate[] | null>(null);
  const [dupesLoading, setDupesLoading] = useState(false);
  const [dupesError, setDupesError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.getSignal(signalId).then(setSignal).catch(console.error);
  }, [apiClient, signalId]);

  const handleToggleQuality = async () => {
    if (!qualityOpen && !qualityData) {
      setQualityLoading(true);
      setQualityError(null);
      try {
        const data = await apiClient.getCaseQuality(signalId);
        setQualityData(data);
      } catch (e: any) {
        setQualityError(e.message || 'Failed to fetch case quality.');
      } finally {
        setQualityLoading(false);
      }
    }
    setQualityOpen(!qualityOpen);
  };

  const handleToggleDupes = async () => {
    if (!dupesOpen && !dupesData) {
      setDupesLoading(true);
      setDupesError(null);
      try {
        const data = await apiClient.getPotentialDuplicates(signalId);
        setDupesData(data);
      } catch (e: any) {
        setDupesError(e.message || 'Failed to fetch duplicates.');
      } finally {
        setDupesLoading(false);
      }
    }
    setDupesOpen(!dupesOpen);
  };

  if (!signal) {
    return <div style={{ color: '#A1A1AA', padding: '2rem', fontFamily: 'monospace' }}>Fetching signal integrity...</div>;
  }

  return (
    <div className={styles.detailWrapper}>
      <header className={styles.headerCard}>
        <div className={styles.titleArea}>
          <h1>{signal.drug_name}</h1>
          <p>{signal.event_name}</p>
        </div>
        <div className={styles.statusBadge}>
          {signal.candidate_status.replace('_', ' ')}
        </div>
      </header>

      <div className={styles.evidenceSummaryBox}>
        <h3 className={styles.summaryTitle}>Why This Signal Was Flagged</h3>
        <p className={styles.summaryParagraph}>
          The combination of <strong>{signal.drug_name}</strong> and <strong>{signal.event_name}</strong> generated a candidate signal driven by <strong>{signal.supporting_report_count}</strong> supporting reports. 
          Statistical modeling reveals a PRR of <strong>{signal.prr.toFixed(2)}</strong>
          {signal.ror !== null && signal.ror !== undefined && ` and an ROR of ${signal.ror.toFixed(2)}`}.
          {(signal.trend_score !== null && signal.trend_score !== undefined) && ` Trend analysis indicates a ${signal.trend_score > 0 ? '+' : ''}${signal.trend_score.toFixed(1)}% shift.`}
          {signal.priority_level && ` Currently assessed as ${signal.priority_level.toUpperCase()} priority.`}
        </p>
        <div className={styles.safetyDisclaimer}>
          This is a candidate statistical signal requiring human review; it does not establish causality.
        </div>
      </div>

      <div className={styles.panelsGrid}>
        {/* Left Panel: Deterministic Metrics */}
        <section className={styles.panelCard}>
          <div className={`${styles.panelBanner} ${styles.deterministic}`}>
            DETERMINISTIC / CALCULATED (NON-AI)
          </div>
          <div className={styles.panelContent}>
            <div className={styles.metricsGrid}>
              <div className={styles.metricBlock}>
                <span className={styles.metricLabel}>Supporting Reports</span>
                <span className={styles.metricValue}>{signal.supporting_report_count}</span>
              </div>
              <div className={styles.metricBlock}>
                <span className={styles.metricLabel}>PRR</span>
                <span className={styles.metricValue}>{signal.prr.toFixed(2)}</span>
              </div>
              <div className={styles.metricBlock}>
                <span className={styles.metricLabel}>ROR (95% CI)</span>
                <span className={`${styles.metricValue} ${signal.ror === null ? styles.nullState : ''}`}>
                  {signal.ror !== null && signal.ror !== undefined ? signal.ror.toFixed(2) : '--'}
                </span>
              </div>
              <div className={styles.metricBlock}>
                <span className={styles.metricLabel}>Trend Score</span>
                <span className={`${styles.metricValue} ${signal.trend_score === null ? styles.nullState : ''}`}>
                  {signal.trend_score !== null && signal.trend_score !== undefined 
                    ? `${signal.trend_score > 0 ? '+' : ''}${signal.trend_score.toFixed(1)}%` 
                    : '--'}
                </span>
              </div>
            </div>
            
            <div className={styles.expandableSection}>
              <button className={styles.expandBtn} onClick={handleToggleQuality}>
                <h3>Case Quality Analysis</h3>
                <span>{qualityOpen ? '▼' : '►'}</span>
              </button>
              
              {qualityOpen && (
                <div className={styles.expandableContent}>
                  {qualityLoading ? (
                    <div className={styles.smallSkeleton}></div>
                  ) : qualityError ? (
                    <div className={styles.errorText}>⚠ {qualityError}</div>
                  ) : qualityData ? (
                    <div className={styles.qualityView}>
                      <div className={styles.qualityHeader}>
                        <span>Status: <strong>{qualityData.status}</strong></span>
                        <span>Score: <strong>{qualityData.completeness_score}%</strong></span>
                      </div>
                      <p className={styles.explanationText}>{qualityData.explanation}</p>
                      {qualityData.missing_information.length > 0 && (
                        <div className={styles.missingList}>
                          <strong>Missing Data:</strong>
                          <ul>
                            {qualityData.missing_information.map((miss, idx) => (
                              <li key={idx}>{miss}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className={styles.emptyText}>No quality data available.</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Right Panel: AI Assessment */}
        <section className={styles.panelCard}>
          <div className={`${styles.panelBanner} ${styles.mlAssisted}`}>
            ⚠ ML-ASSISTED SYNTHESIS — HUMAN REVIEW REQUIRED 
          </div>
          <div className={styles.panelContent}>
            <div className={styles.metricsGrid}>
              <div className={styles.metricBlock}>
                <span className={styles.metricLabel}>Priority Assessment</span>
                <span className={`${styles.priorityBadge} ${signal.priority_level ? styles[signal.priority_level] : styles.unscored}`}>
                  {signal.priority_level ? signal.priority_level : 'UNSCORED'}
                </span>
              </div>
              <div className={styles.metricBlock}>
                <span className={styles.metricLabel}>Risk Score (v4.8)</span>
                <span className={`${styles.metricValue} ${signal.risk_score === null ? styles.nullState : ''}`}>
                  {signal.risk_score !== null && signal.risk_score !== undefined ? `${signal.risk_score} / 100` : '--'}
                </span>
              </div>
            </div>

            <div className={styles.expandableSection} style={{ marginTop: '2rem' }}>
              <button className={styles.expandBtn} onClick={handleToggleDupes}>
                <h3>Potential Duplicates Engine</h3>
                <span>{dupesOpen ? '▼' : '►'}</span>
              </button>
              
              {dupesOpen && (
                <div className={styles.expandableContent}>
                  {dupesLoading ? (
                    <div className={styles.smallSkeleton}></div>
                  ) : dupesError ? (
                     <div className={styles.errorText}>⚠ {dupesError}</div>
                  ) : dupesData && dupesData.length > 0 ? (
                    <div className={styles.dupeList}>
                      {dupesData.map(dupe => (
                        <div key={dupe.candidate_signal_id} className={styles.dupeCard}>
                          <div className={styles.dupeHeader}>
                            <strong>{dupe.candidate_signal_id}</strong>
                            <span className={styles.dupeBadge}>Potential Duplicate</span>
                            <span className={styles.similarity}>Match: {dupe.similarity_match}</span>
                          </div>
                          <p className={styles.explanationText}>{dupe.overlap_reason}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.emptyText}>No potential duplicates flagged.</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      <div className={styles.provenanceFooter}>
        <span className={styles.provTitle}>DATA PROVENANCE:</span>
        <div className={styles.provItems}>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>Dataset Source:</span>
            <span className={styles.provValue}>FDA FAERS Open Data</span>
          </div>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>FDA FAERS Release:</span>
            <span className={styles.provValue}>{signal.dataset_version || 'v2.1 (Q3)'}</span>
          </div>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>Processing Version:</span>
            <span className={styles.provValue}>SignalTrace-v1.4.2</span>
          </div>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>Import Date:</span>
            <span className={styles.provValue}>{new Date().toLocaleDateString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
