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
    console.error("The marketplace interface could not render", error)
  }

  render() {
    if (!this.state.failed) return this.props.children

    return (
      <main className="app-error-page">
        <section className="app-error-card" role="alert">
          <span aria-hidden="true">⌂</span>
          <h1>Something went wrong</h1>
          <p>Your information was not submitted. Reload the page to try again, or return home if the problem continues.</p>
          <div>
            <button type="button" onClick={() => window.location.reload()}>Reload page</button>
            <a href="/">Return home</a>
          </div>
        </section>
      </main>
    )
  }
}

export default AppErrorBoundary
