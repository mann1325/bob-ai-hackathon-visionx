'use client';

import React, { useState } from 'react';
import styles from './RegulatoryPanel.module.css';

interface MappedArea {
  id: string;
  title: string;
  target: string;
  description: string;
  status: 'unlisted' | 'compliant' | 'pending';
  tags: { label: string; isHighlight?: boolean }[];
}

const REVIEW_AREAS: MappedArea[] = [
  {
    id: 'M1',
    title: 'Module 1: Administrative Information',
    target: 'Score: 100%',
    description: 'Regional administrative data and prescribing information format strictly conforms to local authority requirements.',
    status: 'compliant',
    tags: [
      { label: 'Validated' }
    ]
  },
  {
    id: 'M2',
    title: 'Module 2: CTD Summaries',
    target: 'Score: 82% (GAP DETECTED)',
    description: 'Clinical Overview (Section 2.5) is missing an integrated safety narrative for newly flagged hepatotoxicity occurrences.',
    status: 'unlisted',
    tags: [
      { label: 'GAP REPORT: Missing Section 2.5', isHighlight: true },
      { label: 'Requires AI Synthesis' }
    ]
  },
  {
    id: 'M3',
    title: 'Module 3: Quality',
    target: 'Score: 95%',
    description: 'Chemical, pharmaceutical, and biological documentation check complete. Minor formatting issues pending.',
    status: 'pending',
    tags: [
      { label: 'DUE: Q3 2026' }
    ]
  },
  {
    id: 'M4 / M5',
    title: 'Modules 4 & 5: Study Reports',
    target: 'Score: 65% (CRITICAL GAPS)',
    description: 'Efficacy reports complete, but Section 5.3.5 (Reports of Efficacy and Safety Studies) is missing post-market surveillance statistics and calculated PRR models.',
    status: 'unlisted',
    tags: [
      { label: 'GAP REPORT: Clinical Safety Docs', isHighlight: true },
      { label: '15-DAY SUBMISSION THRESHOLD', isHighlight: true }
    ]
  }
];

export function RegulatoryPanel() {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className={styles.panelContainer}>
      <header className={styles.banner}>
        <span>SUBMISSION READINESS</span>
        <span className={styles.engineTag}>ICH M4 CTD DOSSIER & GAP ENFORCER</span>
      </header>

      <div className={styles.sectionGrid}>
        {REVIEW_AREAS.map(area => {
          const isExpanded = expandedId === area.id;
          return (
            <div 
              key={area.id} 
              className={`${styles.itemRow} ${isExpanded ? styles.expanded : ''}`}
              onClick={() => toggleExpand(area.id)}
            >
              <div className={styles.itemStatus}>
                {area.status === 'unlisted' && <div className={styles.iconUnlisted} title="Unlisted / Deficient" />}
                {area.status === 'compliant' && <div className={styles.iconCompliant} title="Compliant" />}
                {area.status === 'pending' && <div className={styles.iconPending} title="Pending Update" />}
              </div>
              
              <div className={styles.itemContent}>
                <div className={styles.itemHeader}>
                  <h3 className={styles.itemTitle}>{area.id}. {area.title}</h3>
                  <div className={styles.headerRight}>
                    <span className={styles.itemTarget}>{area.target}</span>
                    <span className={styles.chevron}>{isExpanded ? '▼' : '►'}</span>
                  </div>
                </div>
                
                {isExpanded && (
                  <div className={styles.itemDetails}>
                    <p className={styles.itemDescription}>{area.description}</p>
                    
                    <div className={styles.tagGroup}>
                      {area.tags.map((tag, idx) => (
                        <span 
                          key={idx} 
                          className={`${styles.tag} ${tag.isHighlight ? styles.highlight : ''}`}
                        >
                          {tag.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
