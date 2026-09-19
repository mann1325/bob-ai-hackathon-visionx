'use client';

import React, { useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { LiveSearchResponse } from '../lib/api/types';
import styles from './LiveSearchWidget.module.css';

interface LiveSearchWidgetProps {
  apiClient: ApiClient;
}

export function LiveSearchWidget({ apiClient }: LiveSearchWidgetProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LiveSearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isDegraded, setIsDegraded] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setIsSearching(true);
    setIsDegraded(false);
    setResults(null);

    try {
      const data = await apiClient.liveSearch(query);
      setResults(data);
    } catch {
      setIsDegraded(true);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className={styles.widgetContainer}>
      <header className={styles.header}>
        <div className={styles.trackerPill}>
          <div className={`${styles.statusDot} ${isDegraded ? styles.degraded : ''}`} />
          Search FDA labels
        </div>
        <div className={styles.controls}>
          <button onClick={() => setIsCollapsed(!isCollapsed)} className={styles.iconBtn} aria-label="Toggle Collapse">
            {isCollapsed ? '□' : '—'}
          </button>
          <button onClick={() => setIsDismissed(true)} className={styles.iconBtn} aria-label="Dismiss">
            ✕
          </button>
        </div>
      </header>

      {!isCollapsed ? (
        <div className={styles.content}>
          <form className={styles.inputWrapper} onSubmit={handleSearch}>
            <input 
              type="text" 
              placeholder="Drug name (e.g. Paxlovid)" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={styles.searchInput}
              disabled={isSearching}
            />
            <button type="submit" className={styles.searchBtn} disabled={isSearching || !query}>
              {isSearching ? (
                <svg className={styles.spinner} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                </svg>
              ) : 'Search'}
            </button>
          </form>

          {isDegraded && (
            <div className={styles.demoErrorState}>
              <span>Unable to complete search</span>
              <button className={styles.retryLinkBtn} onClick={handleSearch} disabled={!query}>Try again</button>
            </div>
          )}

          {!isDegraded && isSearching && (
            <div className={styles.demoLoadingState}>
              <span>Searching signals...</span>
              <span className={styles.spinnerIcon}>◌</span>
            </div>
          )}

          {!isDegraded && !isSearching && results && (
            <div className={styles.resultsArea}>
              <div className={styles.demoSuccessState}>✓ Search complete</div>
              Found <strong>{results.total}</strong> external drug label results for <strong>{results.query}</strong>.
              <br />
              <small>{results.disclaimer}</small>
            </div>
          )}
        </div>
      ) : (
        <div className={styles.collapsedState}>
          Search utility collapsed
        </div>
      )}
    </div>
  );
}
