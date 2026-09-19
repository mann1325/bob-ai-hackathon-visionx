'use client';

import React, { useState } from 'react';
import apiClient from '../lib/api';
import { Signal } from '../lib/api/types';
import { SignalMetricsDetail } from './SignalMetricsDetail';
import { RegulatoryPanel } from './RegulatoryPanel';
import { AiExplanationPanel } from './AiExplanationPanel';
import { DocumentWorkflow } from './DocumentWorkflow';
import { HumanReviewPanel } from './HumanReviewPanel';
import { InvestigationSummary } from './InvestigationSummary';
import { EvidenceExplorer } from './EvidenceExplorer';
import styles from './SignalDetail.module.css';

interface SignalDetailProps { signal: Signal; onBack: () => void; }
type InvestigationTab = 'overview' | 'evidence' | 'quality' | 'regulatory' | 'documents' | 'review';

const tabs: Array<{ id: InvestigationTab; label: string }> = [
  { id: 'overview', label: 'Overview' }, { id: 'evidence', label: 'Evidence' }, { id: 'quality', label: 'Quality / Duplicates' },
  { id: 'regulatory', label: 'Regulatory' }, { id: 'documents', label: 'Documents' }, { id: 'review', label: 'Human Review' },
];

export function SignalDetail({ signal, onBack }: SignalDetailProps) {
  const [activeTab, setActiveTab] = useState<InvestigationTab>('overview');
  const statusLabel = signal.candidate_status.replace('_', ' ');

  return (
    <div className={styles.detailContainer}>
      <header className={styles.header}>
        <div className={styles.headerTop}><button onClick={onBack} className={styles.backBtn} type="button">← Signal Queue</button><span className={styles.contextLabel}>Signal investigation</span></div>
        <div className={styles.signalIdentity}><div><h1>{signal.drug_name}</h1><p>{signal.event_name}</p></div><span className={`${styles.priorityBadge} ${signal.priority_level ? styles[signal.priority_level] : styles.unscored}`}>{signal.priority_level || 'Unscored'} priority</span></div>
        <dl className={styles.contextMeta}><div><dt>Signal ID</dt><dd>{signal.signal_id}</dd></div><div><dt>Review status</dt><dd>{statusLabel}</dd></div><div><dt>Dataset / release</dt><dd>{signal.dataset_version || 'Unavailable'}</dd></div><div><dt>Reports</dt><dd>{signal.supporting_report_count.toLocaleString()}</dd></div></dl>
      </header>
      <nav className={styles.tabs} aria-label="Investigation sections">{tabs.map((tab) => <button key={tab.id} type="button" className={activeTab === tab.id ? styles.activeTab : ''} aria-current={activeTab === tab.id ? 'page' : undefined} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}</nav>
      <main className={styles.content}>
        <section className={styles.section} aria-labelledby="overview-heading" hidden={activeTab !== 'overview'} aria-hidden={activeTab !== 'overview'}><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>What needs attention now</p><h2 id="overview-heading">Investigation overview</h2></div><span className={styles.advisory}>Candidate signal · human review required</span></div><InvestigationSummary signalId={signal.signal_id} apiClient={apiClient} /></section>
        <section className={styles.section} aria-labelledby="evidence-heading" hidden={activeTab !== 'evidence'} aria-hidden={activeTab !== 'evidence'}><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>Deterministic source data</p><h2 id="evidence-heading">Supporting evidence</h2></div><span className={styles.sectionHint}>FAERS reports linked to this signal</span></div><EvidenceExplorer signalId={signal.signal_id} apiClient={apiClient} reportCount={signal.supporting_report_count} /></section>
        <section className={styles.section} aria-labelledby="quality-heading" hidden={activeTab !== 'quality'} aria-hidden={activeTab !== 'quality'}><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>Data integrity and triage</p><h2 id="quality-heading">Quality and duplicates</h2></div></div><SignalMetricsDetail signalId={signal.signal_id} apiClient={apiClient} /></section>
        <section className={styles.section} aria-labelledby="regulatory-heading" hidden={activeTab !== 'regulatory'} aria-hidden={activeTab !== 'regulatory'}><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>Deterministic rule mapping</p><h2 id="regulatory-heading">Regulatory impact</h2></div><span className={styles.sectionHint}>Potential review areas only</span></div><RegulatoryPanel signalId={signal.signal_id} apiClient={apiClient} /></section>
        <section className={styles.section} aria-labelledby="documents-heading" hidden={activeTab !== 'documents'} aria-hidden={activeTab !== 'documents'}><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>Document intelligence</p><h2 id="documents-heading">Regulatory documents</h2></div></div><DocumentWorkflow signalId={signal.signal_id} apiClient={apiClient} /><div className={styles.aiSecondary}><AiExplanationPanel signalId={signal.signal_id} apiClient={apiClient} /></div></section>
        <section className={styles.section} aria-labelledby="review-heading" hidden={activeTab !== 'review'} aria-hidden={activeTab !== 'review'}><div className={styles.sectionHeader}><div><p className={styles.eyebrow}>Final decision workflow</p><h2 id="review-heading">Human review</h2></div><span className={styles.advisory}>Reviewer-controlled assessment</span></div><HumanReviewPanel signalId={signal.signal_id} apiClient={apiClient} /></section>
      </main>
    </div>
  );
}
