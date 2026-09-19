'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { Signal, SignalListResponse } from '../lib/api/types';
import styles from './SignalListTable.module.css';

interface SignalListTableProps { apiClient: ApiClient; onSelectSignal?: (signal: Signal) => void; }
type SortKey = keyof Signal;
const PAGE_SIZE = 10;

const priorityClass = (priority: Signal['priority_level']): string => priority || 'unscored';

export function SignalListTable({ apiClient, onSelectSignal }: SignalListTableProps) {
  const [signalResponse, setSignalResponse] = useState<SignalListResponse>({ items: [], total: 0, page: 1, page_size: 20, pages: 1 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: 'asc' | 'desc' } | null>(null);
  const hasLoadedSignals = useRef(false);

  useEffect(() => {
    if (hasLoadedSignals.current) return;
    hasLoadedSignals.current = true;
    const loadSignals = async () => {
      setIsLoading(true); setError(null);
      try { setSignalResponse(await apiClient.listSignals()); }
      catch (err: unknown) { setError(err instanceof Error ? err.message : 'Failed to load signals.'); }
      finally { setIsLoading(false); }
    };
    void loadSignals();
  }, [apiClient]);

  const filteredSignals = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    const filtered = signalResponse.items.filter((signal) => {
      const matchesSearch = !query || signal.drug_name.toLowerCase().includes(query) || signal.event_name.toLowerCase().includes(query);
      return matchesSearch && (priorityFilter === 'all' || signal.priority_level === priorityFilter) && (statusFilter === 'all' || signal.candidate_status === statusFilter);
    });
    if (!sortConfig) return filtered;
    return [...filtered].sort((left, right) => {
      const leftValue = left[sortConfig.key]; const rightValue = right[sortConfig.key];
      if (leftValue == null) return 1; if (rightValue == null) return -1;
      const result = leftValue < rightValue ? -1 : leftValue > rightValue ? 1 : 0;
      return sortConfig.direction === 'asc' ? result : -result;
    });
  }, [priorityFilter, searchTerm, signalResponse.items, sortConfig, statusFilter]);

  const pageCount = Math.max(1, Math.ceil(filteredSignals.length / PAGE_SIZE));
  const visibleSignals = filteredSignals.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const reviewCount = signalResponse.items.filter((signal) => signal.candidate_status !== 'closed').length;
  const selectSignal = (signal: Signal) => onSelectSignal?.(signal);
  const resetFilters = () => { setSearchTerm(''); setPriorityFilter('all'); setStatusFilter('all'); setPage(1); };
  const requestSort = (key: SortKey) => setSortConfig((current) => current?.key === key && current.direction === 'asc' ? { key, direction: 'desc' } : { key, direction: 'asc' });
  const sortLabel = (key: SortKey) => sortConfig?.key === key ? (sortConfig.direction === 'asc' ? ' ↑' : ' ↓') : '';

  return <div className={styles.tableContainer}>
    <div className={styles.queueIntro}>
      <div><p className={styles.eyebrow}>Review workspace</p><h1>Signal Queue</h1><p className={styles.queueDescription}>Prioritized candidate signals requiring pharmacovigilance review.</p></div>
      <div className={styles.queueCounts}><div><strong>{signalResponse.total}</strong><span>Total signals</span></div><div><strong>{reviewCount}</strong><span>Requiring review</span></div></div>
    </div>
    <div className={styles.searchHeader}>
      <div className={styles.filterField}><label htmlFor="signal-search">Search signals</label><input id="signal-search" type="search" placeholder="Search by drug or event..." value={searchTerm} onChange={(event) => { setSearchTerm(event.target.value); setPage(1); }} /></div>
      <div className={styles.filterField}><label htmlFor="priority-filter">Priority</label><select id="priority-filter" value={priorityFilter} onChange={(event) => { setPriorityFilter(event.target.value); setPage(1); }}><option value="all">All priorities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>
      <div className={styles.filterField}><label htmlFor="status-filter">Review status</label><select id="status-filter" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}><option value="all">All statuses</option><option value="candidate">Candidate</option><option value="under_review">Under review</option><option value="closed">Closed</option></select></div>
      {(searchTerm || priorityFilter !== 'all' || statusFilter !== 'all') && <button type="button" className={styles.resetButton} onClick={resetFilters}>Reset filters</button>}
    </div>
    <div className={styles.tableWrapper}>
      <table className={styles.signalTable}><thead><tr>
        {([['drug_name', 'Drug / Event'], ['supporting_report_count', 'Reports'], ['prr', 'PRR'], ['ror', 'ROR'], ['priority_level', 'Priority'], ['candidate_status', 'Review status']] as const).map(([key, label]) => <th key={key} onClick={() => requestSort(key)} aria-sort={sortConfig?.key === key ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{label}{sortLabel(key)}</th>)}<th>Open</th>
      </tr></thead><tbody>
        {isLoading ? Array.from({ length: 4 }).map((_, index) => <tr key={`skeleton-${index}`}><td colSpan={7}><div className={styles.skeletonPulse} /></td></tr>) : error ? <tr><td colSpan={7}><div className={styles.errorState} role="alert">{error}<button type="button" onClick={() => window.location.reload()}>Retry</button></div></td></tr> : visibleSignals.length === 0 ? <tr><td colSpan={7}><div className={styles.emptyState}><strong>No signals found</strong><span>Try changing your filters or search criteria.</span>{(searchTerm || priorityFilter !== 'all' || statusFilter !== 'all') && <button type="button" onClick={resetFilters}>Reset filters</button>}</div></td></tr> : visibleSignals.map((signal) => <tr key={signal.signal_id} className={styles.clickableRow} onClick={() => selectSignal(signal)}>
          <td className={styles.identityCell}><strong title={signal.drug_name}>{signal.drug_name}</strong><span title={signal.event_name}>{signal.event_name}</span></td><td className={styles.numericCell}>{signal.supporting_report_count.toLocaleString()}</td><td className={styles.numericCell}>{signal.prr.toFixed(2)}</td><td className={styles.numericCell}>{signal.ror?.toFixed(2) || '--'}</td><td><span className={`${styles.badge} ${styles[priorityClass(signal.priority_level)]}`}>{signal.priority_level || 'Unscored'}</span></td><td><span className={styles.statusBadge}>{signal.candidate_status.replace('_', ' ')}</span></td><td><button type="button" className={styles.openButton} onClick={(event) => { event.stopPropagation(); selectSignal(signal); }}>Open</button></td>
        </tr>)}
      </tbody></table>
      <div className={styles.mobileList}>{!isLoading && !error && visibleSignals.map((signal) => <article className={styles.mobileCard} key={signal.signal_id} onClick={() => selectSignal(signal)}>
        <div className={styles.mobileCardHeader}><div className={styles.identityCell}><strong>{signal.drug_name}</strong><span>{signal.event_name}</span></div><span className={`${styles.badge} ${styles[priorityClass(signal.priority_level)]}`}>{signal.priority_level || 'Unscored'}</span></div>
        <div className={styles.mobileMetrics}><span><small>Reports</small><b>{signal.supporting_report_count.toLocaleString()}</b></span><span><small>PRR</small><b>{signal.prr.toFixed(2)}</b></span><span><small>ROR</small><b>{signal.ror?.toFixed(2) || '--'}</b></span></div>
        <div className={styles.mobileCardFooter}><span>{signal.candidate_status.replace('_', ' ')}</span><button type="button" className={styles.openButton} onClick={(event) => { event.stopPropagation(); selectSignal(signal); }}>Open investigation</button></div>
      </article>)}</div>
    </div>
    <div className={styles.pagination}><span>Showing {visibleSignals.length ? (page - 1) * PAGE_SIZE + 1 : 0}-{Math.min(page * PAGE_SIZE, filteredSignals.length)} of {filteredSignals.length}</span><div><button type="button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button><span>Page {page} of {pageCount}</span><button type="button" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>
  </div>;
}