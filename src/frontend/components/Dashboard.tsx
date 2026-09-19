'use client';

import React from 'react';
import apiClient from '../lib/api';
import { Signal } from '../lib/api/types';
import { SignalListTable } from './SignalListTable';
import { LiveSearchWidget } from './LiveSearchWidget';
import { OnboardingModal } from './ui/OnboardingModal';
import styles from './Dashboard.module.css';

interface DashboardProps {
  onSelectSignal: (signal: Signal) => void;
}

export function Dashboard({ onSelectSignal }: DashboardProps) {
  const [showOnboarding, setShowOnboarding] = React.useState(false);

  React.useEffect(() => {
    const completed = localStorage.getItem('signaltrace_onboarding_completed');
    if (!completed) {
      setShowOnboarding(true);
    }
  }, []);

  const handleCloseOnboarding = () => {
    localStorage.setItem('signaltrace_onboarding_completed', 'true');
    setShowOnboarding(false);
  };

  return (
    <div className={styles.dashboardContainer}>
      <OnboardingModal isOpen={showOnboarding} onClose={handleCloseOnboarding} />
      <header className={styles.header}>
        <div><div className={styles.brand}>SignalTrace</div><div className={styles.headerContext}>Pharmacovigilance workspace</div></div>
        
        <div className={styles.headerControls}>
          <div className={styles.widgetWrapper}>
            <LiveSearchWidget apiClient={apiClient} />
          </div>
          <button className={styles.learnButton} type="button" onClick={() => setShowOnboarding(true)}>
            (?) Learn
          </button>
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
