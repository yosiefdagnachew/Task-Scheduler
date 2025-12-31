import React from 'react';

export default function ConfirmDialog({
  open,
  title,
  message,
  onCancel,
  onConfirm,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmDisabled = false,
}) {
  if (!open) return null;

  const overlayStyle = {
    position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'rgba(0,0,0,0.4)', zIndex: 1000,
  };
  const cardStyle = {
    width: 'min(92vw, 520px)', background: '#fff', borderRadius: 10,
    boxShadow: '0 10px 30px rgba(0,0,0,.2)', overflow: 'hidden',
    animation: 'fdialog-pop .12s ease-out',
  };
  const headerStyle = { padding: '14px 18px', fontSize: 18, fontWeight: 600, borderBottom: '1px solid #e5e7eb' };
  const bodyStyle = { padding: '16px 18px', color: '#374151', whiteSpace: 'pre-wrap' };
  const actionsStyle = { padding: '12px 18px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: 10, justifyContent: 'flex-end' };
  const btnBase = { padding: '8px 14px', borderRadius: 8, fontWeight: 600, cursor: 'pointer' };
  const btnGhost = { ...btnBase, border: '1px solid #e5e7eb', background: '#fff', color: '#374151' };
  const btnPrimary = { ...btnBase, background: '#2563eb', color: '#fff', border: 'none', opacity: confirmDisabled ? .6 : 1 };

  return (
    <div style={overlayStyle}>
      <div style={cardStyle}>
        <div style={headerStyle}>{title}</div>
        <div style={bodyStyle}>{message}</div>
        <div style={actionsStyle}>
          <button style={btnGhost} onClick={onCancel}>
            {cancelText}
          </button>
          <button style={btnPrimary} onClick={onConfirm} disabled={confirmDisabled}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
