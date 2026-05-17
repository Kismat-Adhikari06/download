import LoadingSpinner from './LoadingSpinner.jsx'
import DownloadLink from './DownloadLink.jsx'
import ErrorMessage from './ErrorMessage.jsx'

/**
 * StatusDisplay — switches between spinner, download link, and error message.
 *
 * Props:
 *   status    {'idle'|'loading'|'success'|'error'}
 *   result    {{ download_url: string, filename: string } | null}
 *   errorMsg  {string}
 */
export default function StatusDisplay({ status, result, errorMsg }) {
  if (status === 'loading') {
    return <LoadingSpinner />
  }

  if (status === 'success' && result) {
    return (
      <DownloadLink
        download_url={result.download_url}
        filename={result.filename}
      />
    )
  }

  if (status === 'error' && errorMsg) {
    return <ErrorMessage message={errorMsg} />
  }

  return null
}
