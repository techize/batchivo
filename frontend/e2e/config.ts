/**
 * E2E Test Configuration
 *
 * Centralized configuration for E2E tests.
 * Uses environment variables with sensible defaults.
 */

// API URL for backend requests
export const API_URL = process.env.PLAYWRIGHT_API_URL || 'https://api.nozzly.app'

// Health check endpoint
export const HEALTH_URL = `${API_URL}/health`
