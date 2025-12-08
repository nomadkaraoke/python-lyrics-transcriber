import React from "react";

type Props = {
  models: { id: string; name: string; available: boolean }[];
  value?: string;
  onChange: (modelId: string) => void;
};

export const ModelSelector: React.FC<Props> = ({ models, value, onChange }) => {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {models.map((m) => (
        <option key={m.id} value={m.id} disabled={!m.available}>
          {m.name} {m.available ? "" : "(unavailable)"}
        </option>
      ))}
    </select>
  );
};

export default ModelSelector;


