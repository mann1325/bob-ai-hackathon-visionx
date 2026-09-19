'use client';

import React from 'react';
import apiClient from '../lib/api';
import { Signal } from '../lib/api/types';
import { SignalListTable } from './SignalListTable';
import { LiveSearchWidget } from './LiveSearchWidget';
import styles from './Dashboard.module.css';

interface DashboardProps {
  onSelectSignal: (signal: Signal) => void;
}

export function Dashboard({ onSelectSignal }: DashboardProps) {
  return (
    <div className={styles.dashboardContainer}>
      <header className={styles.header}>
        <div><div className={styles.brand}>SignalTrace</div><div className={styles.headerContext}>Pharmacovigilance workspace</div></div>
        
        <div className={styles.widgetWrapper}>
          <LiveSearchWidget apiClient={apiClient} />
        </div>
      </header>

      <main className={styles.mainContent}>
        <section className={styles.tableSection}>
          <SignalListTable apiClient={apiClient} onSelectSignal={onSelectSignal} />
        </section>
      </main>
    </div>
  );
}
