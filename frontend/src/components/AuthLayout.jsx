function AuthLayout({ children, wide = false, eyebrow = "HabitaRD" }) {
  return (
    <main className="auth-page">
      <div className={`auth-shell${wide ? " auth-shell-wide" : ""}`}>
        <aside className="auth-trust" aria-label="Información sobre la seguridad de la cuenta">
          <img
            className="auth-trust-background"
            src="/residence-panel-v1.jpg"
            alt=""
            aria-hidden="true"
          />
          <div className="auth-brand-mark"><img src="/habitard-logo.jpeg" alt="" width="56" height="56" /></div>
          <p className="auth-eyebrow">{eyebrow}</p>
          <h2>Una forma más segura de encontrar su próxima propiedad.</h2>
          <p className="auth-trust-copy">
            Un espacio pensado para acompañarle con calma, desde la primera búsqueda hasta encontrar un lugar verdaderamente especial.
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
