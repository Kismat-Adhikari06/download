import { useState } from 'react'
import DownloadForm from './components/DownloadForm.jsx'
import StatusDisplay from './components/StatusDisplay.jsx'
import { requestDownload } from './api.js'
import './styles/main.css'

/**
 * App — root component, owns all state.
 *
 * State:
 *   url       {string}
 *   format    {'video'|'audio'}
 *   status    {'idle'|'loading'|'success'|'error'}
 *   result    {{ download_url, filename } | null}
 *   errorMsg  {string}
 *   urlError  {string}  inline validation error for the URL field
 */
export default function App() {
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('video')
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [urlError, setUrlError] = useState('')

  async function handleSubmit(submittedUrl, submittedFormat) {
    // Client-side validation
    if (!submittedUrl || submittedUrl.trim() === '') {
      setUrlError('Please enter a URL.')
      return
    }
    setUrlError('')

    setStatus('loading')
    setResult(null)
    setErrorMsg('')

    try {
      const data = await requestDownload(submittedUrl.trim(), submittedFormat)
      setResult(data)
      setStatus('success')
    } catch (err) {
      setErrorMsg(err.message ?? 'An unexpected error occurred.')
      setStatus('error')
    }
  }

  const isLoading = status === 'loading'

  return (
    <main className="app-container">
      <div className="card">
        <h1 className="card-title">Universal Media Downloader</h1>
        <p className="card-subtitle">
          Paste a URL, choose a format, and download.
        </p>

        <DownloadForm
          url={url}
          onUrlChange={setUrl}
          urlError={urlError}
          format={format}
          onFormatChange={setFormat}
          isLoading={isLoading}
          onSubmit={handleSubmit}
        />

        <StatusDisplay
          status={status}
          result={result}
          errorMsg={errorMsg}
        />
      </div>
    </main>
  )
}
