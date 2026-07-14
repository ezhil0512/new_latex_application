/**
 * Main Application Orchestrator
 */

import { uploadDocument, getPreviewData } from './modules/api.js';
import {
    initDragAndDrop,
    updatePipelineStatus,
    toggleActionControls,
    showError,
    clearError,
    setDropZoneError,
    showUploadStatus,
    hideUploadStatus,
    showProcessingCard,
    hideProcessingCard,
    updateProcessingStatus,
    updateProcessingTimer,
    initZoomControls,
    setupZoomListeners,
    setupViewerControls,
} from './modules/ui.js';
import {
    renderInputPreview,
    renderDiagramAssets,
    renderStructurePreview,
    cleanupPreviewUrls,
    renderLatexViewer,
    closeDiagramLightbox,
} from './modules/preview.js';
import { formatBytes } from './modules/utils.js';
import {
    prepareTexDownload,
    handleTexDownloadClick,
    downloadZipExport,
    copyLatexToClipboard,
    revokeExportUrls
} from './modules/export.js';

// Core Application State
const state = {
    selectedFile: null,
    sessionId: null,
    latexCode: '',
    latexBody: '',
    assets: [],
    status: 'idle', // 'idle' | 'processing' | 'ready'
    /** @type {AbortController|null} */
    abortController: null,
    timerInterval: null,
    timerSeconds: 0,
};

// Supported formats and size limit (mirrors backend configuration)
const SUPPORTED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

// DOM References
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const docPreviewCard = document.getElementById('doc-preview-card');
const diagramPreviewCard = document.getElementById('diagram-preview-card');
const previewFilename = document.getElementById('preview-filename');
const previewFilesize = document.getElementById('preview-filesize');
const documentViewPort = document.getElementById('document-view-port');
const clearFileBtn = document.getElementById('clear-file-btn');
const actionPanel = document.getElementById('action-panel');
const generateLatexBtn = document.getElementById('generate-latex-btn');
const copyLatexBtn = document.getElementById('copy-latex-btn');
const downloadTexBtn = document.getElementById('download-tex-btn');
const downloadZipBtn = document.getElementById('download-zip-btn');
const latexCodeOutput = document.getElementById('latex-code-output');
const latexViewerContainer = document.getElementById('latex-viewer-container');
const assetsList = document.getElementById('assets-list');
const structurePreview = document.getElementById('structure-preview');
const errorDismissBtn = document.getElementById('error-dismiss-btn');
const cancelProcessingBtn = document.getElementById('cancel-processing-btn');
const diagramLightbox = document.getElementById('diagram-lightbox');
const lightboxCloseBtn = document.getElementById('lightbox-close-btn');

/* ------------------------------------------------------------------ */
/*  Abort Helpers                                                      */
/* ------------------------------------------------------------------ */

/**
 * Cancel any in-flight API request tied to the current AbortController.
 */
function cancelInFlightRequest() {
    if (state.abortController) {
        state.abortController.abort();
        state.abortController = null;
    }
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
    state.timerSeconds = 0;
    updateProcessingTimer(0);
}

/* ------------------------------------------------------------------ */
/*  File Selection                                                     */
/* ------------------------------------------------------------------ */

/**
 * Validate a file's extension against supported formats.
 * @param {string} filename
 * @returns {boolean}
 */
function isValidExtension(filename) {
    const ext = '.' + filename.split('.').pop().toLowerCase();
    return SUPPORTED_EXTENSIONS.includes(ext);
}

/**
 * Handle new file selection (via browse dialog or drag-and-drop).
 * @param {File} file
 */
function handleFileSelection(file) {
    if (!file) return;

    // Clear any previous errors and cancel any in-flight requests
    clearError();
    setDropZoneError(false);
    cancelInFlightRequest();

    // Validate file extension
    if (!isValidExtension(file.name)) {
        showError('Unsupported file format. Please upload a PDF, PNG, JPG, or JPEG file.');
        setDropZoneError(true);
        return;
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
        showError(`File size (${formatBytes(file.size)}) exceeds the 50 MB limit.`);
        setDropZoneError(true);
        return;
    }

    // Reset state for new file
    state.selectedFile = file;
    state.sessionId = null;
    state.latexCode = '';
    state.latexBody = '';
    state.assets = [];
    state.status = 'idle';

    // Update UI elements
    previewFilename.textContent = file.name;
    previewFilesize.textContent = formatBytes(file.size);
    renderInputPreview(file, documentViewPort);

    // Swap views
    dropZone.classList.add('hidden');
    docPreviewCard.classList.remove('hidden');
    diagramPreviewCard.classList.add('hidden');
    actionPanel.classList.remove('hidden');

    // Initialize zoom toolbar
    initZoomControls(file);

    // Reset output panels
    latexCodeOutput.value = '';
    if (latexViewerContainer) {
        latexViewerContainer.innerHTML = '<div class="latex-placeholder">Your generated LaTeX code will appear here...</div>';
    }
    assetsList.innerHTML = '<span class="placeholder-text">No diagrams detected.</span>';
    structurePreview.innerHTML = '<span class="placeholder-text">A structural outline will be shown here.</span>';

    // Reset buttons and hide status
    toggleActionControls(false);
    hideUploadStatus();
}

/* ------------------------------------------------------------------ */
/*  Clear Selection                                                    */
/* ------------------------------------------------------------------ */

/**
 * Reset layout back to empty upload state.
 */
function clearSelection() {
    // Cancel any in-flight request
    cancelInFlightRequest();

    // Close lightbox if open
    closeDiagramLightbox();

    state.selectedFile = null;
    state.sessionId = null;
    state.latexCode = '';
    state.latexBody = '';
    state.assets = [];
    state.status = 'idle';

    fileInput.value = '';

    // Clean up Object URLs to free memory
    cleanupPreviewUrls(documentViewPort);
    revokeExportUrls();
    documentViewPort.innerHTML = '<span class="placeholder-text">Preview loading...</span>';

    // Hide panels
    docPreviewCard.classList.add('hidden');
    diagramPreviewCard.classList.add('hidden');
    actionPanel.classList.add('hidden');
    hideProcessingCard();
    dropZone.classList.remove('hidden');

    // Reset zoom controls
    initZoomControls(null);

    // Reset outputs
    latexCodeOutput.value = '';
    if (latexViewerContainer) {
        latexViewerContainer.innerHTML = '<div class="latex-placeholder">Your generated LaTeX code will appear here...</div>';
    }
    const wordWrapToggle = document.getElementById('word-wrap-toggle');
    if (wordWrapToggle && latexViewerContainer) {
        latexViewerContainer.classList.remove('word-wrap');
        wordWrapToggle.classList.remove('btn-primary');
        wordWrapToggle.classList.add('btn-secondary');
    }

    assetsList.innerHTML = '<span class="placeholder-text">No diagrams detected.</span>';
    structurePreview.innerHTML = '<span class="placeholder-text">A structural outline will be shown here.</span>';

    toggleActionControls(false);
    hideUploadStatus();
    clearError();
    setDropZoneError(false);
    updatePipelineStatus('idle');
}

/* ------------------------------------------------------------------ */
/*  LaTeX Generation Pipeline                                          */
/* ------------------------------------------------------------------ */

/**
 * Trigger the compilation pipeline by uploading to backend and polling result.
 */
async function startLatexGeneration() {
    if (!state.selectedFile) return;

    // Prevent duplicate submissions
    if (state.status === 'processing') return;

    // Cancel any previous in-flight request
    cancelInFlightRequest();

    // Create a new AbortController for this request lifecycle
    state.abortController = new AbortController();
    const { signal } = state.abortController;

    state.status = 'processing';
    clearError();
    updatePipelineStatus('busy');
    toggleActionControls(true); // Disables Generate button + shows spinner

    // Hide input preview and action buttons, show processing status screen
    docPreviewCard.classList.add('hidden');
    actionPanel.classList.add('hidden');
    showProcessingCard();
    updateProcessingStatus('Uploading document…');

    // Start stopwatch timer
    state.timerSeconds = 0;
    updateProcessingTimer(0);
    state.timerInterval = setInterval(() => {
        state.timerSeconds++;
        updateProcessingTimer(state.timerSeconds);
    }, 1000);

    try {
        // Step 1: Upload and trigger conversion
        const uploadResult = await uploadDocument(state.selectedFile, { signal });

        // If the request was aborted, silently exit
        if (uploadResult.aborted) return;

        if (uploadResult.error) {
            showError(uploadResult.error);
            state.status = 'idle';
            return;
        }

        state.sessionId = uploadResult.session_id;
        updateProcessingStatus('Running processing pipeline…');

        // Step 2: Fetch generation previews
        const previewResult = await getPreviewData(state.sessionId, { signal });

        // If the request was aborted, silently exit
        if (previewResult.aborted) return;

        if (previewResult.error) {
            showError(previewResult.error);
            state.status = 'idle';
            return;
        }

        updateProcessingStatus('Retrieving preview files…');

        state.latexCode = previewResult.latex_preview || '';
        // Preserve the full LaTeX document body for later MathJax rendering
        state.latexBody = previewResult.latex_body || '';
        state.assets = previewResult.asset_names || [];
        state.status = 'ready';

        // Update output containers
        latexCodeOutput.value = state.latexCode;
        renderLatexViewer(state.latexCode, latexViewerContainer);
        renderDiagramAssets(state.sessionId, state.assets, assetsList);
        renderStructurePreview(state.latexCode, structurePreview);

        // Prepare the .tex download URL and properties (anchor-based)
        if (downloadTexBtn && state.latexCode) {
            prepareTexDownload(downloadTexBtn, state.latexCode, state.selectedFile.name);
        }

    } catch (error) {
        // Unexpected errors (should not normally happen since api.js catches)
        if (error.name !== 'AbortError') {
            console.error('Processing failed:', error);
            showError(`Unexpected error: ${error.message || error}`);
            state.status = 'idle';
        }
    } finally {
        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
        hideProcessingCard();
        state.abortController = null;
        updatePipelineStatus('idle');
        toggleActionControls(false); // Re-enables Generate button
        
        // Restore doc preview card and actions only if we still have a file selected
        if (state.selectedFile) {
            docPreviewCard.classList.remove('hidden');
            actionPanel.classList.remove('hidden');
            if (state.status === 'ready') {
                diagramPreviewCard.classList.remove('hidden');
            }
            initZoomControls(state.selectedFile);
        }
    }
}

/* ------------------------------------------------------------------ */
/*  Event Binding                                                      */
/* ------------------------------------------------------------------ */

document.addEventListener('DOMContentLoaded', () => {
    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    // Drag and Drop
    initDragAndDrop(dropZone, handleFileSelection);

    // Buttons
    clearFileBtn.addEventListener('click', clearSelection);
    generateLatexBtn.addEventListener('click', startLatexGeneration);

    // Error dismiss
    if (errorDismissBtn) {
        errorDismissBtn.addEventListener('click', () => {
            clearError();
            setDropZoneError(false);
        });
    }

    // Cancel processing button
    if (cancelProcessingBtn) {
        cancelProcessingBtn.addEventListener('click', clearSelection);
    }

    // Initialize Phase 4 custom zoom and monospace viewer controls
    setupZoomListeners();
    setupViewerControls();

    // Lightbox close controls
    if (lightboxCloseBtn) {
        lightboxCloseBtn.addEventListener('click', closeDiagramLightbox);
    }
    if (diagramLightbox) {
        diagramLightbox.addEventListener('click', (e) => {
            // Close lightbox if backdrop is clicked
            if (e.target === diagramLightbox) {
                closeDiagramLightbox();
            }
        });
    }

    // Copy to clipboard
    copyLatexBtn.addEventListener('click', () => {
        if (!state.latexCode) return;
        copyLatexToClipboard(state.latexCode, copyLatexBtn);
    });

    // Download .TEX success feedback
    downloadTexBtn.addEventListener('click', () => {
        handleTexDownloadClick(downloadTexBtn);
    });

    // Programmatic .ZIP download via fetch with error validation
    downloadZipBtn.addEventListener('click', () => {
        if (!state.sessionId) return;
        downloadZipExport(state.sessionId, downloadZipBtn);
    });
});
