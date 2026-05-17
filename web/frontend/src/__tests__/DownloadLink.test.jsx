/**
 * Tests for DownloadLink component.
 *
 * Property 14: Download link renders all required information
 * // Feature: web-ui, Property 14: Download link renders all required information
 * Validates: Requirements 8.1, 8.2, 8.3
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import DownloadLink from '../components/DownloadLink.jsx'

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

describe('DownloadLink', () => {
  it('renders an anchor with the correct href', () => {
    render(
      <DownloadLink
        download_url="http://localhost:8000/files/abc/video.mp4"
        filename="video.mp4"
      />
    )
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', 'http://localhost:8000/files/abc/video.mp4')
  })

  it('renders an anchor with the correct download attribute', () => {
    render(
      <DownloadLink
        download_url="http://localhost:8000/files/abc/video.mp4"
        filename="video.mp4"
      />
    )
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('download', 'video.mp4')
  })

  it('displays the filename as visible text', () => {
    render(
      <DownloadLink
        download_url="http://localhost:8000/files/abc/audio.mp3"
        filename="audio.mp3"
      />
    )
    expect(screen.getByText('audio.mp3')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Property 14: Download link renders all required information
// // Feature: web-ui, Property 14: Download link renders all required information
// Validates: Requirements 8.1, 8.2, 8.3
// ---------------------------------------------------------------------------

describe('DownloadLink — Property 14', () => {
  it('always renders href, download attribute, and visible filename', () => {
    fc.assert(
      fc.property(
        fc.record({
          download_url: fc.webUrl(),
          filename: fc.string({ minLength: 1 }),
        }),
        ({ download_url, filename }) => {
          const { unmount } = render(
            <DownloadLink download_url={download_url} filename={filename} />
          )

          const link = document.querySelector('a')
          expect(link).not.toBeNull()
          expect(link.getAttribute('href')).toBe(download_url)
          expect(link.getAttribute('download')).toBe(filename)
          expect(link.textContent).toContain(filename)

          unmount()
        }
      ),
      { numRuns: 100 }
    )
  })
})
