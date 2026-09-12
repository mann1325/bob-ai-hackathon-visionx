'use client';

import React from 'react';
import { AiExplanationPanel } from '../../../components/AiExplanationPanel';
import { MockAdapter } from '../../../lib/api/mock-adapter';

const devApiClient = new MockAdapter();

export default function AiExplanationDevPage() {
  return (
    <div style={{ backgroundColor: '#0B0C10', minHeight: '100vh', padding: '3rem' }}>
      <h1 style={{ color: '#FAFAFA', fontFamily: 'Inter, sans-serif', fontSize: '1.25rem', marginBottom: '2rem' }}>
        DEV ISOLATION ZONE: AI Explanation Panel
      </h1>
      
      <div style={{ maxWidth: '600px' }}>
        <AiExplanationPanel apiClient={devApiClient} signalId="SIG-1001" />
      </div>
    </div>
  );
}
