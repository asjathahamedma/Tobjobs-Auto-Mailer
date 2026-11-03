"use client";

import { useEffect, useRef } from "react";
import { Check, X } from "lucide-react";

type ToastProps = {
  message: string;
  onDismiss: () => void;
};

export function Toast({ message, onDismiss }: ToastProps) {
  const dismiss = useRef(onDismiss);
  dismiss.current = onDismiss;

  useEffect(() => {
    const timer = window.setTimeout(() => dismiss.current(), 4000);
    return () => window.clearTimeout(timer);
  }, [message]);

  if (!message) return null;

  return (
    <div className="toast" role="status" aria-live="polite">
      <Check size={18} />
      <span>{message}</span>
      <button type="button" aria-label="Dismiss notification" onClick={onDismiss}><X size={16} /></button>
    </div>
  );
}
