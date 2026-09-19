'use client';

import React, { useEffect, useState } from 'react';
import { ApiClient } from '../lib/api/client';
import { ProcessedReport, SupportingReportList } from '../lib/api/types';
import styles from './EvidenceExplorer.module.css';

interface EvidenceExplorerProps {
  apiClient: ApiClient;
  signalId: string;
  reportCount: number;
}

const PAGE_SIZE = 10;

function displayValue(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? '--' : String(value);
}

export function EvidenceExplorer({ apiClient, signalId, reportCount }: EvidenceExplorerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [reportList, setReportList] = useState<SupportingReportList | null>(null);
  const [selectedReport, setSelectedReport] = useState<ProcessedReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedReport && !detailLoading && !detailError) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedReport(null);
        setDetailError(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [detailError, detailLoading, selectedReport]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    let active = true;
    apiClient.listSupportingReports(signalId, page, PAGE_SIZE)
      .then((response) => {
        if (active) {
          setReportList(response);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : 'Failed to load supporting reports.');
          setReportList(null);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [apiClient, isOpen, page, signalId]);

  const handleSelectReport = async (reportId: string) => {
    setSelectedReport(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      setSelectedReport(await apiClient.getReport(reportId));
    } catch (requestError: unknown) {
      setDetailError(requestError instanceof Error ? requestError.message : 'Failed to load report details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleToggleExplorer = () => {
    if (!isOpen) {
      setLoading(true);
      setError(null);
    }
    setIsOpen((open) => !open);
  };

  const handlePageChange = (nextPage: number) => {
    setLoading(true);
    setPage(nextPage);
  };

  const totalPages = reportList ? Math.max(1, Math.ceil(reportList.total / reportList.page_size)) : 1;

  return (
    <section id="evidence-explorer" className={styles.explorer} aria-label="Evidence Explorer">
      <button
        className={styles.explorerToggle}
        type="button"
        aria-expanded={isOpen}
        onClick={handleToggleExplorer}
      >
        <span>
          <strong>Evidence Explorer</strong>
          <small>Supporting FAERS reports</small>
        </span>
        <span className={styles.toggleMeta}>
          {reportCount.toLocaleString()} reports <span aria-hidden="true">{isOpen ? '▼' : '►'}</span>
        </span>
      </button>

      {isOpen && (
        <div className={styles.explorerContent}>
          <p className={styles.dataNote}>
            Seriousness is derived from official FAERS patient outcome (OUTC) codes. Signal strength and priority are calculated separately.
          </p>
          {loading ? (
            <div className={styles.loadingState}>Loading supporting reports...</div>
          ) : error ? (
            <div className={styles.errorState} role="alert">{error}</div>
          ) : reportList && reportList.reports.length === 0 ? (
            <div className={styles.emptyState}>No supporting reports are available for this signal.</div>
          ) : reportList ? (
            <>
              <div className={styles.listHeader}>
                <span>{reportList.total.toLocaleString()} stored reports</span>
                <span>Page {reportList.page} of {totalPages}</span>
              </div>
              <div className={styles.reportList}>
                {reportList.reports.map((report) => (
                  <button
                    key={report.report_id}
                    type="button"
                    className={styles.reportRow}
                    onClick={() => void handleSelectReport(report.report_id)}
                  >
                    <span className={styles.reportIdentity}>
                      <strong>{report.report_id}</strong>
                      <small>{report.drug_name}</small>
                    </span>
                    <span className={styles.reportReaction}>{report.reactions.length ? report.reactions.join(', ') : '--'}</span>
                      <span className={styles.reportSeriousness}>{report.seriousness}</span>
                    <span className={styles.reportMeta}>{displayValue(report.event_date)} · {displayValue(report.report_quarter)}</span>
                    <span className={styles.openLabel}>View detail →</span>
                  </button>
                ))}
              </div>
              <div className={styles.pagination}>
                <button type="button" disabled={page <= 1 || loading} onClick={() => handlePageChange(page - 1)}>
                  Previous
                </button>
                <span>{page} / {totalPages}</span>
                <button type="button" disabled={page >= totalPages || loading} onClick={() => handlePageChange(page + 1)}>
                  Next
                </button>
              </div>
            </>
          ) : null}

          {(detailLoading || detailError || selectedReport) && (
            <>
              <button type="button" className={styles.drawerBackdrop} aria-label="Close report detail" onClick={() => { setSelectedReport(null); setDetailError(null); }} />
            <aside className={styles.detailPanel} role="dialog" aria-modal="true" aria-labelledby="report-detail-title">
              <div className={styles.detailHeader}>
                <h3 id="report-detail-title">Report Detail</h3>
                {selectedReport && <span>{selectedReport.report_id}</span>}
                <button type="button" className={styles.closeButton} aria-label="Close report detail" onClick={() => { setSelectedReport(null); setDetailError(null); }}>Close</button>
              </div>
              {detailLoading ? (
                <div className={styles.loadingState}>Loading report detail...</div>
              ) : detailError ? (
                <div className={styles.errorState} role="alert">{detailError}</div>
              ) : selectedReport ? (
                <dl className={styles.detailGrid}>
                  <div><dt>Report ID</dt><dd>{selectedReport.report_id}</dd></div>
                  <div><dt>Drug</dt><dd>{displayValue(selectedReport.drug_name)}</dd></div>
                  <div><dt>Reactions</dt><dd>{selectedReport.reactions.length ? selectedReport.reactions.join(', ') : '--'}</dd></div>
                  <div><dt>Patient age</dt><dd>{displayValue(selectedReport.patient_age)}</dd></div>
                  <div><dt>Patient sex</dt><dd>{displayValue(selectedReport.patient_sex)}</dd></div>
                  <div><dt>Event date</dt><dd>{displayValue(selectedReport.event_date)}</dd></div>
                  <div><dt>Seriousness</dt><dd>{selectedReport.seriousness}</dd></div>
                  <div><dt>FAERS outcome code(s)</dt><dd>{selectedReport.seriousness_codes.length ? selectedReport.seriousness_codes.join(', ') : '--'}</dd></div>
                  <div><dt>Report quarter</dt><dd>{displayValue(selectedReport.report_quarter)}</dd></div>
                  <div><dt>Source</dt><dd>{displayValue(selectedReport.source)}</dd></div>
                </dl>
              ) : null}
            </aside>
            </>
          )}
        </div>
      )}
    </section>
  );
}