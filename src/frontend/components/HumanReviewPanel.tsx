'use client';

import React, { useEffect, useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { EvidenceChecklist, HumanReview, HumanReviewUpdate, ReviewStatus } from '../lib/api/types';
import styles from './HumanReviewPanel.module.css';

interface HumanReviewPanelProps {
  apiClient: ApiClient;
  signalId: string;
}

const checklistItems: Array<{ key: keyof EvidenceChecklist; label: string }> = [
  { key: 'supporting_reports_reviewed', label: 'Supporting reports reviewed' },
  { key: 'case_quality_reviewed', label: 'Case quality reviewed' },
  { key: 'reporting_trend_reviewed', label: 'Reporting trend reviewed' },
  { key: 'duplicates_reviewed', label: 'Duplicate candidates reviewed' },
  { key: 'ai_explanation_reviewed', label: 'AI explanation reviewed' },
  { key: 'regulatory_documents_reviewed', label: 'Regulatory/document evidence reviewed' },
];

const blankChecklist = (): EvidenceChecklist => ({
  supporting_reports_reviewed: false,
  case_quality_reviewed: false,
  reporting_trend_reviewed: false,
  duplicates_reviewed: false,
  ai_explanation_reviewed: false,
  regulatory_documents_reviewed: false,
});

export function HumanReviewPanel({ apiClient, signalId }: HumanReviewPanelProps) {
  const [review, setReview] = useState<HumanReview | null>(null);
  const [status, setStatus] = useState<ReviewStatus>('not_started');
  const [checklist, setChecklist] = useState<EvidenceChecklist>(blankChecklist);
  const [notes, setNotes] = useState('');
  const [conclusion, setConclusion] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    apiClient.getReview(signalId)
      .then((saved) => {
        if (!active) return;
        setReview(saved);
        setStatus(saved.review_status);
        setChecklist({ ...blankChecklist(), ...saved.evidence_checklist });
        setNotes(saved.reviewer_notes);
        setConclusion(saved.reviewer_conclusion);
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : 'Failed to load human review.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiClient, signalId]);

  const save = async () => {
    if (status === 'reviewed' && review?.review_status !== 'reviewed' && !window.confirm('Mark this signal as reviewed? Confirm that the evidence checklist and conclusion are complete.')) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    const payload: HumanReviewUpdate = {
      review_status: status,
      evidence_checklist: checklist,
      reviewer_notes: notes,
      reviewer_conclusion: conclusion,
    };
    try {
      const saved = await apiClient.saveReview(signalId, payload);
      setReview(saved);
      setMessage('Review saved.');
    } catch (requestError: unknown) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to save human review.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={styles.panel} aria-labelledby="human-review-heading">
      <div className={styles.header}>
        <div>
          <h2 id="human-review-heading">Human Review</h2>
          <p>Reviewer-controlled assessment. AI and deterministic outputs remain advisory.</p>
        </div>
        {review?.updated_at && <time dateTime={review.updated_at}>Saved {new Date(review.updated_at).toLocaleString()}</time>}
      </div>
      {loading ? <div className={styles.state}>Loading review state...</div> : (
        <>
          <div className={styles.progressSummary}><strong>{Object.values(checklist).filter(Boolean).length} of {checklistItems.length} evidence areas reviewed</strong><span>Complete the checklist before marking the signal reviewed.</span></div>
          <label className={styles.fieldLabel} htmlFor="review-status">Review Status</label>
          <select id="review-status" className={styles.select} value={status} onChange={(event) => setStatus(event.target.value as ReviewStatus)}>
            <option value="not_started">Not Started</option>
            <option value="in_review">In Review</option>
            <option value="reviewed">Reviewed</option>
          </select>

          <fieldset className={styles.checklist}>
            <legend>Evidence Checklist</legend>
            {checklistItems.map((item) => (
              <label className={styles.checkboxRow} key={item.key}>
                <input
                  type="checkbox"
                  checked={checklist[item.key]}
                  onChange={(event) => setChecklist((current) => ({ ...current, [item.key]: event.target.checked }))}
                />
                <span>{item.label}</span>
              </label>
            ))}
          </fieldset>

          <label className={styles.fieldLabel} htmlFor="reviewer-notes">Reviewer Notes</label>
          <textarea id="reviewer-notes" className={styles.textarea} value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} />

          <label className={styles.fieldLabel} htmlFor="reviewer-conclusion">Reviewer Conclusion <span>Human-authored conclusion</span></label>
          <textarea id="reviewer-conclusion" className={styles.textarea} value={conclusion} onChange={(event) => setConclusion(event.target.value)} rows={4} />

          {error && <div className={styles.error} role="alert">{error}</div>}
          {message && <div className={styles.success} role="status">{message}</div>}
          <button className={styles.saveButton} type="button" onClick={() => void save()} disabled={saving}>
            {saving ? 'Saving Review...' : 'Save Review'}
          </button>
        </>
      )}
    </section>
  );
}