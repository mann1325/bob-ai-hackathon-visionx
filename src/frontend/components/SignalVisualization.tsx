'use client';

import React, { useState } from 'react';
import styles from './SignalVisualization.module.css';

interface IllustrativeSignalPoint {
  drug: string;
  event: string;
  reports: number;
  prr: number;
  ror: number;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
}

interface IllustrativeReportingPoint {
  period: string;
  count: number;
}

// Demo data only — replace with real SignalTrace data later.
const ILLUSTRATIVE_SIGNAL_GRAPH_DATA: IllustrativeSignalPoint[] = [
  { drug: 'AMOXICILLIN', event: 'RASH', reports: 184, prr: 1.4, ror: 1.6, priority: 'Low' },
  { drug: 'SERTRALINE', event: 'NAUSEA', reports: 326, prr: 2.1, ror: 2.4, priority: 'Medium' },
  { drug: 'METFORMIN', event: 'FATIGUE', reports: 492, prr: 3.4, ror: 3.8, priority: 'Medium' },
  { drug: 'LISINOPRIL', event: 'COUGH', reports: 715, prr: 4.9, ror: 5.5, priority: 'High' },
  { drug: 'IBUPROFEN', event: 'DIZZINESS', reports: 938, prr: 6.8, ror: 7.4, priority: 'High' },
  { drug: 'ADAPALENE', event: 'DRUG INEFFECTIVE', reports: 1694, prr: 8.6, ror: 33.39, priority: 'Critical' },
  { drug: 'WARFARIN', event: 'HAEMORRHAGE', reports: 1186, prr: 10.4, ror: 12.1, priority: 'Critical' },
  { drug: 'OMEPRAZOLE', event: 'HEADACHE', reports: 604, prr: 12.2, ror: 13.6, priority: 'High' },
  { drug: 'ATORVASTATIN', event: 'MYALGIA', reports: 856, prr: 5.7, ror: 6.3, priority: 'High' },
];

const ILLUSTRATIVE_REPORTING_ACTIVITY_DATA: IllustrativeReportingPoint[] = [
  { period: '2025 Q1', count: 412 },
  { period: '2025 Q2', count: 568 },
  { period: '2025 Q3', count: 721 },
  { period: '2025 Q4', count: 904 },
  { period: '2026 Q1', count: 1128 },
  { period: '2026 Q2', count: 1346 },
];

const CHART_WIDTH = 760;
const CHART_HEIGHT = 390;
const PADDING = { top: 34, right: 34, bottom: 62, left: 72 };
const PRR_THRESHOLD = 2;
const MAX_PRR = 14;
const MAX_REPORTS = 1800;

function pointCoordinates(point: IllustrativeSignalPoint) {
  const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  return {
    x: PADDING.left + (point.prr / MAX_PRR) * plotWidth,
    y: PADDING.top + plotHeight - (point.reports / MAX_REPORTS) * plotHeight,
  };
}

function reportingCoordinates(point: IllustrativeReportingPoint, index: number) {
  const chartWidth = 760 - 72 - 34;
  const chartHeight = 320 - 34 - 52;
  const maxCount = 1500;
  return {
    x: 72 + (index / (ILLUSTRATIVE_REPORTING_ACTIVITY_DATA.length - 1)) * chartWidth,
    y: 34 + chartHeight - (point.count / maxCount) * chartHeight,
  };
}

function formatNumber(value: number, digits = 2): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function SignalVisualization() {
  const [selectedPoint, setSelectedPoint] = useState<IllustrativeSignalPoint | null>(null);
  const [selectedReportingPoint, setSelectedReportingPoint] = useState<IllustrativeReportingPoint | null>(null);
  const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const thresholdX = PADDING.left + (PRR_THRESHOLD / MAX_PRR) * plotWidth;
  const tooltipPoint = selectedPoint ? pointCoordinates(selectedPoint) : null;
  const reportingTooltipPoint = selectedReportingPoint
    ? reportingCoordinates(selectedReportingPoint, ILLUSTRATIVE_REPORTING_ACTIVITY_DATA.indexOf(selectedReportingPoint))
    : null;
  const reportingLinePoints = ILLUSTRATIVE_REPORTING_ACTIVITY_DATA
    .map((point, index) => {
      const coordinates = reportingCoordinates(point, index);
      return `${coordinates.x},${coordinates.y}`;
    })
    .join(' ');

  return (
    <section className={styles.panel} aria-labelledby="signal-visualization-heading">
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Investigation Visualization</p>
          <h2 id="signal-visualization-heading">Signal Visualization</h2>
          <p className={styles.description}>A comparative landscape of illustrative drug-event signals by statistical strength and evidence volume.</p>
        </div>
      </header>

      <div className={styles.graphCard}>
        <div className={styles.graphHeader}>
          <div>
            <h3>Signal Landscape</h3>
            <p>PRR is plotted against supporting reports; points are not a time series.</p>
          </div>
          <span className={styles.thresholdKey}><i /> PRR = 2 reference</span>
        </div>

        <div className={styles.chartFrame}>
          <svg className={styles.chart} viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label="Illustrative signal landscape scatter plot">
            <line className={styles.axis} x1={PADDING.left} y1={PADDING.top + plotHeight} x2={CHART_WIDTH - PADDING.right} y2={PADDING.top + plotHeight} />
            <line className={styles.axis} x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={PADDING.top + plotHeight} />
            <line className={styles.thresholdLine} x1={thresholdX} y1={PADDING.top} x2={thresholdX} y2={PADDING.top + plotHeight} />
            <text className={styles.thresholdLabel} x={thresholdX + 6} y={PADDING.top - 10}>PRR = 2</text>

            {[0, 4, 8, 12, 14].map((value) => {
              const x = PADDING.left + (value / MAX_PRR) * plotWidth;
              return <text className={styles.tick} key={`x-${value}`} x={x} y={CHART_HEIGHT - 34} textAnchor="middle">{value}</text>;
            })}
            {[0, 600, 1200, 1800].map((value) => {
              const y = PADDING.top + plotHeight - (value / MAX_REPORTS) * plotHeight;
              return <text className={styles.tick} key={`y-${value}`} x={PADDING.left - 12} y={y + 4} textAnchor="end">{value.toLocaleString()}</text>;
            })}

            {ILLUSTRATIVE_SIGNAL_GRAPH_DATA.map((point) => {
              const coordinates = pointCoordinates(point);
              const isSelected = selectedPoint === point;
              return (
                <g
                  key={`${point.drug}-${point.event}`}
                  className={styles.pointGroup}
                  tabIndex={0}
                  role="img"
                  aria-label={`${point.drug}, ${point.event}, ${point.reports} reports, PRR ${point.prr}`}
                  onMouseEnter={() => setSelectedPoint(point)}
                  onMouseLeave={() => setSelectedPoint(null)}
                  onFocus={() => setSelectedPoint(point)}
                  onBlur={() => setSelectedPoint(null)}
                >
                  <circle className={styles.pointHalo} cx={coordinates.x} cy={coordinates.y} r={isSelected ? 14 : 10} />
                  <circle className={`${styles.point} ${isSelected ? styles.pointSelected : ''}`} cx={coordinates.x} cy={coordinates.y} r="6" />
                </g>
              );
            })}
          </svg>
          <span className={styles.xAxisLabel}>PRR</span>
          <span className={styles.yAxisLabel}>Supporting Reports</span>

          {selectedPoint && tooltipPoint && (
            <div className={styles.tooltip} style={{ left: `${(tooltipPoint.x / CHART_WIDTH) * 100}%`, top: `${(tooltipPoint.y / CHART_HEIGHT) * 100}%` }} role="tooltip">
              <strong>{selectedPoint.drug} → {selectedPoint.event}</strong>
              <span>Reports: {selectedPoint.reports.toLocaleString()}</span>
              <span>PRR: {formatNumber(selectedPoint.prr)}</span>
              <span>ROR: {formatNumber(selectedPoint.ror)}</span>
              <span>Priority: {selectedPoint.priority}</span>
            </div>
          )}
        </div>
      </div>

      <div className={styles.graphCard}>
        <div className={styles.graphHeader}>
          <div>
            <h3>Reporting Activity</h3>
            <p>Illustrative quarterly report counts for interface demonstration only.</p>
          </div>
        </div>

        <div className={styles.chartFrame}>
          <svg className={styles.chart} viewBox="0 0 760 320" role="img" aria-label="Illustrative reporting activity line chart">
            <line className={styles.axis} x1="72" y1="34" x2="72" y2="268" />
            <line className={styles.axis} x1="72" y1="268" x2="726" y2="268" />
            {[0, 500, 1000, 1500].map((value) => {
              const y = 268 - (value / 1500) * 234;
              return <text className={styles.tick} key={`report-y-${value}`} x="60" y={y + 4} textAnchor="end">{value.toLocaleString()}</text>;
            })}
            <polyline className={styles.activityLine} points={reportingLinePoints} fill="none" />
            {ILLUSTRATIVE_REPORTING_ACTIVITY_DATA.map((point, index) => {
              const coordinates = reportingCoordinates(point, index);
              const isSelected = selectedReportingPoint === point;
              return (
                <g
                  key={point.period}
                  className={styles.pointGroup}
                  tabIndex={0}
                  role="img"
                  aria-label={`${point.period}: ${point.count} illustrative reports`}
                  onMouseEnter={() => setSelectedReportingPoint(point)}
                  onMouseLeave={() => setSelectedReportingPoint(null)}
                  onFocus={() => setSelectedReportingPoint(point)}
                  onBlur={() => setSelectedReportingPoint(null)}
                >
                  <circle className={styles.pointHalo} cx={coordinates.x} cy={coordinates.y} r={isSelected ? 13 : 9} />
                  <circle className={`${styles.point} ${isSelected ? styles.pointSelected : ''}`} cx={coordinates.x} cy={coordinates.y} r="5" />
                  <text className={styles.periodLabel} x={coordinates.x} y="292" textAnchor="middle">{point.period}</text>
                </g>
              );
            })}
          </svg>
          <span className={styles.xAxisLabel}>Reporting Period</span>
          <span className={styles.yAxisLabel}>Report Count</span>

          {selectedReportingPoint && reportingTooltipPoint && (
            <div className={styles.tooltip} style={{ left: `${(reportingTooltipPoint.x / 760) * 100}%`, top: `${(reportingTooltipPoint.y / 320) * 100}%` }} role="tooltip">
              <strong>{selectedReportingPoint.period}</strong>
              <span>Report Count: {selectedReportingPoint.count.toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
