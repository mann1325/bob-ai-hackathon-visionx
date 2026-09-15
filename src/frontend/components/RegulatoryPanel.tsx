'use client';

import React, { useEffect, useState } from 'react';
import defaultApiClient from '../lib/api';
import { ApiClient } from '../lib/api/client';
import { RegulatoryImpact, ReviewArea } from '../lib/api/types';
import styles from './RegulatoryPanel.module.css';

interface RegulatoryPanelProps {
  apiClient?: ApiClient;
  signalId?: string;
}

function reviewAreaKey(area: ReviewArea, index: number): string {
  return `${area.document_type}-${index}`;
}

export function RegulatoryPanel({ apiClient = defaultApiClient, signalId = 'SIG-1001' }: RegulatoryPanelProps) {
  const [impact, setImpact] = useState<RegulatoryImpact | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const loadImpact = async () => {
      setIsLoading(true);
      setError(null);
      try {
        setImpact(await apiClient.getRegulatoryImpact(signalId));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load regulatory impact.');
      } finally {
        setIsLoading(false);
      }
    };

    void loadImpact();
  }, [apiClient, signalId]);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className={styles.panelContainer}>
      <header className={styles.banner}>
        <span>REGULATORY REVIEW IMPACT</span>
        <span className={styles.engineTag}>DETERMINISTIC RULE ENGINE</span>
      </header>

      {isLoading && <div className={styles.itemDetails}>Evaluating signal-specific rules...</div>}
      {error && <div className={styles.itemDetails}>{error}</div>}

      {!isLoading && !error && impact && (
        <>
          <section className={styles.reviewSection}>
            <h2 className={styles.sectionHeading}>Potential Review Areas</h2>
            <div className={styles.sectionGrid}>
              {impact.review_areas.length === 0 ? (
                <div className={styles.emptyState}>No potential review areas matched.</div>
              ) : (
                impact.review_areas.map((area, index) => {
                  const id = reviewAreaKey(area, index);
                  const isExpanded = expandedId === id;
                  return (
                    <div
                      key={id}
                      className={`${styles.itemRow} ${styles.reviewRow} ${isExpanded ? styles.expanded : ''}`}
                      onClick={() => toggleExpand(id)}
                    >
                      <div className={styles.itemStatus}>
                        <div className={styles.iconPending} title="Potential review area" />
                      </div>
                      <div className={styles.itemContent}>
                        <div className={styles.itemHeader}>
                          <h3 className={styles.itemTitle}>{area.document_type}</h3>
                          <div className={styles.headerRight}>
                            <span className={styles.itemTarget}>{area.priority || 'medium'} priority</span>
                            <span className={styles.chevron}>{isExpanded ? '▼' : '►'}</span>
                          </div>
                        </div>
                        {isExpanded && (
                          <div className={styles.itemDetails}>
                            {area.section_hint && <p className={styles.itemDescription}>{area.section_hint}</p>}
                            {area.rationale && <p className={styles.itemDescription}>{area.rationale}</p>}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>

          <section className={styles.ruleSection}>
            <h2 className={styles.sectionHeading}>Deterministic Rule Matches</h2>
            <div className={styles.sectionGrid}>
              {impact.rule_matches.length === 0 ? (
                <div className={styles.emptyState}>No deterministic rule matches.</div>
              ) : (
                impact.rule_matches.map((match) => (
                  <div key={match.rule_id} className={`${styles.itemRow} ${styles.ruleRow}`}>
                    <div className={styles.itemStatus}>
                      <div className={styles.iconPending} title="Deterministic rule match" />
                    </div>
                    <div className={styles.itemContent}>
                      <div className={styles.itemHeader}>
                        <h3 className={styles.itemTitle}>{match.rule_id}: {match.rule_name}</h3>
                      </div>
                      <div className={styles.itemDetails}>
                        <p className={styles.itemDescription}>{match.condition_matched}</p>
                        {match.confidence_rationale && <p className={styles.itemDescription}>{match.confidence_rationale}</p>}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          <div className={styles.reviewNotice}>
            <p className={styles.itemDescription}>
              {impact.human_review_required ? 'Human review required.' : 'Human review not required.'}
            </p>
            <p className={styles.disclaimer}>{impact.disclaimer}</p>
          </div>
        </>
      )}
    </div>
  );
}
