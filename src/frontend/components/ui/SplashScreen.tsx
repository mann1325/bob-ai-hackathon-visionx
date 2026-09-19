'use client';

import React, { useEffect, useState } from 'react';
import styles from './SplashScreen.module.css';

interface SplashScreenProps {
  onComplete: () => void;
}

export function SplashScreen({ onComplete }: SplashScreenProps) {
  const [hidden, setHidden] = useState(false);
  
  const brandName = "SignalTrace";

  useEffect(() => {
    // Keep the splash screen visible for 3.5 seconds before hiding
    const timer = setTimeout(() => {
      setHidden(true);
      // Wait for the CSS fade-out transition (0.5s) before completely unmounting / signaling complete
      setTimeout(() => {
        onComplete();
      }, 500);
    }, 3500);

    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className={`${styles.splashContainer} ${hidden ? styles.hidden : ''}`}>
      {/* Animated Brand Name */}
      <div className={styles.brandContainer}>
        <div className={styles.brandText}>
          {brandName.split('').map((char, index) => (
            <span 
              key={index} 
              className={styles.brandChar}
              style={{ animationDelay: `${0.2 + (index * 0.08)}s` }}
            >
              {char}
            </span>
          ))}
        </div>
        <div className={styles.tagline}>
          Pharmacovigilance Intelligence
        </div>
      </div>

      {/* 3D Printing Press CSS Animation */}
      <div className={styles.pressWrapper}>
        <div className={styles.press}>
          <div className={styles.sheet}></div>
          <div className={styles.roll}></div>
          <div className={styles.sheet}></div>
          <div className={styles.roll}></div>
          <div className={styles.sheet}></div>
          <div className={styles.roll}></div>
          <div className={styles.sheet}></div>
          <div className={styles.sheet}></div>
          <div className={styles.sheet}></div>
          <div className={styles.sheet}></div>
          <div className={styles.sheet}></div>
          <div className={styles.roll}></div>
        </div>
      </div>
    </div>
  );
}
