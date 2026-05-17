/**
 * LoadingSpinner — animated CSS spinner, no external library.
 */
export default function LoadingSpinner() {
  return (
    <div className="spinner-wrapper" role="status" aria-label="Loading">
      <div className="spinner" />
      <span className="spinner-text">Downloading…</span>
    </div>
  )
}
