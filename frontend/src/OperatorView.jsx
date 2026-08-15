import { useState, useEffect } from "react";
import { API } from "./api";

const TABS = [
  { id: "questions", label: "All Questions" },
  { id: "queue", label: "Improvement Queue" },
  { id: "knowledge", label: "Knowledge Base" },
];

const ACTION_COLOR = {
  emergency: "var(--bw-coral)",
  escalate: "var(--bw-indigo)",
  answer_then_flag: "var(--bw-orange)",
  answer: "var(--bw-border)",
  off_topic: "var(--bw-border)",
};

const ACTION_SEVERITY = {
  emergency: 0,
  escalate: 1,
  answer_then_flag: 2,
  answer: 3,
  off_topic: 4,
};

const inputStyle = {
  width: "100%",
  padding: "0.6rem 0.75rem",
  border: "1.5px solid var(--bw-border)",
  borderRadius: "8px",
  fontSize: "0.9rem",
  fontFamily: "var(--font)",
  outline: "none",
  background: "white",
};

function Loading() {
  return (
    <div style={{
      textAlign: "center",
      padding: "2rem",
      color: "var(--bw-text-soft)",
    }}>
      Loading...
    </div>
  );
}

function Empty({ text }) {
  return (
    <div style={{
      textAlign: "center",
      padding: "2rem",
      color: "var(--bw-text-soft)",
      fontSize: "0.9rem",
    }}>
      {text}
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <div>
      <label style={{
        display: "block",
        fontSize: "0.75rem",
        fontWeight: 600,
        color: "var(--bw-text-soft)",
        marginBottom: "4px",
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}>
        {label}
      </label>
      {children}
    </div>
  );
}

function QuestionsTab({ refresh }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("severity");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    setLoading(true);
    API.operator.questions()
      .then(data => {
        setItems(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  const sorted = [...items].sort((a, b) => {
    if (sortBy === "severity") {
      const sa = ACTION_SEVERITY[a.action_taken] ?? 99;
      const sb = ACTION_SEVERITY[b.action_taken] ?? 99;
      if (sa !== sb) return sa - sb;
    }
    return new Date(b.timestamp) - new Date(a.timestamp);
  });

  if (loading) return <Loading />;
  if (!items.length) return (
    <Empty text="No questions yet" />
  );

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: "12px"
    }}>
      {/* Sort control */}
      <div style={{
        display: "flex",
        gap: "8px",
        marginBottom: "4px"
      }}>
        {["severity", "time"].map(s => (
          <button
            key={s}
            onClick={() => setSortBy(s)}
            style={{
              background: sortBy === s
                ? "var(--bw-indigo)"
                : "white",
              color: sortBy === s
                ? "white"
                : "var(--bw-text-soft)",
              border: "1.5px solid var(--bw-border)",
              borderRadius: "20px",
              padding: "0.3rem 0.75rem",
              fontSize: "0.8rem",
              fontWeight: 600,
            }}
          >
            {s === "severity" ? "By Urgency" : "By Time"}
          </button>
        ))}
      </div>

      {sorted.map(item => (
        <div
          key={item.id}
          style={{
            background: "var(--bw-surface)",
            borderRadius: "var(--radius-card)",
            borderLeft: `4px solid ${ACTION_COLOR[item.action_taken] || "var(--bw-border)"}`,
            padding: "1rem",
          }}
        >
          <div style={{
            fontWeight: 700,
            fontSize: "0.95rem",
            marginBottom: "0.5rem",
          }}>
            {item.question}
          </div>

          <div
            onClick={() => setExpanded(
              expanded === item.id ? null : item.id
            )}
            style={{
              fontSize: "0.85rem",
              color: "var(--bw-text-soft)",
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: expanded === item.id
                ? "unset" : 2,
              WebkitBoxOrient: "vertical",
              marginBottom: "0.5rem",
              cursor: "pointer",
            }}
          >
            {item.answer}
          </div>

          <div style={{
            fontSize: "0.75rem",
            color: "var(--bw-text-soft)",
            display: "flex",
            justifyContent: "space-between",
          }}>
            <span>
              {new Date(item.timestamp).toLocaleString()}
            </span>
            <span style={{
              color: ACTION_COLOR[item.action_taken],
              fontWeight: 600,
              textTransform: "uppercase",
              fontSize: "0.7rem",
            }}>
              {item.action_taken.replace(/_/g, " ")}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function QueueTab({ refresh, onPolicyCreated }) {
  const [gaps, setGaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(null);
  const [form, setForm] = useState({});

  useEffect(() => {
    setLoading(true);
    API.operator.gaps()
      .then(setGaps)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  async function dismiss(id) {
    await API.operator.updateGap(id, {
      status: "dismissed"
    });
    setGaps(prev => prev.map(g =>
      g.id === id ? { ...g, status: "dismissed" } : g
    ));
  }

  function startApprove(gap) {
    const titleGuess = gap.question
      .replace(/^(do you|does|can i|is there|what|how)\s+/i, "")
      .replace(/\?$/, "")
      .split(" ")
      .map(w => w[0].toUpperCase() + w.slice(1))
      .join(" ");

    setApproving(gap.id);
    setForm({
      title: titleGuess,
      topic: "general",
      content: "",
      action: "answer",
      escalation_contact: "",
    });
  }

  async function submitApprove(gap) {
    const body = {
      title: form.title,
      topic: form.topic,
      content: form.content,
      action: form.action,
      ...(form.action !== "answer" &&
        form.escalation_contact
        ? { escalation_contact: form.escalation_contact }
        : {}),
    };

    try {
      await API.operator.createPolicy(body);
      await API.operator.updateGap(gap.id, {
        status: "approved"
      });
      setGaps(prev => prev.map(g =>
        g.id === gap.id
          ? { ...g, status: "approved" }
          : g
      ));
      setApproving(null);
      onPolicyCreated();
    } catch (err) {
      alert(`Failed: ${err.message}`);
    }
  }

  if (loading) return <Loading />;
  if (!gaps.length) return (
    <Empty text="No gaps in the queue" />
  );

  const pending = gaps.filter(g => g.status === "pending");
  const resolved = gaps.filter(g => g.status !== "pending");

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: "12px"
    }}>
      {pending.map(gap => (
        <div key={gap.id} style={{
          background: "var(--bw-surface)",
          borderRadius: "var(--radius-card)",
          padding: "1rem",
        }}>
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: "0.75rem",
            gap: "8px",
          }}>
            <div style={{
              fontWeight: 700,
              fontSize: "0.95rem",
              flex: 1,
            }}>
              {gap.question}
            </div>
            <div style={{
              background: gap.count >= 3
                ? "var(--bw-orange)"
                : "var(--bw-bubble-gray)",
              color: gap.count >= 3
                ? "white"
                : "var(--bw-text-soft)",
              borderRadius: "20px",
              padding: "0.2rem 0.6rem",
              fontSize: "0.75rem",
              fontWeight: 700,
              flexShrink: 0,
            }}>
              ×{gap.count} asked
            </div>
          </div>

          {approving === gap.id ? (
            <div style={{
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              background: "var(--bw-bg)",
              borderRadius: "12px",
              padding: "1rem",
            }}>
              <FormField label="Title">
                <input
                  value={form.title}
                  onChange={e => setForm(f => ({
                    ...f, title: e.target.value
                  }))}
                  style={inputStyle}
                />
              </FormField>
              <FormField label="Topic">
                <input
                  value={form.topic}
                  onChange={e => setForm(f => ({
                    ...f, topic: e.target.value
                  }))}
                  placeholder="e.g. health, billing, hours"
                  style={inputStyle}
                />
              </FormField>
              <FormField label="Answer">
                <textarea
                  value={form.content}
                  onChange={e => setForm(f => ({
                    ...f, content: e.target.value
                  }))}
                  placeholder="Write the answer parents should get..."
                  rows={4}
                  style={{
                    ...inputStyle,
                    resize: "vertical"
                  }}
                />
              </FormField>
              <FormField label="Action">
                <select
                  value={form.action}
                  onChange={e => setForm(f => ({
                    ...f, action: e.target.value
                  }))}
                  style={inputStyle}
                >
                  <option value="answer">Answer</option>
                  <option value="answer_then_flag">
                    Answer + flag staff
                  </option>
                  <option value="escalate">
                    Always escalate
                  </option>
                </select>
              </FormField>
              {form.action !== "answer" && (
                <FormField label="Escalation Contact">
                  <input
                    value={form.escalation_contact}
                    onChange={e => setForm(f => ({
                      ...f,
                      escalation_contact: e.target.value
                    }))}
                    placeholder="e.g. Director Maria Torres"
                    style={inputStyle}
                  />
                </FormField>
              )}
              <div style={{
                display: "flex",
                gap: "8px"
              }}>
                <button
                  onClick={() => submitApprove(gap)}
                  disabled={
                    !form.content.trim() ||
                    !form.title.trim()
                  }
                  style={{
                    background: "var(--bw-green)",
                    color: "white",
                    border: "none",
                    borderRadius: "8px",
                    padding: "0.5rem 1rem",
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    opacity:
                      !form.content.trim() ||
                      !form.title.trim() ? 0.5 : 1,
                  }}
                >
                  Add to Knowledge Base
                </button>
                <button
                  onClick={() => setApproving(null)}
                  style={{
                    background: "var(--bw-bubble-gray)",
                    color: "var(--bw-text-soft)",
                    border: "none",
                    borderRadius: "8px",
                    padding: "0.5rem 1rem",
                    fontSize: "0.85rem",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => startApprove(gap)}
                style={{
                  background: "var(--bw-indigo)",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  padding: "0.4rem 0.9rem",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                }}
              >
                Approve
              </button>
              <button
                onClick={() => dismiss(gap.id)}
                style={{
                  background: "var(--bw-bubble-gray)",
                  color: "var(--bw-text-soft)",
                  border: "none",
                  borderRadius: "8px",
                  padding: "0.4rem 0.9rem",
                  fontSize: "0.85rem",
                }}
              >
                Dismiss
              </button>
            </div>
          )}
        </div>
      ))}

      {resolved.length > 0 && (
        <>
          <div style={{
            fontSize: "0.8rem",
            color: "var(--bw-text-soft)",
            fontWeight: 600,
            marginTop: "0.5rem",
          }}>
            RESOLVED
          </div>
          {resolved.map(gap => (
            <div key={gap.id} style={{
              background: "var(--bw-surface)",
              borderRadius: "var(--radius-card)",
              padding: "1rem",
              opacity: 0.5,
            }}>
              <div style={{ fontSize: "0.9rem" }}>
                {gap.question}
              </div>
              <div style={{
                fontSize: "0.75rem",
                color: gap.status === "approved"
                  ? "var(--bw-green)"
                  : "var(--bw-text-soft)",
                marginTop: "0.25rem",
                fontWeight: 600,
              }}>
                {gap.status.toUpperCase()}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function KnowledgeTab({ refresh }) {
  const [policies, setPolicies] = useState([]);
  const [stale, setStale] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    setLoading(true);
    Promise.all([
      API.operator.policies(),
      API.operator.stale(),
    ]).then(([p, s]) => {
      setPolicies(p);
      setStale(s.map(x => x.id));
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  const grouped = policies.reduce((acc, p) => {
    const t = p.topic || "general";
    if (!acc[t]) acc[t] = [];
    acc[t].push(p);
    return acc;
  }, {});

  async function saveEdit(policy) {
    const changes = {};
    if (editForm.title !== policy.title)
      changes.title = editForm.title;
    if (editForm.content !== policy.content)
      changes.content = editForm.content;
    if (editForm.action !== policy.action)
      changes.action = editForm.action;

    if (!Object.keys(changes).length) {
      setEditing(null);
      return;
    }

    try {
      const updated = await API.operator.updatePolicy(
        policy.id, changes
      );
      setPolicies(prev => prev.map(p =>
        p.id === policy.id ? updated : p
      ));
      setEditing(null);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    }
  }

  if (loading) return <Loading />;

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: "24px"
    }}>
      {Object.entries(grouped).sort().map(([topic, items]) => (
        <div key={topic}>
          <div style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            color: "var(--bw-text-soft)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: "8px",
          }}>
            {topic}
          </div>
          <div style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}>
            {items.map(policy => {
              const isStale = stale.includes(policy.id);
              const isSensitive =
                policy.sensitivity === "sensitive";
              const isEditing = editing === policy.id;

              return (
                <div key={policy.id} style={{
                  background: "var(--bw-surface)",
                  borderRadius: "var(--radius-card)",
                  padding: "1rem",
                  border: isStale
                    ? "1.5px solid var(--bw-orange)"
                    : "1.5px solid var(--bw-border)",
                }}>
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "0.5rem",
                    gap: "8px",
                  }}>
                    <div style={{
                      fontWeight: 700,
                      fontSize: "0.95rem",
                    }}>
                      {policy.title}
                      {isSensitive && (
                        <span style={{ marginLeft: "6px" }}>
                          🔒
                        </span>
                      )}
                    </div>
                    <div style={{
                      display: "flex",
                      gap: "6px",
                      flexShrink: 0
                    }}>
                      {isStale && (
                        <span style={{
                          background: "var(--bw-orange)",
                          color: "white",
                          borderRadius: "20px",
                          padding: "0.15rem 0.5rem",
                          fontSize: "0.7rem",
                          fontWeight: 700,
                        }}>
                          ⚠ Expires {policy.expires}
                        </span>
                      )}
                    </div>
                  </div>

                  {isEditing ? (
                    <div style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}>
                      <FormField label="Title">
                        <input
                          value={editForm.title}
                          onChange={e => setEditForm(f => ({
                            ...f, title: e.target.value
                          }))}
                          style={inputStyle}
                        />
                      </FormField>
                      <FormField label="Content">
                        <textarea
                          value={editForm.content}
                          onChange={e => setEditForm(f => ({
                            ...f, content: e.target.value
                          }))}
                          rows={4}
                          style={{
                            ...inputStyle,
                            resize: "vertical"
                          }}
                        />
                      </FormField>
                      <div style={{
                        display: "flex",
                        gap: "8px"
                      }}>
                        <button
                          onClick={() => saveEdit(policy)}
                          style={{
                            background: "var(--bw-indigo)",
                            color: "white",
                            border: "none",
                            borderRadius: "8px",
                            padding: "0.4rem 0.9rem",
                            fontSize: "0.85rem",
                            fontWeight: 600,
                          }}
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditing(null)}
                          style={{
                            background: "var(--bw-bubble-gray)",
                            color: "var(--bw-text-soft)",
                            border: "none",
                            borderRadius: "8px",
                            padding: "0.4rem 0.9rem",
                            fontSize: "0.85rem",
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div style={{
                        fontSize: "0.85rem",
                        color: "var(--bw-text-soft)",
                        lineHeight: 1.5,
                        marginBottom: "0.5rem",
                      }}>
                        {policy.content.slice(0, 120)}
                        {policy.content.length > 120
                          ? "…" : ""}
                      </div>
                      <div style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}>
                        <span style={{
                          fontSize: "0.75rem",
                          color: "var(--bw-text-soft)",
                        }}>
                          verified {policy.last_verified}
                        </span>
                        {isSensitive ? (
                          <span style={{
                            fontSize: "0.75rem",
                            color: "var(--bw-text-soft)",
                            fontStyle: "italic",
                          }}>
                            Safety policy — contact support to edit
                          </span>
                        ) : (
                          <button
                            onClick={() => {
                              setEditing(policy.id);
                              setEditForm({
                                title: policy.title,
                                content: policy.content,
                                action: policy.action,
                              });
                            }}
                            style={{
                              background: "none",
                              border: "1.5px solid var(--bw-border)",
                              borderRadius: "8px",
                              padding: "0.25rem 0.65rem",
                              fontSize: "0.8rem",
                              color: "var(--bw-text-soft)",
                            }}
                          >
                            Edit
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function OperatorView({ onLogout, navigate }) {
  const [tab, setTab] = useState("questions");
  const [refresh, setRefresh] = useState(0);

  function switchTab(id) {
    setTab(id);
    setRefresh(r => r + 1);
  }

  function forceRefresh() {
    setRefresh(r => r + 1);
  }

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100dvh",
      background: "var(--bw-bg)",
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
          color: "white",
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}>
          ☀️ Staff Control Center
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={forceRefresh}
            style={{
              background: "rgba(255,255,255,0.15)",
              border: "none",
              borderRadius: "8px",
              color: "white",
              fontSize: "0.85rem",
              padding: "0.35rem 0.65rem",
            }}
          >
            ↻
          </button>
          <button
            onClick={() => navigate("/")}
            style={{
              background: "rgba(255,255,255,0.15)",
              border: "none",
              borderRadius: "8px",
              color: "white",
              fontSize: "0.75rem",
              padding: "0.35rem 0.65rem",
            }}
          >
            Parent View
          </button>
          <button
            onClick={onLogout}
            style={{
              background: "rgba(255,255,255,0.15)",
              border: "none",
              borderRadius: "8px",
              color: "white",
              fontSize: "0.75rem",
              padding: "0.35rem 0.65rem",
            }}
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex",
        borderBottom: "1px solid var(--bw-border)",
        background: "var(--bw-surface)",
        flexShrink: 0,
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => switchTab(t.id)}
            style={{
              flex: 1,
              padding: "0.75rem 0.5rem",
              border: "none",
              borderBottom: tab === t.id
                ? "2px solid var(--bw-indigo)"
                : "2px solid transparent",
              background: "none",
              color: tab === t.id
                ? "var(--bw-indigo)"
                : "var(--bw-text-soft)",
              fontSize: "0.85rem",
              fontWeight: tab === t.id ? 700 : 400,
              fontFamily: "var(--font)",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "1.25rem",
      }}>
        {tab === "questions" && (
          <QuestionsTab refresh={refresh} />
        )}
        {tab === "queue" && (
          <QueueTab
            refresh={refresh}
            onPolicyCreated={forceRefresh}
          />
        )}
        {tab === "knowledge" && (
          <KnowledgeTab refresh={refresh} />
        )}
      </div>
    </div>
  );
}