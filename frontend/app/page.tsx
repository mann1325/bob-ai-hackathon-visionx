'use client';

import React, { useState, useEffect } from 'react';
import { Dashboard } from '../components/Dashboard';
import { SignalDetail } from '../components/SignalDetail';
import { Signal } from '../lib/api/types';
import styles from './page.module.css';

export default function Home() {
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  
  // Splash Screen State
  const [showSplash, setShowSplash] = useState(true);
  const [fadeSplash, setFadeSplash] = useState(false);

  useEffect(() => {
    // Hold splash for 3.5 seconds, then fade out
    const fadeTimer = setTimeout(() => {
      setFadeSplash(true);
    }, 3500);

    // Completely unmount after fade transition (0.8s)
    const unmountTimer = setTimeout(() => {
      setShowSplash(false);
    }, 4300);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(unmountTimer);
    };
  }, []);

  return (
    <>
      {showSplash && (
        <div className={`${styles.splashContainer} ${fadeSplash ? styles.splashFadeOut : ''}`}>
          <div className={styles.splashLogoContainer}>
            <div className={styles.content}>
              <div className={styles.pill}>
                <div className={styles.medicine}>
                  <i /><i /><i /><i /><i /><i /><i /><i /><i /><i />
                  <i /><i /><i /><i /><i /><i /><i /><i /><i /><i />
                </div>
                <div className={styles.side}></div>
                <div className={styles.side}></div>
              </div>
            </div>
            <div className={styles.splashBrand}>
              SignalTrace
            </div>
          </div>
        </div>
      )}

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
