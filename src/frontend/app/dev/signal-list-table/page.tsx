'use client';

import React from 'react';
import { SignalListTable } from '../../../components/SignalListTable';
import { MockAdapter } from '../../../lib/api/mock-adapter';

const devApiClient = new MockAdapter();

export default function SignalListTableDevPage() {
  return (
    <div style={{ backgroundColor: '#0B0C10', minHeight: '100vh', padding: '3rem' }}>
      <h1 style={{ color: '#FAFAFA', fontFamily: 'Inter, sans-serif', fontSize: '1.25rem', marginBottom: '2rem' }}>
        DEV ISOLATION ZONE: Signal List Table
      </h1>
      
      <div style={{ maxWidth: '1200px' }}>
        <SignalListTable apiClient={devApiClient} />
      </div>
    </div>
  );
}
