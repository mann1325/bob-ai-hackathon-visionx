import React, { useEffect, useRef } from 'react';
import styles from './DocumentsModal.module.css';
import { DocumentWorkflow } from '../DocumentWorkflow';
import { AiExplanationPanel } from '../AiExplanationPanel';
import { ApiClient } from '../../lib/api/client';

interface DocumentsModalProps {
  view: 'upload' | 'ai' | null;
  onClose: () => void;
  signalId: string;
  apiClient: ApiClient;
}

export function DocumentsModal({ view, onClose, signalId, apiClient }: DocumentsModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!view) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [view, onClose]);

  if (!view) return null;

  return (
    <div className={styles.overlay} aria-modal="true" role="dialog">
      <div className={styles.modal} ref={modalRef}>
        <div className={styles.header}>
          <div className={styles.brandTitle}>
            {view === 'upload' ? 'Regulatory Documents' : 'AI Evidence Explanation'}
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>
        
        <div className={styles.body}>
          <div className={styles.contentWrapper}>
            {view === 'upload' && <DocumentWorkflow signalId={signalId} apiClient={apiClient} />}
            {view === 'ai' && (
              <div className={styles.aiSecondary}>
                <AiExplanationPanel signalId={signalId} apiClient={apiClient} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
