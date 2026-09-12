'use client';

import React from 'react';
import { RegulatoryPanel } from '../../../components/RegulatoryPanel';

export default function RegulatoryPanelDevPage() {
  return (
    <div style={{ backgroundColor: '#0B0C10', minHeight: '100vh', padding: '3rem' }}>
      <h1 style={{ color: '#FAFAFA', fontFamily: 'Inter, sans-serif', fontSize: '1.25rem', marginBottom: '2rem' }}>
        DEV ISOLATION ZONE: Regulatory Mappings Panel
      </h1>
      
      <div style={{ maxWidth: '800px' }}>
        <RegulatoryPanel />
      </div>
    </div>
  );
}
