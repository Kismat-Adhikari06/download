/**
 * UrlInput — controlled text input for the media URL.
 *
 * Props:
 *   url       {string}   current URL value
 *   onChange  {function} called with the new string on every keystroke
 *   urlError  {string}   inline validation error; shown below input when non-empty
 *   disabled  {boolean}  disables the input while a request is in-flight
 */
export default function UrlInput({ url, onChange, urlError, disabled }) {
  return (
    <div className="url-input-wrapper">
      <label htmlFor="url-input" className="field-label">
        Media URL
      </label>
      <input
        id="url-input"
        type="text"
        className={`url-input${urlError ? ' url-input--error' : ''}`}
        value={url}
        onChange={(e) => onChange(e.target.value)}
        placeholder="https://www.youtube.com/watch?v=..."
        disabled={disabled}
        aria-describedby={urlError ? 'url-error' : undefined}
        aria-invalid={urlError ? 'true' : 'false'}
      />
      {urlError && (
        <span id="url-error" className="field-error" role="alert">
          {urlError}
        </span>
      )}
    </div>
  )
}
