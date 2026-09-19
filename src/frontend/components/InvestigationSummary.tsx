'use client';

import React, { useEffect, useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { InvestigationSummary as InvestigationSummaryData, SignalDetail } from '../lib/api/types';
import styles from './InvestigationSummary.module.css';

interface InvestigationSummaryProps {
  apiClient: ApiClient;
  signalId: string;
}

function valueOrUnavailable(value: string | number | null | undefined): string | number {
  return value === null || value === undefined || value === '' ? 'Unavailable' : value;
}

function checklistCount(summary: InvestigationSummaryData): number {
  return summary.human_review ? Object.values(summary.human_review.evidence_checklist).filter(Boolean).length : 0;
}

export function InvestigationSummary({ apiClient, signalId }: InvestigationSummaryProps) {
  const [summary, setSummary] = useState<InvestigationSummaryData | null>(null);
  const [signalDetail, setSignalDetail] = useState<SignalDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([apiClient.getInvestigationSummary(signalId), apiClient.getSignal(signalId)])
      .then(([data, detail]) => {
        if (active) {
          setSummary(data);
          setSignalDetail(detail);
        }
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : 'Failed to load investigation summary.');
      });
    return () => { active = false; };
  }, [apiClient, signalId]);

  return (
    <section className={styles.summary} aria-labelledby="investigation-summary-heading">
      <div className={styles.header}>
        <div>
          <h2 id="investigation-summary-heading">Investigation Summary</h2>
          <p>Read-only synthesis of existing signal evidence and reviewer state.</p>
        </div>
      </div>
      {error ? <div className={styles.error} role="alert">{error}</div> : !summary ? <div className={styles.state}>Loading investigation summary...</div> : (
        <>
          <div className={styles.grid}>
            <div><span>Signal</span><strong>{summary.signal_id}</strong></div>
            <div><span>Drug</span><strong>{summary.drug_name}</strong></div>
            <div><span>Event</span><strong>{summary.event_name}</strong></div>
            <div><span>Status / Priority</span><strong>{summary.candidate_status} / {valueOrUnavailable(summary.priority_level)}</strong></div>
            <div><span>Reports</span><strong>{summary.supporting_report_count}</strong></div>
            <div><span>PRR / ROR</span><strong>{summary.prr.toFixed(2)} / {summary.ror === null ? 'Unavailable' : summary.ror.toFixed(2)}</strong></div>
            <div><span>Chi-square</span><strong>{summary.chi_square === null ? 'Unavailable' : summary.chi_square.toFixed(2)}</strong></div>
            <div><span>Trend Score</span><strong>{valueOrUnavailable(summary.trend_score)}</strong></div>
            <div><span>Dataset / Release</span><strong>{summary.dataset_version ? `FDA FAERS / ${summary.dataset_version}` : 'Unavailable'}</strong></div>
          </div>
          <div className={styles.provenance}><span>Dataset/source</span><strong>{signalDetail?.dataset_source || 'Unavailable'}</strong><span>Release</span><strong>{summary.dataset_version || 'Unavailable'}</strong><span>Processing version</span><strong>{signalDetail?.processing_version || 'Unavailable'}</strong><span>Import date</span><strong>{signalDetail?.import_date ? new Date(`${signalDetail.import_date}T00:00:00Z`).toLocaleDateString() : 'Unavailable'}</strong></div>
          <div className={styles.reason}><span>Why flagged</span><p>{summary.why_flagged}</p></div>
          <div className={styles.briefGrid}>
            <details><summary>Statistical Detail</summary><p>Trend data: {summary.trend_data ? `${summary.trend_data.length} points` : 'Unavailable'}</p>{signalDetail?.metrics?.contingency_table && <p>Contingency table: {Object.entries(signalDetail.metrics.contingency_table).map(([key, value]) => `${key}=${value}`).join(' · ')}</p>}</details>
            <details open><summary>Evidence Limitations</summary>{(summary.known_limitations.length || signalDetail?.known_limitations?.length) ? <ul>{(summary.known_limitations.length ? summary.known_limitations : signalDetail?.known_limitations || []).map((item) => <li key={item}>{item}</li>)}</ul> : <p>Unavailable for this signal.</p>}</details>
            <details><summary>Supporting Evidence</summary><p>{summary.supporting_report_count.toLocaleString()} supporting reports. Seriousness and FAERS outcomes are available per report in Evidence Explorer.</p><p><a href="#evidence-explorer">View Supporting Reports</a></p></details>
            <details><summary>Case Quality</summary>{summary.case_quality ? <><p>Score {summary.case_quality.quality_score.toFixed(2)} · {summary.case_quality.total_reports.toLocaleString()} reports</p><p>Missing age: {summary.case_quality.missing_age_count} · sex: {summary.case_quality.missing_sex_count} · event date: {summary.case_quality.missing_date_count}</p><p>{summary.case_quality.quality_flags.join(', ') || 'No flags'}</p></> : <p>Unavailable</p>}</details>
            <details><summary>Reporting Trend</summary><p>{summary.trend_data ? `${summary.trend_data.length} existing trend points.` : 'Unavailable for this signal.'}</p></details>
            <details><summary>Duplicate Triage</summary><p>{summary.duplicate_count.toLocaleString()} potential duplicate candidates for human triage.</p>{summary.duplicates.map((item) => <p key={item.candidate_id}><strong>{item.report_id_a} / {item.report_id_b}</strong> · {item.similarity_score === null ? 'Unavailable' : `${Math.round(item.similarity_score * 100)}%`} similarity · {item.matched_fields.join(', ')} · {item.status}. Human review required.</p>)}</details>
            <details><summary>AI Synthesis</summary>{summary.ai_explanation ? <><p>{summary.ai_explanation.evidence_summary}</p><p>Advisory: human review required. {summary.ai_explanation.disclaimer}</p></> : <p>No AI explanation generated. AI remains advisory and is not generated automatically.</p>}</details>
            <details><summary>Regulatory Review</summary><p>{summary.regulatory_review_areas.length} Potential Review Areas · {summary.regulatory_rule_matches.length} rule matches.</p><p><strong>Deterministic Rule Matches</strong></p>{summary.regulatory_rule_matches.map((rule) => <p key={rule.rule_id}><strong>{rule.rule_id}: {rule.condition_matched}</strong> {rule.review_area.rationale} {rule.review_area.section_hint}</p>)}<p>Potential review guidance only. It does not constitute a confirmed regulatory deficiency or proof of causality; final determinations require qualified professional review.</p></details>
            <details><summary>Documents</summary>{summary.documents.length ? summary.documents.map((doc) => <p key={doc.document_id}>{doc.filename} · {doc.analysis_status || 'Not analyzed'} · {doc.relevant_section_count} sections · {doc.potential_coverage_gap || 'No coverage gap returned'} · Human review required: {doc.human_review_required ? 'Yes' : 'No'}</p>) : <p>No documents are associated with this signal.</p>}</details>
            <details><summary>Human Review</summary><p>Status: {summary.human_review?.review_status || 'not_started'} · Checklist: {checklistCount(summary)} / 6</p><p>Notes: {summary.human_review?.reviewer_notes || 'None'}</p><p>Human-authored conclusion: {summary.human_review?.reviewer_conclusion || 'None'}</p></details>
          </div>
          <p className={styles.disclaimer}>Read-only aggregation of existing evidence. It does not establish causality or make a regulatory decision.</p>
        </>
      )}
    </section>
  );
}
