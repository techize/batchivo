import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Validates a redirect URL to prevent open redirect attacks.
 * Only allows relative paths (starting with /) or same-origin URLs.
 * Returns the default path if the URL is invalid or external.
 */
export function getSafeRedirectUrl(url: string | null, defaultPath = '/dashboard'): string {
  if (!url) {
    return defaultPath
  }

  // Only allow relative paths starting with /
  // This prevents:
  // - Protocol-relative URLs (//evil.com)
  // - Absolute URLs (https://evil.com)
  // - javascript: URLs
  // - data: URLs
  if (url.startsWith('/') && !url.startsWith('//')) {
    return url
  }

  // If it's an absolute URL, check if it's same-origin
  try {
    const redirectUrl = new URL(url, window.location.origin)
    if (redirectUrl.origin === window.location.origin) {
      return redirectUrl.pathname + redirectUrl.search
    }
  } catch {
    // Invalid URL
  }

  return defaultPath
}
