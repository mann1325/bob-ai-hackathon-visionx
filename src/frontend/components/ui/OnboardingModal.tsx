import React, { useEffect, useRef, useState } from 'react';
import styles from './OnboardingModal.module.css';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function OnboardingModal({ isOpen, onClose }: OnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) {
      setCurrentStep(0);
      return;
    }
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleNext = () => {
    if (currentStep < 2) {
      setCurrentStep(curr => curr + 1);
    } else {
      onClose();
    }
  };

  const steps = [
    {
      title: "How SignalTrace works",
      subtitle: "Understand the signals",
      content: (
        <div className={styles.stepContent}>
          <p className={styles.paragraph}>
            SignalTrace analyzes adverse-event reports to identify drug-event combinations that occur more often than expected. It uses statistical signal detection metrics to help pharmacovigilance teams prioritize what should be reviewed.
          </p>
          <div className={styles.flowchart}>
            <div className={styles.flowBox}>Adverse-event reports</div>
            <div className={styles.flowArrow}>↓</div>
            <div className={styles.flowBox}>Drug–event combinations</div>
            <div className={styles.flowArrow}>↓</div>
            <div className={styles.flowBox}>Statistical analysis (PRR & ROR)</div>
            <div className={styles.flowArrow}>↓</div>
            <div className={styles.flowBox}>Signal prioritization</div>
            <div className={styles.flowArrow}>↓</div>
            <div className={styles.flowBoxAccent}>Human pharmacovigilance review</div>
          </div>
          <p className={styles.disclaimer}>
            <strong>SignalTrace is a decision-support tool.</strong> It identifies statistical reporting signals that may warrant further investigation. It does not prove that a drug caused an adverse event.
          </p>
        </div>
      )
    },
    {
      title: "PRR & ROR",
      subtitle: "Statistical Signals Explained",
      content: (
        <div className={styles.stepContent}>
          <div className={styles.metricsGrid}>
            <div className={styles.metricCard}>
              <h3>PRR — Proportional Reporting Ratio</h3>
              <p>PRR compares how frequently an adverse event is reported for a specific drug with how frequently the same event is reported for other drugs.</p>
              <ul className={styles.metricList}>
                <li><strong>PRR &gt; 1:</strong> Reported proportionally more often.</li>
                <li><strong>PRR ≈ 1:</strong> Reporting is broadly proportional.</li>
                <li><strong>PRR &lt; 1:</strong> Reported proportionally less often.</li>
              </ul>
            </div>
            
            <div className={styles.metricCard}>
              <h3>ROR — Reporting Odds Ratio</h3>
              <p>ROR compares the odds of reporting a specific adverse event for a drug against the odds of reporting that event for other drugs.</p>
              <ul className={styles.metricList}>
                <li><strong>ROR &gt; 1:</strong> Relatively higher reporting odds.</li>
                <li><strong>ROR ≈ 1:</strong> Similar reporting odds.</li>
                <li><strong>ROR &lt; 1:</strong> Relatively lower reporting odds.</li>
              </ul>
            </div>
          </div>
          
          <div className={styles.disclaimerWarning}>
            <span role="img" aria-label="warning">⚠️</span> Statistical signals support safety review; they do not establish formal causality.
          </div>
        </div>
      )
    },
    {
      title: "How to read this queue",
      subtitle: "Dashboard Reference",
      content: (
        <div className={styles.stepContent}>
          <p className={styles.paragraph}>
            SignalTrace uses these measures alongside report volume and other evidence to prioritize candidate signals for your review.
          </p>
          <dl className={styles.definitionList}>
            <div className={styles.defItem}>
              <dt>Reports</dt>
              <dd>Number of adverse-event reports associated with the drug-event combination.</dd>
            </div>
            <div className={styles.defItem}>
              <dt>PRR & ROR</dt>
              <dd>Proportional reporting strength and reporting odds strength (statistical flags).</dd>
            </div>
            <div className={styles.defItem}>
              <dt>Priority</dt>
              <dd>SignalTrace's current review-priority classification (Critical, High, Medium, Low).</dd>
            </div>
            <div className={styles.defItem}>
              <dt>Review Status</dt>
              <dd>Current workflow status of the signal within your team.</dd>
            </div>
          </dl>
          <div className={styles.disclaimerNote}>
            Note: "Critical", "Low", etc. are prioritization labels and absolutely not clinical conclusions.
          </div>
        </div>
      )
    }
  ];

  return (
    <div className={styles.overlay} aria-modal="true" role="dialog">
      <div className={styles.modal} ref={modalRef}>
        <div className={styles.header}>
          <div className={styles.brandTitle}>SignalTrace</div>
          <div className={styles.stepTracker}>
            {currentStep + 1} of 3
          </div>
        </div>
        
        <div className={styles.body}>
          <h2 className={styles.title}>{steps[currentStep].title}</h2>
          <h3 className={styles.subtitle}>{steps[currentStep].subtitle}</h3>
          
          <div className={styles.contentArea}>
            {steps[currentStep].content}
          </div>
        </div>
        
        <div className={styles.footer}>
          <div className={styles.footerDots}>
            {[0, 1, 2].map((idx) => (
              <span key={idx} className={`${styles.dot} ${idx <= currentStep ? styles.activeDot : ''}`}></span>
            ))}
          </div>
          
          <div className={styles.actions}>
            <button className={styles.skipBtn} onClick={onClose} type="button">
              Skip
            </button>
            <button className={styles.continueBtn} onClick={handleNext} type="button">
              {currentStep === 2 ? 'Start reviewing' : 'Continue'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
