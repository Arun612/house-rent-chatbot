import React, { useState, useEffect } from 'react';

export default function ToastContainer({ toasts }) {
  return (
    <div id="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast--${t.type}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}
