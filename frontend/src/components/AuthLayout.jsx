function ShieldMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.75 19 5.8v5.35c0 4.55-2.9 8.64-7 10.1-4.1-1.46-7-5.55-7-10.1V5.8l7-3.05Z" />
      <path d="m8.8 12 2.05 2.05 4.35-4.35" />
    </svg>
  )
}

function AuthLayout({ children, wide = false, eyebrow = "HabitaRD" }) {
  return (
    <main className="auth-page">
      <div className={`auth-shell${wide ? " auth-shell-wide" : ""}`}>
        <aside className="auth-trust" aria-label="Información sobre la seguridad de la cuenta">
          <div className="auth-brand-mark"><ShieldMark /></div>
          <p className="auth-eyebrow">{eyebrow}</p>
          <h2>Una forma más segura de encontrar su próxima propiedad.</h2>
          <p className="auth-trust-copy">
            Su cuenta mantiene sus conversaciones, propiedades guardadas y actividad en un solo lugar protegido.
          </p>
          <ul className="auth-trust-list">
            <li><span aria-hidden="true">✓</span> Recuperación segura con tiempo limitado</li>
            <li><span aria-hidden="true">✓</span> Protección contra intentos repetidos de acceso</li>
            <li><span aria-hidden="true">✓</span> Acceso desde cualquier dispositivo de confianza</li>
          </ul>
        </aside>
        <section className="auth-card">{children}</section>
      </div>
    </main>
  )
}

export default AuthLayout
