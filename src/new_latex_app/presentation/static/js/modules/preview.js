/**
 * Module responsible for rendering uploaded documents and LaTeX/diagram assets.
 */

import { formatBytes } from './utils.js';

/**
 * Render the uploaded file inside the workspace preview viewport.
 * - Images: displayed via Object URL (fully offline).
 * - PDFs: a styled metadata card with filename, size, and a PDF icon.
 *   The browser's built-in PDF viewer is embedded as an iframe below the
 *   metadata card as a graceful enhancement.
 * @param {File} file
 * @param {HTMLElement} viewPortElement
 */
export function renderInputPreview(file, viewPortElement) {
    if (!file || !viewPortElement) return;

    // Clean up any existing Object URLs from previous previews
    _revokeExistingObjectUrls(viewPortElement);
    viewPortElement.innerHTML = '';

    const fileUrl = URL.createObjectURL(file);

    if (file.type === 'application/pdf') {
        _renderPdfPreview(file, fileUrl, viewPortElement);
    } else if (file.type.startsWith('image/')) {
        _renderImagePreview(fileUrl, file.name, viewPortElement);
    } else {
        const errorSpan = document.createElement('span');
        errorSpan.className = 'placeholder-text';
        errorSpan.textContent = 'Preview not supported for this file format.';
        viewPortElement.appendChild(errorSpan);
    }
}

/**
 * Render an image file preview.
 * @param {string} objectUrl
 * @param {string} altText
 * @param {HTMLElement} container
 */
function _renderImagePreview(objectUrl, altText, container) {
    const img = document.createElement('img');
    img.src = objectUrl;
    img.alt = altText;
    img.className = 'preview-image';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '100%';
    img.style.objectFit = 'contain';
    img.dataset.objectUrl = objectUrl;
    container.appendChild(img);
}

/**
 * Render a PDF metadata card with embedded iframe preview.
 * @param {File} file
 * @param {string} objectUrl
 * @param {HTMLElement} container
 */
function _renderPdfPreview(file, objectUrl, container) {
    // Metadata card
    const metaCard = document.createElement('div');
    metaCard.className = 'pdf-preview-info';

    const icon = document.createElement('span');
    icon.className = 'pdf-icon';
    icon.textContent = '📕';
    icon.setAttribute('aria-hidden', 'true');

    const details = document.createElement('div');
    details.className = 'pdf-details';

    const nameEl = document.createElement('span');
    nameEl.className = 'pdf-name';
    nameEl.textContent = file.name;

    const sizeEl = document.createElement('span');
    sizeEl.className = 'pdf-size';
    sizeEl.textContent = formatBytes(file.size);

    const badge = document.createElement('span');
    badge.className = 'file-type-badge';
    badge.textContent = 'PDF';

    details.appendChild(nameEl);
    details.appendChild(sizeEl);

    metaCard.appendChild(icon);
    metaCard.appendChild(details);
    metaCard.appendChild(badge);

    container.appendChild(metaCard);

    // Embedded iframe for browser-native PDF rendering (graceful enhancement)
    const iframe = document.createElement('iframe');
    iframe.src = objectUrl;
    iframe.className = 'pdf-iframe';
    iframe.title = `Preview of ${file.name}`;
    iframe.dataset.objectUrl = objectUrl;
    container.appendChild(iframe);
}

/**
 * Revoke any Object URLs stored in the current preview container to free memory.
 * @param {HTMLElement} container
 */
function _revokeExistingObjectUrls(container) {
    const elements = container.querySelectorAll('[data-object-url]');
    elements.forEach(el => {
        try { URL.revokeObjectURL(el.dataset.objectUrl); } catch (_e) { /* ignore */ }
    });
}

/**
 * Clean up all Object URLs from a container. Intended to be called on file clear.
 * @param {HTMLElement} container
 */
export function cleanupPreviewUrls(container) {
    if (!container) return;
    _revokeExistingObjectUrls(container);
}

/**
 * Render diagram asset thumbnails in the assets grid.
 * @param {string} sessionId
 * @param {Array<string>} assetNames
 * @param {HTMLElement} containerElement
 */
export function renderDiagramAssets(sessionId, assetNames, containerElement) {
    if (!containerElement) return;
    containerElement.innerHTML = '';

    if (!assetNames || assetNames.length === 0) {
        containerElement.innerHTML = '<span class="placeholder-text">No diagrams detected.</span>';
        return;
    }

    assetNames.forEach(name => {
        const card = document.createElement('div');
        card.className = 'asset-card';
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-label', `View diagram ${name}`);

        const img = document.createElement('img');
        img.className = 'asset-img';
        img.alt = name;
        img.loading = 'lazy'; // Lazy loading
        const assetUrl = `/preview/${encodeURIComponent(sessionId)}/assets/${encodeURIComponent(name)}`;
        img.src = assetUrl;

        const nameSpan = document.createElement('span');
        nameSpan.className = 'asset-name';
        nameSpan.textContent = name;

        card.appendChild(img);
        card.appendChild(nameSpan);

        // Click to enlarge binding
        const triggerOpen = () => openDiagramLightbox(assetUrl, name);
        card.addEventListener('click', triggerOpen);
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                triggerOpen();
            }
        });

        containerElement.appendChild(card);
    });
}

/**
 * Render the generated LaTeX in a read-only, monospace line-by-line viewer.
 * Text content is set securely to prevent markup injection.
 * Optimize DOM size for large documents.
 * @param {string} latex
 * @param {HTMLElement} containerElement
 */
export function renderLatexViewer(latex, containerElement) {
    if (!containerElement) return;
    containerElement.innerHTML = '';

    if (!latex) {
        containerElement.innerHTML = '<div class="latex-placeholder">No LaTeX code generated.</div>';
        return;
    }

    const lines = latex.split('\n');
    
    // Performance optimization for extremely large LaTeX outputs (> 1500 lines)
    // to avoid creating too many DOM nodes
    if (lines.length > 1500) {
        const pre = document.createElement('pre');
        pre.style.margin = '0';
        pre.style.padding = '0 var(--spacing-md)';
        const code = document.createElement('code');
        code.id = 'latex-code-display-fallback';
        code.textContent = latex;
        pre.appendChild(code);
        containerElement.appendChild(pre);
        return;
    }

    const fragment = document.createDocumentFragment();

    for (let i = 0; i < lines.length; i++) {
        const lineRow = document.createElement('div');
        lineRow.className = 'latex-line';

        const lineNum = document.createElement('span');
        lineNum.className = 'line-number';
        lineNum.textContent = i + 1;

        const lineContent = document.createElement('span');
        lineContent.className = 'line-content';
        lineContent.textContent = lines[i] || ' '; // Keep space to preserve visual line height

        lineRow.appendChild(lineNum);
        lineRow.appendChild(lineContent);
        fragment.appendChild(lineRow);
    }

    containerElement.appendChild(fragment);
}

/**
 * Display the diagram lightbox overlay.
 * @param {string} src
 * @param {string} alt
 */
export function openDiagramLightbox(src, alt) {
    const lightbox = document.getElementById('diagram-lightbox');
    const img = document.getElementById('lightbox-img');
    if (!lightbox || !img) return;

    img.src = src;
    img.alt = alt || 'Enlarged diagram';
    
    lightbox.classList.add('active');
    lightbox.setAttribute('aria-hidden', 'false');
}

/**
 * Hide the diagram lightbox overlay.
 */
export function closeDiagramLightbox() {
    const lightbox = document.getElementById('diagram-lightbox');
    const img = document.getElementById('lightbox-img');
    if (!lightbox) return;

    lightbox.classList.remove('active');
    lightbox.setAttribute('aria-hidden', 'true');
    if (img) img.src = '';
}

// Close lightbox on Escape key globally
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDiagramLightbox();
    }
});

/**
 * Render structural summary/outline of the generated LaTeX.
 * @param {string} latex
 * @param {HTMLElement} structureElement
 */
export function renderStructurePreview(latex, structureElement) {
    if (!structureElement) return;
    structureElement.innerHTML = '';

    if (!latex) {
        structureElement.innerHTML = '<span class="placeholder-text">A structural outline will be shown here.</span>';
        return;
    }

    // A simple regex parser to extract document hierarchies (\section, \subsection, \begin{...})
    const lines = latex.split('\n');
    let hasItems = false;

    lines.forEach(line => {
        const sectionMatch = line.match(/\\(section|subsection|subsubsection)\*?\{(.*?)\}/);
        const beginMatch = line.match(/\\begin\{(document|figure|table|equation|chemistry)\}/);

        if (sectionMatch) {
            hasItems = true;
            const level = sectionMatch[1];
            const title = sectionMatch[2];
            const div = document.createElement('div');
            div.className = `structure-item structure-${level}`;
            div.style.paddingLeft = level === 'section' ? '0px' : level === 'subsection' ? '12px' : '24px';
            div.innerHTML = `<strong>${level.toUpperCase()}:</strong> ${title}`;
            structureElement.appendChild(div);
        } else if (beginMatch) {
            hasItems = true;
            const block = beginMatch[1];
            const div = document.createElement('div');
            div.className = 'structure-item structure-block';
            div.style.paddingLeft = '8px';
            div.style.color = 'var(--text-secondary)';
            div.innerHTML = `📦 Started <code>${block}</code> block`;
            structureElement.appendChild(div);
        }
    });

    if (!hasItems) {
        structureElement.innerHTML = '<span class="placeholder-text">Simple document structure parsed. No headers found.</span>';
    }
}

/**
 * Render LaTeX body into the math preview container using MathJax when available.
 * - Inserts the raw `latexBody` as text into `#mathjax-preview-container`.
 * - Calls `MathJax.typesetPromise([container])` if MathJax is present.
 * - If MathJax is not present, the raw text remains visible.
 * @param {string} latexBody
 */
export function renderMathJaxPreview(latexBody) {
    const container = document.getElementById('mathjax-preview-container');
    if (!container) return;

    // Clear previous contents
    container.innerHTML = '';

    // Insert body as text to avoid HTML injection; MathJax will scan text nodes
    const textHolder = document.createElement('div');
    textHolder.textContent = latexBody || '';
    container.appendChild(textHolder);

    // If MathJax is available and provides typesetPromise, typeset this container
    try {
        if (typeof MathJax !== 'undefined' && MathJax && typeof MathJax.typesetPromise === 'function') {
            // typesetPromise returns a Promise; callers may await if they later invoke this function
            MathJax.typesetPromise([container]).catch(() => {
                // Swallow errors to avoid breaking the UI; keep raw content visible
            });
        }
    } catch (_e) {
        // If any unexpected error, leave the raw content in place
    }
}
