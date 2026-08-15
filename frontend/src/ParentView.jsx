import { useState, useEffect, useRef } from "react";
import { API } from "./api";
import Message from "./components/Message";

const CHIPS = [
  "Are you open this Friday?",
  "My child has a fever",
  "What's tuition for a 3-year-old?",
  "How do I schedule a tour?",
  "I forgot to pack lunch!",
];

const WELCOME = {
  role: "assistant",
  text: "Hi! I'm the AI front desk assistant for Sunshine Early Learning Center. How can I help you today?",
  response: null,
};

export default function ParentView({ navigate }) {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [policies, setPolicies] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    API.getPolicies().then(setPolicies).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function send(text) {
    if (!text.trim() || loading) return;
    setInput("");
    setLoading(true);

    setMessages(prev => [
      ...prev,
      { role: "parent", text }
    ]);

    setMessages(prev => [
      ...prev,
      { role: "typing" }
    ]);

    try {
      const response = await API.ask(text);

      const unknownCited = response.source_policy_ids?.some(
        id => !policies.find(p => p.id === id)
      );
      if (unknownCited) {
        API.getPolicies().then(setPolicies).catch(() => {});
      }

      setMessages(prev => [
        ...prev.filter(m => m.role !== "typing"),
        {
          role: "assistant",
          text: response.answer,
          response,
        },
      ]);
    } catch {
      setMessages(prev => [
        ...prev.filter(m => m.role !== "typing"),
        {
          role: "assistant",
          text: "I'm having trouble right now — please call us at (206) 555-0123.",
          response: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100dvh",
      maxWidth: "480px",
      margin: "0 auto",
      background: "var(--bw-surface)",
    }}>
      {/* Header */}
      <div style={{
        background: "var(--bw-indigo)",
        padding: "1rem 1.25rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          <span style={{ fontSize: "1.5rem" }}>☀️</span>
          <div>
            <div style={{
              color: "white",
              fontWeight: 700,
              fontSize: "0.95rem",
            }}>
              Sunshine Early Learning Center
            </div>
            <div style={{
              color: "rgba(255,255,255,0.7)",
              fontSize: "0.75rem",
            }}>
              AI Front Desk — staff sees anything I can't answer
            </div>
          </div>
        </div>
        <button
          onClick={() => navigate("/operator")}
          style={{
            background: "rgba(255,255,255,0.15)",
            border: "none",
            borderRadius: "8px",
            color: "white",
            fontSize: "0.75rem",
            padding: "0.35rem 0.65rem",
            fontWeight: 600,
          }}
        >
          Staff
        </button>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "1rem 1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "4px",
      }}>
        {messages.map((msg, i) => (
          <Message key={i} message={msg} policies={policies} />
        ))}

        {/* Suggestion chips */}
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          marginTop: "0.5rem",
        }}>
          {CHIPS.map(chip => (
            <button
              key={chip}
              onClick={() => send(chip)}
              disabled={loading}
              style={{
                background: "white",
                border: "1.5px solid var(--bw-border)",
                borderRadius: "20px",
                padding: "0.5rem 1rem",
                fontSize: "0.85rem",
                color: "var(--bw-indigo)",
                fontWeight: 500,
                opacity: loading ? 0.5 : 1,
              }}
            >
              {chip}
            </button>
          ))}
        </div>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: "0.75rem 1.25rem 1.25rem",
        borderTop: "1px solid var(--bw-border)",
        display: "flex",
        gap: "8px",
        flexShrink: 0,
        background: "var(--bw-surface)",
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send(input)}
          placeholder="Ask a question..."
          disabled={loading}
          style={{
            flex: 1,
            padding: "0.75rem 1rem",
            border: "1.5px solid var(--bw-border)",
            borderRadius: "var(--radius-bubble)",
            fontSize: "0.95rem",
            outline: "none",
            fontFamily: "var(--font)",
          }}
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          style={{
            background: "var(--bw-indigo)",
            border: "none",
            borderRadius: "50%",
            width: "44px",
            height: "44px",
            color: "white",
            fontSize: "1.1rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: loading || !input.trim() ? 0.5 : 1,
            flexShrink: 0,
          }}
        >
          ↑
        </button>
      </div>
    </div>
  );
}