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

/**
 * Fetch the export ZIP package for a session.
 * Uses fetch() instead of a bare anchor href to allow HTTP error interception
 * before triggering the download, preventing the browser from navigating to
 * an error JSON response.
 * @param {string} sessionId
 * @returns {Promise<object>} { blob, filename } on success, { error } on failure
 */
export async function fetchExportZip(sessionId) {
    try {
        const response = await fetch(`/download/${encodeURIComponent(sessionId)}`, {
            method: 'GET',
        });

        if (!response.ok) {
            try {
                const errorData = await response.json();
                return { error: errorData.error || `Download failed (${response.status})` };
            } catch (_e) {
                return { error: `Download failed (${response.status})` };
            }
        }

        const blob = await response.blob();

        // Extract filename from Content-Disposition header if available
        const disposition = response.headers.get('Content-Disposition');
        let filename = `export_${sessionId}.zip`;
        if (disposition) {
            const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
            }
        }

        return { blob, filename };
    } catch (_err) {
        return { error: 'Network error: could not download export package.' };
    }
}
