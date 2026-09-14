'use client';

import React from 'react';
import { LiveSearchWidget } from '../../../components/LiveSearchWidget';
import { MockAdapter } from '../../../lib/api/mock-adapter';

// Explicitly instantiate MockAdapter to guarantee no real backend requests in dev route
const devApiClient = new MockAdapter();

export default function LiveSearchDevPage() {
  return (
    <div style={{ backgroundColor: '#0B0C10', minHeight: '100vh', padding: '3rem' }}>
      <h1 style={{ color: '#FAFAFA', fontFamily: 'Inter, sans-serif', fontSize: '1.25rem', marginBottom: '2rem' }}>
        DEV ISOLATION ZONE: openFDA Live Search Widget
      </h1>
      
      {/* Container simulating a corner-pinned widget in a complex UI */}
      <div style={{ position: 'relative', height: '400px', border: '1px dashed #27272A', padding: '1rem' }}>
        <p style={{ color: '#71717A', fontFamily: 'JetBrains Mono', fontSize: '0.75rem' }}>
          Background UI Placeholder (Dashboard Core, etc.)
        </p>

        <div style={{ position: 'absolute', bottom: '1rem', right: '1rem' }}>
           <LiveSearchWidget apiClient={devApiClient} />
        </div>
      </div>
    </div>
  );
}
