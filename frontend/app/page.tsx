'use client';

import React, { useState } from 'react';
import { Dashboard } from '../components/Dashboard';
import { SignalDetail } from '../components/SignalDetail';
import { Signal } from '../shared-schemas/types';

export default function Home() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);

  if (selectedSignal) {
    return (
      <SignalDetail 
        signal={selectedSignal} 
        onBack={() => setSelectedSignal(null)} 
      />
    );
  }

  return (
    <Dashboard 
      onSelectSignal={(signal) => setSelectedSignal(signal)} 
    />
  );
}
