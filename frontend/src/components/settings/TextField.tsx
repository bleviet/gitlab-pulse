interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (next: string) => void;
  problem?: string;
  placeholder?: string;
  hint?: string;
}

export function TextField({ id, label, value, onChange, problem, placeholder, hint }: TextFieldProps) {
  const problemId = `${id}-problem`;
  return (
    <div className="settings-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        className={`settings-input${problem ? " error" : ""}`}
        value={value}
        placeholder={placeholder}
        aria-invalid={problem ? true : undefined}
        aria-describedby={problem ? problemId : hint ? `${id}-hint` : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint && !problem && (
        <p id={`${id}-hint`} className="settings-hint">
          {hint}
        </p>
      )}
      {problem && (
        <p id={problemId} className="settings-error-text" role="alert">
          {problem}
        </p>
      )}
    </div>
  );
}
