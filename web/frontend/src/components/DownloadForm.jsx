import UrlInput from './UrlInput.jsx'
import FormatSelector from './FormatSelector.jsx'
import SubmitButton from './SubmitButton.jsx'

/**
 * DownloadForm — composes UrlInput, FormatSelector, and SubmitButton.
 *
 * Props:
 *   url        {string}
 *   onUrlChange {function}
 *   urlError   {string}
 *   format     {'video'|'audio'}
 *   onFormatChange {function}
 *   isLoading  {boolean}
 *   onSubmit   {function}  called with validated (url, format) when form is valid
 */
export default function DownloadForm({
  url,
  onUrlChange,
  urlError,
  format,
  onFormatChange,
  isLoading,
  onSubmit,
}) {
  function handleSubmit(e) {
    e.preventDefault()
    onSubmit(url, format)
  }

  return (
    <form className="download-form" onSubmit={handleSubmit} noValidate>
      <UrlInput
        url={url}
        onChange={onUrlChange}
        urlError={urlError}
        disabled={isLoading}
      />
      <FormatSelector
        format={format}
        onChange={onFormatChange}
        disabled={isLoading}
      />
      <SubmitButton disabled={isLoading} />
    </form>
  )
}
