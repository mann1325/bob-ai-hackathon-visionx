import React from 'react';
import styles from './AILabel.module.css';

interface AILabelProps {
  label: string;
  value: React.ReactNode;
  inline?: boolean;
}

export function AILabel({ label, value, inline = false }: AILabelProps) {
  return (
    <div className={`${styles.container} ${inline ? styles.inline : ''}`}>
      <div className={styles.header}>
        <span className={styles.label}>{label}</span>
        <div className={styles.aiBadge}>
          <svg
            className={styles.icon}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2v20" />
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
          AI-Assisted — Human Review Required
        </div>
      </div>
      <div className={styles.valueWrapper}>
        {value}
      </div>
    </div>
  );
}
