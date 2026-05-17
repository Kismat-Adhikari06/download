/**
 * DownloadLink — renders a clickable download anchor.
 *
 * Props:
 *   download_url {string} href for the anchor (Temp_Link from backend)
 *   filename     {string} suggested save-as filename; also shown as visible text
 */
export default function DownloadLink({ download_url, filename }) {
  return (
    <div className="download-link-wrapper">
      <p className="download-ready-text">Your file is ready:</p>
      <a
        href={download_url}
        download={filename}
        className="download-link"
      >
        {filename}
      </a>
    </div>
  )
}
