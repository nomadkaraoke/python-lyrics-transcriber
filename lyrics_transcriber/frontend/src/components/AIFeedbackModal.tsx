import React from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: { reviewerAction: string; finalText?: string; reasonCategory: string; reasonDetail?: string }) => void;
  suggestion?: { text: string; reasoning?: string; confidence?: number };
};

export const AIFeedbackModal: React.FC<Props> = ({ isOpen, onClose, onSubmit, suggestion }) => {
  const [reviewerAction, setAction] = React.useState("ACCEPT");
  const [finalText, setFinalText] = React.useState("");
  const [reasonCategory, setReason] = React.useState("AI_CORRECT");
  const [reasonDetail, setDetail] = React.useState("");

  if (!isOpen) return null;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "#fff", padding: 16, width: 480, borderRadius: 8 }}>
        <h3>AI Suggestion</h3>
        <p style={{ marginTop: 8 }}>
          {suggestion?.text ?? "No suggestion"}
          {suggestion?.confidence != null ? ` (confidence ${Math.round((suggestion.confidence || 0) * 100)}%)` : null}
        </p>
        {suggestion?.reasoning ? <small>{suggestion.reasoning}</small> : null}

        <div style={{ marginTop: 12 }}>
          <label>Action</label>
          <select value={reviewerAction} onChange={(e) => setAction(e.target.value)} style={{ marginLeft: 8 }}>
            <option value="ACCEPT">Accept</option>
            <option value="REJECT">Reject</option>
            <option value="MODIFY">Modify</option>
          </select>
        </div>

        {reviewerAction === "MODIFY" ? (
          <div style={{ marginTop: 12 }}>
            <label>Final Text</label>
            <input value={finalText} onChange={(e) => setFinalText(e.target.value)} style={{ marginLeft: 8, width: "100%" }} />
          </div>
        ) : null}

        <div style={{ marginTop: 12 }}>
          <label>Reason</label>
          <select value={reasonCategory} onChange={(e) => setReason(e.target.value)} style={{ marginLeft: 8 }}>
            <option value="AI_CORRECT">AI_CORRECT</option>
            <option value="AI_INCORRECT">AI_INCORRECT</option>
            <option value="AI_SUBOPTIMAL">AI_SUBOPTIMAL</option>
            <option value="CONTEXT_NEEDED">CONTEXT_NEEDED</option>
            <option value="SUBJECTIVE_PREFERENCE">SUBJECTIVE_PREFERENCE</option>
          </select>
        </div>

        <div style={{ marginTop: 12 }}>
          <label>Details</label>
          <textarea value={reasonDetail} onChange={(e) => setDetail(e.target.value)} style={{ marginLeft: 8, width: "100%" }} />
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
          <button onClick={onClose}>Cancel</button>
          <button
            onClick={() =>
              onSubmit({ reviewerAction, finalText: finalText || undefined, reasonCategory, reasonDetail: reasonDetail || undefined })
            }
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIFeedbackModal;


