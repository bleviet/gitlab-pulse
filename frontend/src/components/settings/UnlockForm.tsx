import { useState, type FormEvent } from "react";

interface UnlockFormProps {
  onLogin: (password: string) => Promise<void>;
  onDone: () => void;
}

export function UnlockForm({ onLogin, onDone }: UnlockFormProps) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setBusy(true);
    setError(null);
    try {
      await onLogin(password);
      setPassword("");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="settings-unlock" onSubmit={(e) => void handleSubmit(e)}>
      <div className="settings-field">
        <label htmlFor="settings-admin-password">Admin Password</label>
        <input
          id="settings-admin-password"
          type="password"
          className="settings-input"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter password"
          aria-describedby={error ? "settings-unlock-error" : undefined}
        />
      </div>
      <button type="submit" className="pulse-btn-primary" disabled={busy || !password}>
        {busy ? "Signing in..." : "Authenticate"}
      </button>
      {error && (
        <span id="settings-unlock-error" className="settings-error-text" role="alert">
          {error}
        </span>
      )}
    </form>
  );
}
