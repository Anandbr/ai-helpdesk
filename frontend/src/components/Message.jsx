import { useState } from "react";

export default function Message({ message, policies = [] }) {
  const [expandedPolicy, setExpandedPolicy] = useState(null);
  const isParent = message.role === "parent";
  const isEmergency =
    message.response?.action_taken === "emergency";
  const isEscalation =
    message.response?.action_taken === "escalate";

  const policyMap = Object.fromEntries(
    policies.map(p => [p.id, p])
  );

  if (message.role === "typing") {
    return (
      <div style={{
        display: "flex",
        padding: "4px 0"
      }}>
        <TypingDots />
      </div>
    );
  }

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: isParent ? "flex-end" : "flex-start",
      gap: "4px",
      padding: "4px 0",
    }}>

      {/* Emergency banner */}
      {isEmergency && (
        <div style={{
          background: "var(--bw-coral)",
          color: "white",
          borderRadius: "10px",
          padding: "0.5rem 0.75rem",
          fontSize: "0.85rem",
          fontWeight: 700,
          maxWidth: "80%",
        }}>
          🚨 Emergency — Call 911
        </div>
      )}

      {/* Message bubble */}
      <div style={{
        maxWidth: "80%",
        padding: "0.75rem 1rem",
        borderRadius: isParent
          ? "18px 18px 4px 18px"
          : "18px 18px 18px 4px",
        background: isParent
          ? "var(--bw-bubble-gray)"
          : isEmergency
            ? "#FEE2E2"
            : "var(--bw-teal)",
        color: isParent
          ? "var(--bw-text)"
          : isEmergency
            ? "var(--bw-coral)"
            : "white",
        fontSize: "0.95rem",
        lineHeight: 1.5,
        whiteSpace: "pre-wrap",
      }}>
        {message.text}
      </div>

      {/* Escalation banner */}
      {isEscalation && message.response?.escalation_contact && (
        <div style={{
          background: "rgba(91, 95, 221, 0.12)",
          color: "var(--bw-indigo)",
          borderRadius: "10px",
          padding: "0.4rem 0.75rem",
          fontSize: "0.8rem",
          maxWidth: "80%",
        }}>
          👤 Passed to: {message.response.escalation_contact}
        </div>
      )}

      {/* Citation chips */}
      {!isParent &&
        message.response?.source_policy_ids?.length > 0 && (
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "6px",
          maxWidth: "80%",
        }}>
          {message.response.source_policy_ids.map(id => {
            const policy = policyMap[id];
            if (!policy) return null;
            const isExpanded = expandedPolicy === id;
            return (
              <div key={id}>
                <button
                  onClick={() => setExpandedPolicy(
                    isExpanded ? null : id
                  )}
                  style={{
                    background: "white",
                    border: "1.5px solid var(--bw-border)",
                    borderRadius: "20px",
                    padding: "0.25rem 0.75rem",
                    fontSize: "0.75rem",
                    color: "var(--bw-text-soft)",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  📋 {policy.title}
                  <span style={{ fontSize: "0.6rem" }}>
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </button>
                {isExpanded && (
                  <div style={{
                    background: "white",
                    border: "1.5px solid var(--bw-border)",
                    borderRadius: "10px",
                    padding: "0.75rem",
                    fontSize: "0.8rem",
                    color: "var(--bw-text)",
                    lineHeight: 1.5,
                    marginTop: "4px",
                    maxWidth: "280px",
                  }}>
                    {policy.content}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TypingDots() {
  return (
    <div style={{
      background: "var(--bw-teal)",
      borderRadius: "18px 18px 18px 4px",
      padding: "0.75rem 1rem",
      display: "flex",
      gap: "4px",
      alignItems: "center",
    }}>
      {[0, 1, 2].map(i => (
        <div
          key={i}
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: "white",
            opacity: 0.8,
            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}