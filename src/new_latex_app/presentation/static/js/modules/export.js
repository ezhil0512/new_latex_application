/**
 * Phase 5 — Export Interface Module
 * Handles .tex download (anchor-based Blob URL), .zip download (fetch-based),
 * clipboard copy, and export feedback notifications.
 */

import { fetchExportZip } from './api.js';
import { copyToClipboard } from './utils.js';
import { showExportToast } from './ui.js';

/** @type {string|null} Track active .tex Blob URL for cleanup */
let activeTexBlobUrl = null;

/** @type {boolean} Prevent concurrent zip downloads */
let isZipDownloading = false;

/* ------------------------------------------------------------------ */
/*  .TEX Download (Anchor-based Blob URL)                              */
/* ------------------------------------------------------------------ */

/**
 * Prepare the .tex download anchor with a fresh Blob URL.
 * Revokes any previously created Blob URL to prevent memory leaks.
 * @param {HTMLAnchorElement} anchorElement
 * @param {string} latexCode
 * @param {string} originalFilename
 */
export function prepareTexDownload(anchorElement, latexCode, originalFilename) {
    if (!anchorElement || !latexCode) return;

    // Revoke previous Blob URL
    if (activeTexBlobUrl) {
        try { URL.revokeObjectURL(activeTexBlobUrl); } catch (_e) { /* ignore */ }
        activeTexBlobUrl = null;
    }

    const texBlob = new Blob([latexCode], { type: 'text/plain;charset=utf-8' });
    activeTexBlobUrl = URL.createObjectURL(texBlob);

    anchorElement.href = activeTexBlobUrl;
    anchorElement.download = originalFilename.replace(/\.[^/.]+$/, '') + '.tex';
}

/**
 * Show success feedback when the .tex download anchor is clicked.
 * @param {HTMLAnchorElement} anchorElement
 */
export function handleTexDownloadClick(anchorElement) {
    if (!anchorElement || anchorElement.classList.contains('disabled')) return;

    showExportToast('LaTeX file downloaded successfully', 'success');
    _flashExportSuccess(anchorElement);
}

/* ------------------------------------------------------------------ */
/*  .ZIP Download (Fetch-based with error handling)                    */
/* ------------------------------------------------------------------ */

/**
 * Download the export .zip package via fetch with loading states and error handling.
 * Prevents the browser from navigating to error JSON responses by intercepting
 * HTTP errors before triggering the download.
 * @param {string} sessionId
 * @param {HTMLButtonElement} buttonElement
 */
export async function downloadZipExport(sessionId, buttonElement) {
    if (!sessionId || isZipDownloading) return;

    isZipDownloading = true;
    const originalHTML = buttonElement ? buttonElement.innerHTML : '';

    // Set loading state
    if (buttonElement) {
        buttonElement.disabled = true;
        buttonElement.classList.add('btn-export-loading');
        buttonElement.innerHTML = '<span class="export-spinner" aria-hidden="true"></span> Downloading…';
    }

    try {
        const result = await fetchExportZip(sessionId);

        if (result.error) {
            showExportToast(result.error, 'error');
            if (buttonElement) {
                _flashExportError(buttonElement);
            }
            return;
        }

        // Trigger download from the fetched Blob
        const url = URL.createObjectURL(result.blob);
        const tempAnchor = document.createElement('a');
        tempAnchor.href = url;
        tempAnchor.download = result.filename || `export_${sessionId}.zip`;
        tempAnchor.style.display = 'none';
        document.body.appendChild(tempAnchor);
        tempAnchor.click();

        // Cleanup temporary anchor and Blob URL
        setTimeout(() => {
            document.body.removeChild(tempAnchor);
            URL.revokeObjectURL(url);
        }, 150);

        showExportToast('Export package downloaded successfully', 'success');
        if (buttonElement) {
            _flashExportSuccess(buttonElement);
        }
    } catch (error) {
        console.error('ZIP download failed:', error);
        showExportToast('Download failed. Please try again.', 'error');
        if (buttonElement) {
            _flashExportError(buttonElement);
        }
    } finally {
        isZipDownloading = false;
        if (buttonElement) {
            buttonElement.classList.remove('btn-export-loading');
            buttonElement.innerHTML = originalHTML;
            buttonElement.disabled = false;
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Copy LaTeX to Clipboard                                            */
/* ------------------------------------------------------------------ */

/**
 * Copy LaTeX code to clipboard with export feedback (toast + button flash).
 * @param {string} latexCode
 * @param {HTMLButtonElement} buttonElement
 */
export async function copyLatexToClipboard(latexCode, buttonElement) {
    if (!latexCode) return;

    const success = await copyToClipboard(latexCode);

    if (success) {
        showExportToast('LaTeX code copied to clipboard', 'success');
        if (buttonElement) {
            const originalText = buttonElement.textContent;
            buttonElement.textContent = 'Copied!';
            _flashExportSuccess(buttonElement);
            setTimeout(() => {
                buttonElement.textContent = originalText;
            }, 2000);
        }
    } else {
        showExportToast('Failed to copy to clipboard', 'error');
        if (buttonElement) {
            _flashExportError(buttonElement);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Cleanup                                                            */
/* ------------------------------------------------------------------ */

/**
 * Revoke any active export Blob URLs to free memory.
 * Call when clearing selection or before re-generating.
 */
export function revokeExportUrls() {
    if (activeTexBlobUrl) {
        try { URL.revokeObjectURL(activeTexBlobUrl); } catch (_e) { /* ignore */ }
        activeTexBlobUrl = null;
    }
}

/* ------------------------------------------------------------------ */
/*  Button Flash Helpers (Internal)                                    */
/* ------------------------------------------------------------------ */

/**
 * Briefly apply success styling to an export element.
 * @param {HTMLElement} element
 */
function _flashExportSuccess(element) {
    if (!element) return;
    element.classList.add('btn-export-success');
    setTimeout(() => {
        element.classList.remove('btn-export-success');
    }, 2000);
}

/**
 * Briefly apply error styling to an export element.
 * @param {HTMLElement} element
 */
function _flashExportError(element) {
    if (!element) return;
    element.classList.add('btn-export-error');
    setTimeout(() => {
        element.classList.remove('btn-export-error');
    }, 3000);
}
