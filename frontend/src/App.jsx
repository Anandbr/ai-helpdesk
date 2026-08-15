import { useState, useEffect } from "react";
import ParentView from "./ParentView";
import OperatorView from "./OperatorView";
import { API, ApiError } from "./api";
import "./index.css";

function PinGate({ onSuccess }) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function tryPin(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      API.setPin(pin);
      await API.operator.policies();
      onSuccess();
    } catch (err) {
      API.clearPin();
      if (err instanceof ApiError && err.status === 401) {
        setError("Incorrect PIN. Try again.");
      } else {
        setError("Connection error. Is the server running?");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--bw-bg)",
    }}>
      <div style={{
        background: "var(--bw-surface)",
        borderRadius: "var(--radius-card)",
        padding: "2rem",
        width: "100%",
        maxWidth: "360px",
        boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
      }}>
        <div style={{
          background: "var(--bw-indigo)",
          borderRadius: "12px",
          padding: "1rem",
          marginBottom: "1.5rem",
          textAlign: "center",
          color: "white",
        }}>
          <div style={{ fontSize: "2rem" }}>☀️</div>
          <div style={{
            fontWeight: 700,
            fontSize: "1rem",
            marginTop: "0.5rem",
          }}>
            Staff Control Center
          </div>
          <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
            Sunshine Early Learning Center
          </div>
        </div>

        <form onSubmit={tryPin}>
          <label style={{
            display: "block",
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "var(--bw-text-soft)",
            marginBottom: "0.5rem",
          }}>
            Staff PIN
          </label>
          <input
            type="password"
            value={pin}
            onChange={e => setPin(e.target.value)}
            placeholder="Enter PIN"
            style={{
              width: "100%",
              padding: "0.75rem 1rem",
              border: `1.5px solid ${error
                ? "var(--bw-coral)"
                : "var(--bw-border)"}`,
              borderRadius: "10px",
              fontSize: "1rem",
              outline: "none",
              marginBottom: "0.75rem",
              fontFamily: "var(--font)",
            }}
          />
          {error && (
            <div style={{
              color: "var(--bw-coral)",
              fontSize: "0.85rem",
              marginBottom: "0.75rem",
            }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !pin}
            style={{
              width: "100%",
              padding: "0.75rem",
              background: "var(--bw-indigo)",
              color: "white",
              border: "none",
              borderRadius: "10px",
              fontSize: "1rem",
              fontWeight: 600,
              opacity: loading || !pin ? 0.6 : 1,
            }}
          >
            {loading ? "Checking..." : "Sign In"}
          </button>
        </form>

        <div style={{
          textAlign: "center",
          marginTop: "1rem",
          fontSize: "0.8rem",
          color: "var(--bw-text-soft)",
        }}>
          Demo PIN: 1234
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [path, setPath] = useState(
    window.location.pathname
  );
  const [pinVerified, setPinVerified] = useState(!!API.pin);

  useEffect(() => {
    const handler = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  function navigate(to) {
    window.history.pushState({}, "", to);
    setPath(to);
  }

  if (path.startsWith("/operator")) {
    if (!pinVerified) {
      return (
        <PinGate onSuccess={() => setPinVerified(true)} />
      );
    }
    return (
      <OperatorView
        onLogout={() => {
          API.clearPin();
          setPinVerified(false);
          navigate("/");
        }}
        navigate={navigate}
      />
    );
  }

  return <ParentView navigate={navigate} />;
}