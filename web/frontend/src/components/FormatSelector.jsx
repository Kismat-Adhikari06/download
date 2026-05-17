/**
 * FormatSelector — two pill buttons for choosing Video or Audio.
 *
 * Props:
 *   format    {'video'|'audio'} currently selected format
 *   onChange  {function}        called with 'video' or 'audio' on selection
 *   disabled  {boolean}         disables both buttons while a request is in-flight
 */
const FORMATS = [
  { value: 'video', label: 'Video' },
  { value: 'audio', label: 'Audio' },
]

export default function FormatSelector({ format, onChange, disabled }) {
  return (
    <div className="format-selector" role="group" aria-label="Output format">
      {FORMATS.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          className={`format-btn${format === value ? ' active' : ''}`}
          onClick={() => onChange(value)}
          disabled={disabled}
          aria-pressed={format === value}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
