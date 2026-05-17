/**
 * SubmitButton — the Download button.
 *
 * Props:
 *   disabled {boolean} disables the button when true (e.g. while loading)
 */
export default function SubmitButton({ disabled }) {
  return (
    <button
      type="submit"
      className={`submit-btn${disabled ? ' submit-btn--disabled' : ''}`}
      disabled={disabled}
    >
      Download
    </button>
  )
}
