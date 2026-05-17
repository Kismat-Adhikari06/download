/**
 * ErrorMessage — styled container for error text.
 *
 * Props:
 *   message {string} error message to display
 */
export default function ErrorMessage({ message }) {
  return (
    <div className="error-message" role="alert">
      <strong>Error: </strong>
      {message}
    </div>
  )
}
