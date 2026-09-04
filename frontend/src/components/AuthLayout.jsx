function ShieldMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.75 19 5.8v5.35c0 4.55-2.9 8.64-7 10.1-4.1-1.46-7-5.55-7-10.1V5.8l7-3.05Z" />
      <path d="m8.8 12 2.05 2.05 4.35-4.35" />
    </svg>
  )
}

function AuthLayout({ children, wide = false, eyebrow = "Property Marketplace" }) {
  return (
    <main className="auth-page">
      <div className={`auth-shell${wide ? " auth-shell-wide" : ""}`}>
        <aside className="auth-trust" aria-label="Account security information">
          <div className="auth-brand-mark"><ShieldMark /></div>
          <p className="auth-eyebrow">{eyebrow}</p>
          <h2>A safer way to find your next property.</h2>
          <p className="auth-trust-copy">
            Your account helps keep conversations, saved homes, and property activity in one protected place.
          </p>
          <ul className="auth-trust-list">
            <li><span aria-hidden="true">✓</span> Secure, time-limited account recovery</li>
            <li><span aria-hidden="true">✓</span> Protection against repeated sign-in attempts</li>
            <li><span aria-hidden="true">✓</span> Access your account from any trusted device</li>
          </ul>
        </aside>
        <section className="auth-card">{children}</section>
      </div>
    </main>
  )
}

export default AuthLayout
