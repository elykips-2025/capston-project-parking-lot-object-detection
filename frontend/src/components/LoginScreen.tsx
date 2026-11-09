import { useState, type FormEvent } from "react";
import { login } from "../api/auth";
import "./LoginScreen.css";
import { ApiError } from "../api/client";

type Props = {
  onAuthenticated: () => void;
};

export default function LoginScreen({ onAuthenticated }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      await login(email, password);
      setPassword("");
      onAuthenticated();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid email or password.");
      } else if (err instanceof ApiError && err.status === 429) {
        setError("Too many login attempts. Please try again later.");
      } else {
        setError(
          err instanceof Error ? err.message : "Unable to sign in.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-showcase" aria-label="About ParkSight AI">
        <div className="login-brand">
          <span className="login-brand-icon" aria-hidden="true">P</span>
          <span>ParkSight AI</span>
        </div>

        <div className="login-showcase-content">
          <span className="login-eyebrow">
            Intelligent parking operations
          </span>
          <h2>Smarter parking. Better decisions.</h2>
          <p>
            Turn camera footage into actionable parking intelligence.
            Monitor occupancy, analyse trends and manage parking sites
            from one platform.
          </p>
        </div>

        <div className="login-showcase-footer">
          Computer vision-powered parking intelligence
        </div>
      </section>

      <section className="login-auth-panel">
      <section className="login-card">
        {/* <div className="login-brand">
          <span className="login-brand-icon">P</span>
          <span>ParkSight AI</span>
        </div> */}

        <h1>Welcome back</h1>
        <p>Sign in to manage your parking operations.</p>

        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="login-email">Email address</label>
          <input
            id="login-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            maxLength={320}
            disabled={submitting}
          />

          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            disabled={submitting}
          />

          {error && (
            <p role="alert" className="login-error">
              {error}
            </p>
          )}

          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="login-footer">
          Secure parking intelligence platform
        </p>
      </section>
      </section>
    </main>
  );
}
