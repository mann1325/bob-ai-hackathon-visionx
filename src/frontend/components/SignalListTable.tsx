'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { ApiClient } from '../lib/api/client';
import { Signal } from '../lib/api/types';
import styles from './SignalListTable.module.css';

interface SignalListTableProps {
  apiClient: ApiClient;
  onSelectSignal?: (signal: Signal) => void;
}

export function SignalListTable({ apiClient, onSelectSignal }: SignalListTableProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  type SortKey = keyof Signal;
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: 'asc' | 'desc' } | null>(null);

  const requestSort = (key: SortKey) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    apiClient.listSignals()
      .then(setSignals)
      .catch((err: any) => setError(err.message || 'Failed to load signals.'))
      .finally(() => setIsLoading(false));
  }, [apiClient]);

  const sortedAndFilteredSignals = useMemo(() => {
    let result = signals;
    if (searchTerm.trim()) {
      const lower = searchTerm.toLowerCase();
      result = result.filter(
        (s) => s.drug_name.toLowerCase().includes(lower) || s.event_name.toLowerCase().includes(lower)
      );
    }
    
    if (sortConfig !== null) {
      result = [...result].sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        // Null handling: always sort nulls to the bottom regardless of direction to keep UI clean
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        if (aVal < bVal) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aVal > bVal) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    
    return result;
  }, [signals, searchTerm, sortConfig]);

  return (
    <div className={styles.tableContainer}>
      <div className={styles.searchHeader}>
        <input 
          type="text" 
          placeholder="Filter signals by drug or event name..." 
          className={styles.searchInput}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.signalTable}>
          <thead>
            <tr>
              <th onClick={() => requestSort('drug_name')}>Drug Name {sortConfig?.key === 'drug_name' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('event_name')}>Event Name {sortConfig?.key === 'event_name' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('supporting_report_count')}>Reports {sortConfig?.key === 'supporting_report_count' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('prr')}>PRR {sortConfig?.key === 'prr' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('ror')}>ROR {sortConfig?.key === 'ror' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('trend_score')}>Trend Score {sortConfig?.key === 'trend_score' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('priority_level')}>Priority Level {sortConfig?.key === 'priority_level' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              <th onClick={() => requestSort('candidate_status')}>Status {sortConfig?.key === 'candidate_status' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={`skeleton-${i}`}>
                  <td colSpan={8}>
                    <div className={styles.skeletonPulse}></div>
                  </td>
                </tr>
              ))
            ) : error ? (
              <tr>
                <td colSpan={8}>
                  <div className={styles.errorState}>
                    ⚠ {error}
                  </div>
                </td>
              </tr>
            ) : sortedAndFilteredSignals.length === 0 ? (
              <tr>
                <td colSpan={8}>
                  <div className={styles.emptyState}>
                    No signals found matching your criteria.
                  </div>
                </td>
              </tr>
            ) : (
              sortedAndFilteredSignals.map(signal => (
                <tr 
                  key={signal.signal_id} 
                  onClick={() => onSelectSignal && onSelectSignal(signal)}
                  className={onSelectSignal ? styles.clickableRow : ''}
                >
                  <td className={styles.boldCell}>{signal.drug_name}</td>
                  <td>{signal.event_name}</td>
                  <td className={styles.numericCell}>{signal.supporting_report_count}</td>
                  <td className={styles.numericCell}>{signal.prr.toFixed(2)}</td>
                  <td className={styles.numericCell}>
                    {signal.ror !== null && signal.ror !== undefined ? signal.ror.toFixed(2) : '--'}
                  </td>
                  <td className={styles.numericCell}>
                    {signal.trend_score !== null && signal.trend_score !== undefined 
                      ? `${signal.trend_score > 0 ? '+' : ''}${signal.trend_score.toFixed(1)}%` 
                      : '--'}
                  </td>
                  <td>
                    <span className={`${styles.badge} ${signal.priority_level ? styles[signal.priority_level] : styles.unscored}`}>
                      {signal.priority_level ? signal.priority_level : 'UNSCORED'}
                    </span>
                  </td>
                  <td>
                    <span className={styles.statusBadge}>
                      {signal.candidate_status.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
