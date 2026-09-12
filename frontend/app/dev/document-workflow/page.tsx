'use client';

import React from 'react';
import { DocumentWorkflow } from '../../../components/DocumentWorkflow';
import { MockAdapter } from '../../../lib/api/mock-adapter';

// Explicitly instantiate MockAdapter to guarantee no real backend requests in dev route
const devApiClient = new MockAdapter();

export default function DocumentWorkflowDevPage() {
  return (
    <div style={{ backgroundColor: '#0B0C10', minHeight: '100vh', padding: '3rem' }}>
      <h1 style={{ color: '#FAFAFA', fontFamily: 'Inter, sans-serif', fontSize: '1.25rem', marginBottom: '2rem' }}>
        DEV ISOLATION ZONE: Document Workflow
      </h1>
      
      <div style={{ maxWidth: '800px' }}>
        <DocumentWorkflow 
          apiClient={devApiClient} 
          signalId="SIG-1001-DEV-ISOLATION" 
        />
      </div>
    </div>
  );
}
