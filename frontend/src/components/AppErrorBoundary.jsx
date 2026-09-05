import { Component } from "react"
import "./AppErrorBoundary.css"

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error) {
    if (import.meta.env.DEV) {
      console.error("The marketplace interface could not render", error)
      return
    }
    console.error("The marketplace interface could not render")
  }

  render() {
    if (!this.state.failed) return this.props.children

    return (
      <main className="app-error-page">
        <section className="app-error-card" role="alert">
          <span aria-hidden="true">⌂</span>
          <h1>Ocurrió un problema</h1>
          <p>Su información no fue enviada. Recargue la página para intentarlo nuevamente o vuelva al inicio si el problema continúa.</p>
          <div>
            <button type="button" onClick={() => window.location.reload()}>Recargar página</button>
            <a href="/">Volver al inicio</a>
          </div>
        </section>
      </main>
    )
  }
}

export default AppErrorBoundary
