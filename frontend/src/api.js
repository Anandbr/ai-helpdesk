class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const API = {
  pin: sessionStorage.getItem("operator_pin") || null,

  async request(path, opts = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(opts.headers || {}),
    };
    if (API.pin) headers["X-Operator-Pin"] = API.pin;

    const res = await fetch(`/api${path}`, {
      ...opts,
      headers
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new ApiError(
        res.status,
        detail.detail || res.statusText
      );
    }
    return res.json();
  },

  ask: (question) =>
    API.request("/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  getPolicies: () => API.request("/policies"),

  setPin(pin) {
    API.pin = pin;
    sessionStorage.setItem("operator_pin", pin);
  },

  clearPin() {
    API.pin = null;
    sessionStorage.removeItem("operator_pin");
  },

  operator: {
    policies: () => API.request("/operator/policies"),
    createPolicy: (policy) =>
      API.request("/operator/policies", {
        method: "POST",
        body: JSON.stringify(policy),
      }),
    updatePolicy: (id, update) =>
      API.request(`/operator/policies/${id}`, {
        method: "PATCH",
        body: JSON.stringify(update),
      }),
    questions: () => API.request("/operator/questions"),
    flagged: () => API.request("/operator/flagged"),
    gaps: () => API.request("/operator/gaps"),
    updateGap: (id, update) =>
      API.request(`/operator/gaps/${id}`, {
        method: "PATCH",
        body: JSON.stringify(update),
      }),
    stale: () => API.request("/operator/stale"),
  },
};

export { API, ApiError };