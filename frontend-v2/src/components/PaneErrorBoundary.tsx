import { Component, type ReactNode } from 'react'
import './PaneErrorBoundary.css'
import {
  forceReloadForChunkError,
  installChunkPreloadRecovery,
  isChunkLoadError,
  maybeAutoReloadForChunkError,
} from '../lib/chunkReload'

// Global net for Vite's `vite:preloadError` (fired before the failed dynamic
// import rethrows): after a deploy the stale index/SW references dead-hash
// chunks and a guarded document reload is the only cure. Installed from here —
// this component IS the recovery surface for both keep-alive panes, and it
// ships in the entry chunk (main.tsx renders it directly). Idempotent.
installChunkPreloadRecovery()

interface Props {
  /** What failed, in the reader's words: "the console", "the Brief". */
  paneName: string
  /**
   * Changing this clears the error. Wired to the visible route, so tapping
   * another tab and coming back is itself the retry — the reader should not
   * have to find a button to get a second attempt.
   */
  resetKey?: string
  children: ReactNode
}

interface State { crashed: boolean; message: string; resetKey?: string }

/**
 * One keep-alive pane's blast radius.
 *
 * WHY THIS EXISTS (C5). `RootErrorBoundary` in main.tsx wraps EVERYTHING —
 * including `<MobileTabBar/>`. So a throw anywhere inside the console, at a
 * moment when a rate-limited backend is handing panels shapes they did not
 * expect, replaced the entire page: the three tabs disappeared along with the
 * surface that failed, and the only control left was Reload. That is the
 * opposite of what the phone shell promises — the bar is deliberately rendered
 * at the root, outside <Routes>, precisely so it survives whatever a pane does.
 *
 * Boundarying each pane keeps that promise: the failing pane says so in its own
 * space, the bar underneath stays live, and the reader can leave for a surface
 * that works instead of reloading. The page scroll is untouched here — the
 * shared lock (lib/scrollLock) is released by the unmount this boundary
 * performs, so a pane that crashed holding it cannot leave the page frozen.
 */
export class PaneErrorBoundary extends Component<Props, State> {
  state: State = { crashed: false, message: '' }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { crashed: true, message: error.message }
  }

  static getDerivedStateFromProps(props: Props, state: State): Partial<State> | null {
    if (state.resetKey !== props.resetKey) {
      return { crashed: false, message: '', resetKey: props.resetKey }
    }
    return null
  }

  componentDidCatch(error: Error) {
    console.error(`[PaneErrorBoundary:${this.props.paneName}]`, error)
    // Stale-chunk class (post-deploy: "Unable to preload CSS…", "Failed to
    // fetch dynamically imported module…"): React.lazy caches the rejected
    // import, so the state-reset retry below can never recover — re-rendering
    // rethrows the same error. A document reload against the fresh index/SW is
    // the cure; sessionStorage-guarded so a reload that does NOT cure (offline)
    // stops cycling and lands on the card, where TRY AGAIN reloads manually.
    maybeAutoReloadForChunkError(error.message)
  }

  private retry = () => {
    if (isChunkLoadError(this.state.message)) {
      // Reader-initiated: bypass the auto-reload guard — a click per attempt
      // can never cycle. Also nudges the SW to update before reloading.
      forceReloadForChunkError()
      return
    }
    this.setState({ crashed: false, message: '' })
  }

  render() {
    if (!this.state.crashed) return this.props.children
    return (
      <div className="pane-error" role="alert">
        <div className="pane-error-icon" aria-hidden="true">⚠</div>
        <div className="pane-error-title">{this.props.paneName} could not render</div>
        {/* Honest about what is and is not known: the pane failed, which says
            nothing about the data it was going to show. No fabricated zero, no
            "nothing to report" — the same rule the lanes inside it follow. */}
        <p className="pane-error-body">
          This surface hit an error. Nothing here is a measurement — the tabs
          below still work.
        </p>
        {this.state.message && <div className="pane-error-detail">{this.state.message}</div>}
        <button type="button" className="pane-error-retry" onClick={this.retry}>
          TRY AGAIN
        </button>
      </div>
    )
  }
}
