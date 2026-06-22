/**
 * Client module for communicating with the backend API.
 * All functions return structured response objects; errors are returned
 * as { error: string } rather than thrown so the caller can handle them.
 */

/**
 * Upload a document (image/PDF) to the Flask processing endpoint.
 * @param {File} file
 * @param {object} [options]
 * @param {AbortSignal} [options.signal] - Optional AbortSignal to cancel the request.
 * @returns {Promise<object>} Upload result or { error: string }
 */
export async function uploadDocument(file, { signal } = {}) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/process', {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' },
            signal,
        });

        const data = await response.json();

        if (!response.ok) {
            return { error: data.error || `Server error (${response.status})` };
        }

        return data;
    } catch (err) {
        if (err.name === 'AbortError') {
            return { error: 'Upload cancelled', aborted: true };
        }
        return { error: 'Network error: could not reach the server.' };
    }
}

/**
 * Retrieve LaTeX code and asset preview data for a session.
 * @param {string} sessionId
 * @param {object} [options]
 * @param {AbortSignal} [options.signal] - Optional AbortSignal to cancel the request.
 * @returns {Promise<object>} Preview result or { error: string }
 */
export async function getPreviewData(sessionId, { signal } = {}) {
    try {
        const response = await fetch(`/preview/${encodeURIComponent(sessionId)}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            signal,
        });

        const data = await response.json();

        if (!response.ok) {
            return { error: data.error || `Server error (${response.status})` };
        }

        return data;
    } catch (err) {
        if (err.name === 'AbortError') {
            return { error: 'Request cancelled', aborted: true };
        }
        return { error: 'Network error: could not reach the server.' };
    }
}
