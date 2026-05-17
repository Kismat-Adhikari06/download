/**
 * Tests for App component.
 *
 * Smoke tests + property-based tests:
 *   Property 4: Loading state is shown for any valid submission
 *   Property 5: Success response always produces a result state
 *   Property 6: Error response always produces an error state
 */
import { render, screen, fireEvent, waitFor, act, cleanup } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'
import App from '../App.jsx'

// Mock the api module
vi.mock('../api.js', () => ({
  requestDownload: vi.fn(),
}))

import { requestDownload } from '../api.js'

// ---------------------------------------------------------------------------
// Smoke tests
// ---------------------------------------------------------------------------

describe('App — smoke tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the URL input field', () => {
    render(<App />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('renders Video and Audio format options', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: /video/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /audio/i })).toBeInTheDocument()
  })

  it('renders the Download button', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument()
  })

  it('defaults format to Video', () => {
    render(<App />)
    const videoBtn = screen.getByRole('button', { name: /video/i })
    expect(videoBtn).toHaveClass('active')
  })

  it('shows inline error when submitting with empty URL', async () => {
    render(<App />)
    fireEvent.submit(
      screen.getByRole('button', { name: /download/i }).closest('form')
    )
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('does not call requestDownload when URL is empty', async () => {
    render(<App />)
    fireEvent.submit(
      screen.getByRole('button', { name: /download/i }).closest('form')
    )
    expect(requestDownload).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Property 4: Loading state is shown for any valid submission
// // Feature: web-ui, Property 4: Loading state is shown for any valid submission
// Validates: Requirements 3.2, 3.3
// ---------------------------------------------------------------------------

describe('App — Property 4: Loading state on valid submission', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows loading spinner and disables submit button while request is in-flight', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }).filter((s) => s.trim() !== ''),
        (url) => {
          // Never resolves — keeps the request in-flight
          requestDownload.mockReturnValue(new Promise(() => {}))

          const { container, unmount } = render(<App />)

          const input = container.querySelector('#url-input')
          fireEvent.change(input, { target: { value: url } })

          const form = container.querySelector('form')
          fireEvent.submit(form)

          // Submit button should be disabled
          const submitBtn = container.querySelector('button[type="submit"]')
          expect(submitBtn).toBeDisabled()

          // Loading spinner should be visible
          const spinner = container.querySelector('[role="status"]')
          expect(spinner).not.toBeNull()

          unmount()
          cleanup()
        }
      ),
      { numRuns: 20 }
    )
  })
})

// ---------------------------------------------------------------------------
// Property 5: Success response always produces a result state
// // Feature: web-ui, Property 5: Success response always produces a result state
// Validates: Requirements 3.4, 8.1, 8.2
// ---------------------------------------------------------------------------

describe('App — Property 5: Success response produces result state', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows download link after successful response', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          download_url: fc.webUrl(),
          filename: fc.string({ minLength: 1 }),
        }),
        async ({ download_url, filename }) => {
          requestDownload.mockResolvedValue({ download_url, filename })

          const { container, unmount } = render(<App />)

          const input = container.querySelector('#url-input')
          fireEvent.change(input, { target: { value: 'https://example.com' } })

          await act(async () => {
            fireEvent.submit(container.querySelector('form'))
          })

          // Wait for the link to appear
          await waitFor(() => {
            expect(container.querySelector('a')).not.toBeNull()
          })

          const link = container.querySelector('a')
          expect(link.getAttribute('href')).toBe(download_url)
          expect(link.getAttribute('download')).toBe(filename)
          expect(link.textContent).toContain(filename)

          unmount()
          cleanup()
        }
      ),
      { numRuns: 20 }
    )
  })
})

// ---------------------------------------------------------------------------
// Property 6: Error response always produces an error state
// // Feature: web-ui, Property 6: Error response always produces an error state
// Validates: Requirements 3.5
// ---------------------------------------------------------------------------

describe('App — Property 6: Error response produces error state', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows error message after failed response', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1 }),
        async (errorMessage) => {
          requestDownload.mockRejectedValue(new Error(errorMessage))

          const { container, unmount } = render(<App />)

          const input = container.querySelector('#url-input')
          fireEvent.change(input, { target: { value: 'https://example.com' } })

          await act(async () => {
            fireEvent.submit(container.querySelector('form'))
          })

          await waitFor(() => {
            expect(container.querySelector('[role="alert"]')).not.toBeNull()
          })

          const alert = container.querySelector('[role="alert"]')
          expect(alert.textContent).toContain(errorMessage)

          unmount()
          cleanup()
        }
      ),
      { numRuns: 20 }
    )
  })
})
