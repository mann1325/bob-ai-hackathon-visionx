'use client';

import React from 'react';
import apiClient from '../lib/api';
import { Signal } from '../lib/api/types';
import { SignalMetricsDetail } from './SignalMetricsDetail';
import { RegulatoryPanel } from './RegulatoryPanel';
import { AiExplanationPanel } from './AiExplanationPanel';
import { DocumentWorkflow } from './DocumentWorkflow';
import styles from './SignalDetail.module.css';

interface SignalDetailProps {
  signal: Signal;
  onBack: () => void;
}

export function SignalDetail({ signal, onBack }: SignalDetailProps) {
  return (
    <div className={styles.detailContainer}>
      {/* Header Shell */}
      <header className={styles.header}>
        <button onClick={onBack} className={styles.backBtn}>← Back to Signal Queue</button>
        <div className={styles.titleSection}>
          <h1 className={styles.drugName}>{signal.drug_name}</h1>
          <span className={styles.eventName}>{signal.event_name}</span>
        </div>
        <span className={styles.statusBadge}>
          {signal.candidate_status.replace('_', ' ')}
        </span>
      </header>

      <div className={styles.gridLayout}>
        {/* Left Column: Metrics & Regulatory */}
        <div className={styles.leftColumn}>
          <SignalMetricsDetail signalId={signal.signal_id} apiClient={apiClient} />
          
          <div className={styles.spacer}></div>
          
          <RegulatoryPanel />
        </div>

        {/* Right Column: AI Inference & Workflow */}
        <div className={styles.rightColumn}>
          <AiExplanationPanel signalId={signal.signal_id} apiClient={apiClient} />
          
          <div className={styles.spacer}></div>
          
          <DocumentWorkflow signalId={signal.signal_id} apiClient={apiClient} />
        </div>
      </div>
    </div>
  );
}
