import React, { useEffect, useRef } from 'react';
import styles from './UserProfilePopup.module.css';

interface UserProfilePopupProps {
  onClose: () => void;
}

export function UserProfilePopup({ onClose }: UserProfilePopupProps) {
  const popupRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popupRef.current && !popupRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  return (
    <div className={styles.popupContainer} ref={popupRef}>
      <div className={styles.card}>
        <div className={styles.image}>JS</div>
        <div className={styles.cardInfo}>
          <span>Jiya Sadaria</span>
          <p>Product Admin</p>
        </div>
        <button className={styles.button} onClick={onClose}>Close Profile</button>
      </div>
    </div>
  );
}
