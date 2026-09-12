'use client';

import React, { useState, useEffect } from 'react';
import apiClient from '../lib/api';
import { Signal } from '../shared-schemas/types';
import styles from './Dashboard.module.css';

interface DashboardProps {
  onSelectSignal: (signal: Signal) => void;
}

export function Dashboard({ onSelectSignal }: DashboardProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<any>(null);

  useEffect(() => {
    // Load baseline candidate signals
    apiClient.getSignals().then(setSignals).catch(console.error);
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    setSearchResults(null);

    try {
      const results = await apiClient.liveSearch(searchTerm);
      setSearchResults(results);
    } catch (err) {
      // Graceful fallback for openFDA / live-search
      setSearchError('Live search data (openFDA) is currently unavailable. Core signal dashboard remains fully operational.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className={styles.dashboardContainer}>
      <header className={styles.header}>
        <div className={styles.brand}>SignalTrace</div>
        <form onSubmit={handleSearch} className={styles.searchForm}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search openFDA drug data (try 'fail' to test fallback)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button type="submit" className={styles.searchButton} disabled={isSearching}>
            {isSearching ? <span className={styles.spinner} /> : 'Search'}
          </button>
        </form>
      </header>

      {searchError && (
        <div className={styles.dismissibleAlert}>
          <div className={styles.alertContent}>
            <span className={styles.alertIcon}>⚠️</span>
            <span>{searchError}</span>
          </div>
          <button className={styles.dismissBtn} onClick={() => setSearchError(null)}>×</button>
        </div>
      )}

      {searchResults && (
        <div className={styles.searchResultsPanel}>
          <h3 className={styles.panelTitle}>Live Search Findings for "{searchTerm}"</h3>
          <div className={styles.searchData}>
            Safety Reports Found: {searchResults.results?.[0]?.safety_reports || 'N/A'}
          </div>
        </div>
      )}

      <main className={styles.mainContent}>
        <h2 className={styles.sectionTitle}>Active Signals</h2>
        <div className={styles.signalsGrid}>
          {signals.map((signal) => (
            <div key={signal.signal_id} className={styles.signalCard}>
              <div className={styles.signalHeader}>
                <h3 className={styles.drugName}>{signal.drug_name}</h3>
                <span className={`${styles.statusBadge} ${styles[signal.candidate_status]}`}>
                  {signal.candidate_status.replace('_', ' ')}
                </span>
              </div>
              <p className={styles.eventName}>{signal.event_name}</p>
              
              <div className={styles.metricsRow}>
                <div className={styles.metric}>
                  <span className={styles.metricValue}>{signal.supporting_report_count}</span>
                  <span className={styles.metricLabel}>Reports</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricValue}>{signal.prr.toFixed(1)}</span>
                  <span className={styles.metricLabel}>PRR</span>
                </div>
                {signal.ror !== null && signal.ror !== undefined && (
                  <div className={styles.metric}>
                    <span className={styles.metricValue}>{signal.ror.toFixed(1)}</span>
                    <span className={styles.metricLabel}>ROR</span>
                  </div>
                )}
              </div>

              <div className={styles.cardFooter}>
                <button 
                  className={styles.viewDetailsBtn}
                  onClick={() => onSelectSignal(signal)}
                >
                  Review Signal
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
