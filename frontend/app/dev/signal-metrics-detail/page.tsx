'use client';

import React from 'react';
import { SignalMetricsDetail } from '../../../components/SignalMetricsDetail';
import { MockAdapter } from '../../../lib/api/mock-adapter';

const devApiClient = new MockAdapter();

export default function SignalMetricsDetailDevPage() {
  return (
    <div style={{ backgroundColor: '#0B0C10', minHeight: '100vh', padding: '3rem' }}>
      <h1 style={{ color: '#FAFAFA', fontFamily: 'Inter, sans-serif', fontSize: '1.25rem', marginBottom: '2rem' }}>
        DEV ISOLATION ZONE: Signal Metrics Detail
      </h1>
      
      <div style={{ maxWidth: '1000px' }}>
        {/* We use SIG-1002 as the default mock id since it explicitly has null fields in MockAdapter to test fallback handling */}
        <SignalMetricsDetail apiClient={devApiClient} signalId="SIG-1002" />
      </div>
    </div>
  );
}
