interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (next: string) => void;
  problem?: string;
  placeholder?: string;
}

export function TextField({ id, label, value, onChange, problem, placeholder }: TextFieldProps) {
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
        aria-describedby={problem ? problemId : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {problem && (
        <p id={problemId} className="settings-error-text" role="alert">
          {problem}
        </p>
      )}
    </div>
  );
}
