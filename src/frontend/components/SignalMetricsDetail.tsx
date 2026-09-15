'use client';

import React, { useState, useEffect } from 'react';
import { ApiClient } from '../lib/api/client';
import { SignalDetail, CaseQualityReport, DuplicateCandidate } from '../lib/api/types';
import styles from './SignalMetricsDetail.module.css';

interface SignalMetricsDetailProps {
  apiClient: ApiClient;
  signalId: string;
}

interface DuplicateReviewDetails {
  drug: string;
  event: string;
  age: string;
  sex: string;
  eventDate: string;
}

function parseDuplicateReviewDetails(rationale: string): DuplicateReviewDetails {
  const match = rationale.match(
    /share drug '([^']+)', event '([^']+)', patient age ([^,]+), sex '([^']+)', and event date (\d{4}-\d{2}-\d{2}|\d{8})/,
  );

  if (!match) {
    return { drug: '--', event: '--', age: '--', sex: '--', eventDate: '--' };
  }

  const [, drug, event, age, sex, rawEventDate] = match;
  const normalizedEventDate = rawEventDate.includes('-')
    ? rawEventDate
    : `${rawEventDate.slice(0, 4)}-${rawEventDate.slice(4, 6)}-${rawEventDate.slice(6, 8)}`;
  const eventDate = rawEventDate
    ? new Date(`${normalizedEventDate}T00:00:00Z`).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        timeZone: 'UTC',
      })
    : '--';

  return { drug, event, age, sex, eventDate };
}

function formatMatchedFields(fields: string[]): string {
  const labels = fields.map((field) => field.replaceAll('_', ' '));
  if (labels.length < 2) {
    return labels[0] || '--';
  }
  return `${labels.slice(0, -1).join(', ')}, and ${labels[labels.length - 1]}`;
}

export function SignalMetricsDetail({ apiClient, signalId }: SignalMetricsDetailProps) {
  const [signal, setSignal] = useState<SignalDetail | null>(null);
  
  const [qualityOpen, setQualityOpen] = useState(false);
  const [qualityData, setQualityData] = useState<CaseQualityReport | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualityError, setQualityError] = useState<string | null>(null);

  const [dupesOpen, setDupesOpen] = useState(false);
  const [dupesExpanded, setDupesExpanded] = useState(false);
  const [dupesData, setDupesData] = useState<DuplicateCandidate[] | null>(null);
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
      } catch (e: unknown) {
        setQualityError(e instanceof Error ? e.message : 'Failed to fetch case quality.');
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
      } catch (e: unknown) {
        setDupesError(e instanceof Error ? e.message : 'Failed to fetch duplicates.');
      } finally {
        setDupesLoading(false);
      }
    }
    setDupesOpen(!dupesOpen);
  };

  const displayedCandidates = dupesData
    ? dupesExpanded ? dupesData : dupesData.slice(0, 3)
    : [];

  const formattedImportDate = signal?.import_date
    ? new Date(`${signal.import_date}T00:00:00Z`).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        timeZone: 'UTC',
      })
    : null;

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
                    ? signal.trend_score.toFixed(2)
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
                        <span>Quality Score: <strong>{qualityData.quality_score.toFixed(2)}</strong></span>
                        <span>Reports: <strong>{qualityData.total_reports}</strong></span>
                      </div>
                      <div className={styles.missingList}>
                        <strong>Missing Fields:</strong>
                        <ul>
                          <li>Age: {qualityData.missing_age_count}</li>
                          <li>Sex: {qualityData.missing_sex_count}</li>
                          <li>Event date: {qualityData.missing_date_count}</li>
                        </ul>
                      </div>
                      {qualityData.quality_flags.length > 0 && (
                        <div className={styles.missingList}>
                          <strong>Quality Flags:</strong>
                          <ul>
                            {qualityData.quality_flags.map((flag) => (
                              <li key={flag}>{flag}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {qualityData.indicators.length > 0 && (
                        <div className={styles.missingList}>
                          <strong>Indicators:</strong>
                          <ul>
                            {qualityData.indicators.map((indicator) => (
                              <li key={indicator.flag}>{indicator.description} ({indicator.impact_level})</li>
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
                <span className={styles.metricLabel}>Risk Score</span>
                <span className={`${styles.metricValue} ${signal.risk_score === null ? styles.nullState : ''}`}>
                  {signal.risk_score !== null && signal.risk_score !== undefined ? signal.risk_score : '--'}
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
                    <>
                      <div className={styles.dupeCount}>
                        {dupesData.length.toLocaleString()} potential duplicates found
                      </div>
                      <div className={styles.dupeList}>
                      {displayedCandidates.map(dupe => (
                        <div key={dupe.candidate_id} className={styles.dupeCard}>
                          {(() => {
                            const details = parseDuplicateReviewDetails(dupe.rationale);
                            const similarity = dupe.similarity_score !== null
                              ? `${Math.round(dupe.similarity_score * 100)}%`
                              : '--';

                            return (
                              <>
                                <div className={styles.reviewMeta}>
                                  <span>Candidate {dupe.candidate_id}</span>
                                  <span>Potential duplicate</span>
                                  <span>Status: {dupe.status}</span>
                                </div>
                                <h4 className={styles.reviewTitle}>Potential Duplicate Review</h4>
                                <p className={styles.reviewIntro}>
                                  Reports {dupe.report_id_a} and {dupe.report_id_b} look very similar.
                                </p>
                                <dl className={styles.reviewDetails}>
                                  <div><dt>Drug</dt><dd>{details.drug}</dd></div>
                                  <div><dt>Event</dt><dd>{details.event}</dd></div>
                                  <div><dt>Age</dt><dd>{details.age}</dd></div>
                                  <div><dt>Sex</dt><dd>{details.sex}</dd></div>
                                  <div><dt>Event date</dt><dd>{details.eventDate}</dd></div>
                                </dl>
                                <dl className={styles.reviewMetrics}>
                                  <div>
                                    <dt>Match</dt>
                                    <dd>{formatMatchedFields(dupe.matched_fields)}</dd>
                                  </div>
                                  <div><dt>Similarity</dt><dd>{similarity}</dd></div>
                                  <div>
                                    <dt>Date difference</dt>
                                    <dd>{dupe.date_proximity_days !== null ? `${dupe.date_proximity_days} days` : '--'}</dd>
                                  </div>
                                </dl>
                                <div className={styles.reviewNotice}>
                                  <strong>{dupe.human_review_required ? 'Human review required.' : `Potential duplicate status: ${dupe.status}.`}</strong>
                                  <p>This is only a potential duplicate based on matching fields. It does not confirm that the reports are duplicates.</p>
                                  <p>No automatic deletion is performed.</p>
                                </div>
                                <p className={styles.similarityDetail}>
                                  Drug similarity: {dupe.drug_similarity !== null ? `${Math.round(dupe.drug_similarity * 100)}%` : '--'} · Event similarity: {dupe.event_similarity !== null ? `${Math.round(dupe.event_similarity * 100)}%` : '--'}
                                </p>
                              </>
                            );
                          })()}
                        </div>
                      ))}
                      </div>
                      {dupesData.length > 3 && (
                        <button
                          className={styles.readMoreButton}
                          onClick={() => setDupesExpanded(!dupesExpanded)}
                        >
                          {dupesExpanded ? 'Read less' : 'Read more'}
                        </button>
                      )}
                    </>
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
            <span className={styles.provValue}>{signal.dataset_source || 'Not available'}</span>
          </div>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>FDA FAERS Release:</span>
            <span className={styles.provValue}>{signal.dataset_version || 'Not available'}</span>
          </div>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>Processing Version:</span>
            <span className={styles.provValue}>{signal.processing_version || 'Not available'}</span>
          </div>
          <div className={styles.provItem}>
            <span className={styles.provLabel}>Import Date:</span>
            <span className={styles.provValue}>{formattedImportDate || 'Not available'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
