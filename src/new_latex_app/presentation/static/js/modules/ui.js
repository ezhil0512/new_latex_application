/**
 * Module responsible for standard UI state mutations, dropzone drag
 * animations, inline error messaging, and upload status display.
 */

/* ------------------------------------------------------------------ */
/*  Drag-and-Drop                                                     */
/* ------------------------------------------------------------------ */

/**
 * Initialize drag and drop events for the upload box.
 * @param {HTMLElement} dropZone
 * @param {Function} onFileDropped callback function when file is resolved
 */
export function initDragAndDrop(dropZone, onFileDropped) {
    if (!dropZone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            onFileDropped(files[0]);
        }
    }, false);
}

/* ------------------------------------------------------------------ */
/*  Pipeline Status Badge                                             */
/* ------------------------------------------------------------------ */

/**
 * Update the state of system badges (connection status & processing pipeline status).
 * @param {string} pipelineState 'idle' | 'busy'
 */
export function updatePipelineStatus(pipelineState) {
    const badge = document.getElementById('pipeline-status-badge');
    if (!badge) return;

    badge.className = 'badge';
    if (pipelineState === 'busy') {
        badge.classList.add('badge-busy');
        badge.textContent = 'Processing…';
    } else {
        badge.classList.add('badge-idle');
        badge.textContent = 'System Idle';
    }
}

/* ------------------------------------------------------------------ */
/*  Action Controls                                                    */
/* ------------------------------------------------------------------ */

/**
 * Enable or disable action buttons in the workspace.
 * @param {boolean} disabled
 */
export function toggleActionControls(disabled) {
    const generateBtn = document.getElementById('generate-latex-btn');
    const copyBtn = document.getElementById('copy-latex-btn');
    const downloadTexBtn = document.getElementById('download-tex-btn');
    const downloadZipBtn = document.getElementById('download-zip-btn');
    const selectAllBtn = document.getElementById('select-all-btn');
    const wordWrapToggle = document.getElementById('word-wrap-toggle');
    const spinner = document.getElementById('processing-spinner');

    if (generateBtn) {
        generateBtn.disabled = disabled;
    }
    if (spinner) {
        if (disabled) {
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }

    // Controls that should activate only after a successful compile
    if (!disabled) {
        const hasContent = document.getElementById('latex-code-output')?.value !== '';
        if (copyBtn) copyBtn.disabled = !hasContent;
        if (selectAllBtn) selectAllBtn.disabled = !hasContent;
        if (wordWrapToggle) wordWrapToggle.disabled = !hasContent;

        if (downloadTexBtn) {
            if (hasContent) {
                downloadTexBtn.classList.remove('disabled');
                downloadTexBtn.removeAttribute('aria-disabled');
            } else {
                downloadTexBtn.classList.add('disabled');
                downloadTexBtn.setAttribute('aria-disabled', 'true');
            }
        }

        if (downloadZipBtn) {
            const hasZip = downloadZipBtn.getAttribute('href') !== null && downloadZipBtn.getAttribute('href') !== '';
            if (hasZip && hasContent) {
                downloadZipBtn.classList.remove('disabled');
                downloadZipBtn.removeAttribute('aria-disabled');
            } else {
                downloadZipBtn.classList.add('disabled');
                downloadZipBtn.setAttribute('aria-disabled', 'true');
            }
        }
    } else {
        // Disable controls when processing
        if (copyBtn) copyBtn.disabled = true;
        if (selectAllBtn) selectAllBtn.disabled = true;
        if (wordWrapToggle) wordWrapToggle.disabled = true;
        if (downloadTexBtn) {
            downloadTexBtn.classList.add('disabled');
            downloadTexBtn.setAttribute('aria-disabled', 'true');
        }
        if (downloadZipBtn) {
            downloadZipBtn.classList.add('disabled');
            downloadZipBtn.setAttribute('aria-disabled', 'true');
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Inline Error Messaging                                             */
/* ------------------------------------------------------------------ */

/**
 * Show an inline error message in the error message area.
 * @param {string} message
 */
export function showError(message) {
    const area = document.getElementById('error-message-area');
    if (!area) return;

    const textEl = area.querySelector('.error-message-text');
    if (textEl) {
        textEl.textContent = message;
    }
    area.classList.remove('hidden');
    area.classList.add('fade-in');
}

/**
 * Clear / dismiss the inline error message area.
 */
export function clearError() {
    const area = document.getElementById('error-message-area');
    if (!area) return;

    area.classList.add('hidden');
    area.classList.remove('fade-in');
}

/**
 * Toggle a visual error-state border on the drop zone.
 * @param {boolean} hasError
 */
export function setDropZoneError(hasError) {
    const dropZone = document.getElementById('drop-zone');
    if (!dropZone) return;

    if (hasError) {
        dropZone.classList.add('error-state');
    } else {
        dropZone.classList.remove('error-state');
    }
}

/* ------------------------------------------------------------------ */
/*  Upload Status Bar                                                  */
/* ------------------------------------------------------------------ */

/**
 * Show the upload status area with a message and optional indeterminate
 * progress bar.
 * @param {string} message
 * @param {boolean} [isIndeterminate=true]
 */
export function showUploadStatus(message, isIndeterminate = true) {
    const status = document.getElementById('upload-status');
    if (!status) return;

    const textEl = status.querySelector('.upload-status-text');
    const bar = status.querySelector('.progress-bar');

    if (textEl) textEl.textContent = message;
    if (bar) {
        bar.classList.toggle('indeterminate', isIndeterminate);
    }

    status.classList.remove('hidden');
    status.classList.add('fade-in');
}

/**
 * Hide the upload status area.
 */
export function hideUploadStatus() {
    const status = document.getElementById('upload-status');
    if (!status) return;

    status.classList.add('hidden');
    status.classList.remove('fade-in');
}

/* ------------------------------------------------------------------ */
/*  Processing Screen Controls                                        */
/* ------------------------------------------------------------------ */

/**
 * Show the processing card container.
 */
export function showProcessingCard() {
    const card = document.getElementById('processing-card');
    if (!card) return;

    card.classList.remove('hidden');
    card.classList.add('fade-in');
}

/**
 * Hide the processing card container.
 */
export function hideProcessingCard() {
    const card = document.getElementById('processing-card');
    if (!card) return;

    card.classList.add('hidden');
    card.classList.remove('fade-in');
}

/**
 * Update the status text of the processing pipeline.
 * @param {string} statusText
 */
export function updateProcessingStatus(statusText) {
    const textEl = document.getElementById('processing-status-text');
    if (textEl) {
        textEl.textContent = statusText;
    }
}

/**
 * Formats a duration in seconds to MM:SS and displays it in the processing timer.
 * @param {number} totalSeconds
 */
export function updateProcessingTimer(totalSeconds) {
    const timerEl = document.getElementById('processing-timer');
    if (!timerEl) return;

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    const formattedMinutes = String(minutes).padStart(2, '0');
    const formattedSeconds = String(seconds).padStart(2, '0');

    timerEl.textContent = `${formattedMinutes}:${formattedSeconds}`;
}

/* ------------------------------------------------------------------ */
/*  Phase 4 – Zoom & Viewer Controls                                  */
/* ------------------------------------------------------------------ */

let currentZoom = 1.0;
let isFitMode = true;

/**
 * Configure the visibility and initial state of image zoom controls.
 * Hides the zoom toolbar completely when previewing PDFs.
 * @param {File} file
 */
export function initZoomControls(file) {
    const zoomToolbar = document.getElementById('zoom-toolbar');
    if (!zoomToolbar) return;

    if (!file || file.type === 'application/pdf') {
        zoomToolbar.classList.add('hidden');
        return;
    }

    // Show zoom toolbar for images only
    zoomToolbar.classList.remove('hidden');

    const img = document.querySelector('#document-view-port img.preview-image');
    if (!img) return;

    // Reset styles to fit mode
    isFitMode = true;
    currentZoom = 1.0;
    img.style.maxWidth = '100%';
    img.style.maxHeight = '100%';
    img.style.width = 'auto';
    img.style.height = 'auto';
}

/**
 * Setup zoom button click listeners. Bind this once on page load.
 */
export function setupZoomListeners() {
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const zoomResetBtn = document.getElementById('zoom-reset-btn');
    const zoomFitBtn = document.getElementById('zoom-fit-btn');

    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', () => {
            const img = document.querySelector('#document-view-port img.preview-image');
            if (!img) return;

            if (isFitMode) {
                currentZoom = img.clientWidth / (img.naturalWidth || 1);
                isFitMode = false;
            }
            currentZoom = Math.min(currentZoom * 1.2, 5.0); // max zoom 5x
            img.style.maxWidth = 'none';
            img.style.maxHeight = 'none';
            img.style.width = (img.naturalWidth * currentZoom) + 'px';
            img.style.height = (img.naturalHeight * currentZoom) + 'px';
        });
    }

    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', () => {
            const img = document.querySelector('#document-view-port img.preview-image');
            if (!img) return;

            if (isFitMode) {
                currentZoom = img.clientWidth / (img.naturalWidth || 1);
                isFitMode = false;
            }
            currentZoom = Math.max(currentZoom / 1.2, 0.1); // min zoom 0.1x
            img.style.maxWidth = 'none';
            img.style.maxHeight = 'none';
            img.style.width = (img.naturalWidth * currentZoom) + 'px';
            img.style.height = (img.naturalHeight * currentZoom) + 'px';
        });
    }

    if (zoomResetBtn) {
        zoomResetBtn.addEventListener('click', () => {
            const img = document.querySelector('#document-view-port img.preview-image');
            if (!img) return;

            isFitMode = false;
            currentZoom = 1.0;
            img.style.maxWidth = 'none';
            img.style.maxHeight = 'none';
            img.style.width = img.naturalWidth + 'px';
            img.style.height = img.naturalHeight + 'px';
        });
    }

    if (zoomFitBtn) {
        zoomFitBtn.addEventListener('click', () => {
            const img = document.querySelector('#document-view-port img.preview-image');
            if (!img) return;

            isFitMode = true;
            currentZoom = 1.0;
            img.style.maxWidth = '100%';
            img.style.maxHeight = '100%';
            img.style.width = 'auto';
            img.style.height = 'auto';
        });
    }
}

/**
 * Setup LaTeX viewer utility control event listeners. Bind this once on page load.
 */
export function setupViewerControls() {
    const selectAllBtn = document.getElementById('select-all-btn');
    const wordWrapToggle = document.getElementById('word-wrap-toggle');
    const viewerContainer = document.getElementById('latex-viewer-container');

    if (wordWrapToggle && viewerContainer) {
        wordWrapToggle.addEventListener('click', () => {
            const isWrapped = viewerContainer.classList.toggle('word-wrap');
            wordWrapToggle.classList.toggle('btn-primary', isWrapped);
            wordWrapToggle.classList.toggle('btn-secondary', !isWrapped);
        });
    }

    if (selectAllBtn && viewerContainer) {
        selectAllBtn.addEventListener('click', () => {
            // Select all code content inside the viewer
            const range = document.createRange();
            range.selectNodeContents(viewerContainer);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
        });
    }
}
