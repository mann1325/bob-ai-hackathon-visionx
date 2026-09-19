'use client';

import React, { useEffect, useState } from 'react';
import { Dashboard } from '../components/Dashboard';
import { SignalDetail } from '../components/SignalDetail';
import { Signal } from '../lib/api/types';

export default function Home() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [showSplash, setShowSplash] = useState(true);
  const [fadeSplash, setFadeSplash] = useState(false);

  useEffect(() => {
    const fadeTimer = window.setTimeout(() => setFadeSplash(true), 700);
    const unmountTimer = window.setTimeout(() => setShowSplash(false), 1500);
    return () => { window.clearTimeout(fadeTimer); window.clearTimeout(unmountTimer); };
  }, []);

  return (
    <>
      {showSplash && <div className={`splashContainer ${fadeSplash ? 'splashFadeOut' : ''}`} aria-hidden="true"><div className="splashLogoContainer"><div className="content"><div className="pill"><div className="medicine">{Array.from({ length: 20 }, (_, index) => <i key={index} />)}</div><div className="side" /><div className="side" /></div></div><div className="splashBrand">SignalTrace</div></div></div>}
      {selectedSignal ? (
        <SignalDetail 
          signal={selectedSignal} 
          onBack={() => setSelectedSignal(null)} 
        />
      ) : (
        <Dashboard 
          onSelectSignal={(signal) => setSelectedSignal(signal)} 
        />
      )}
    </>
  );
}
