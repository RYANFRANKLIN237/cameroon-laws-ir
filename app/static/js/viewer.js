pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

const params = new URLSearchParams(window.location.search);
const source = params.get("source") || "";
const initialPage = Math.max(1, parseInt(params.get("page") || "1", 10) || 1);
const quote = (params.get("q") || "").trim();
const pdfUrl = source ? `/view-pdf/${encodeURIComponent(source)}` : "";

const el = {
    title: document.getElementById("docTitle"),
    pageInfo: document.getElementById("pageInfo"),
    status: document.getElementById("status"),
    prev: document.getElementById("prevPage"),
    next: document.getElementById("nextPage"),
    findAgain: document.getElementById("findAgain"),
    openRaw: document.getElementById("openRaw"),
    pdfCanvas: document.getElementById("pdfCanvas"),
    highlightCanvas: document.getElementById("highlightCanvas"),
    container: document.getElementById("viewerContainer"),
};

let pdfDoc = null;
let currentPage = initialPage;
let rendering = false;

function setStatus(message) {
    el.status.textContent = message || "";
}

function normalize(text) {
    return (text || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function clearHighlights() {
    const context = el.highlightCanvas.getContext("2d");
    context.clearRect(0, 0, el.highlightCanvas.width, el.highlightCanvas.height);
}

function drawHighlights(rects, viewport) {
    const context = el.highlightCanvas.getContext("2d");
    const secondaryColor = getComputedStyle(document.documentElement)
        .getPropertyValue("--secondary")
        .trim();

    clearHighlights();
    context.fillStyle = secondaryColor;
    context.globalAlpha = 0.45;

    for (const [x, y, width, height] of rects) {
        const rectangle = viewport.convertToViewportRectangle([
            x,
            y,
            x + width,
            y + height,
        ]);
        const left = Math.min(rectangle[0], rectangle[2]);
        const top = Math.min(rectangle[1], rectangle[3]);
        const highlightWidth = Math.abs(rectangle[2] - rectangle[0]);
        const highlightHeight = Math.abs(rectangle[3] - rectangle[1]);
        context.fillRect(left, top, highlightWidth, highlightHeight);
    }

    context.globalAlpha = 1;
}

async function findQuoteRects(page, searchQuote) {
    if (!searchQuote) return [];

    const textContent = await page.getTextContent();
    const items = textContent.items.filter(
        (item) => typeof item.str === "string" && item.str.length,
    );
    if (!items.length) return [];

    let haystack = "";
    const charToItem = [];

    for (let itemIndex = 0; itemIndex < items.length; itemIndex += 1) {
        const piece = items[itemIndex].str;
        for (let charIndex = 0; charIndex < piece.length; charIndex += 1) {
            haystack += piece[charIndex].toLowerCase();
            charToItem.push(itemIndex);
        }
        if (itemIndex < items.length - 1) {
            haystack += " ";
            charToItem.push(itemIndex);
        }
    }

    const compactParts = [];
    const compactToHaystack = [];

    for (let index = 0; index < haystack.length; index += 1) {
        const character = haystack[index];
        if (/\s/.test(character)) {
            if (
                compactParts.length &&
                compactParts[compactParts.length - 1] !== " "
            ) {
                compactParts.push(" ");
                compactToHaystack.push(index);
            }
        } else {
            compactParts.push(character);
            compactToHaystack.push(index);
        }
    }

    const compact = compactParts.join("").trim();
    const base = normalize(searchQuote);
    const needles = [base];

    for (const length of [80, 60, 40, 24]) {
        if (base.length > length) needles.push(base.slice(0, length));
    }

    let matchStart = -1;
    let matchLength = 0;

    for (const needle of needles) {
        if (needle.length < 8) continue;
        const index = compact.indexOf(needle);
        if (index !== -1) {
            matchStart = index;
            matchLength = needle.length;
            break;
        }
    }

    if (matchStart < 0) return [];

    const startHaystack = compactToHaystack[matchStart];
    const endHaystack =
        compactToHaystack[
            Math.min(
                matchStart + matchLength - 1,
                compactToHaystack.length - 1,
            )
        ];

    if (startHaystack == null || endHaystack == null) return [];

    const itemIndexes = new Set();
    for (let index = startHaystack; index <= endHaystack; index += 1) {
        itemIndexes.add(charToItem[index]);
    }

    const rects = [];
    for (const itemIndex of itemIndexes) {
        const item = items[itemIndex];
        const transform = item.transform;
        const fontHeight = Math.hypot(transform[2], transform[3]) || 10;
        const width =
            item.width || item.str.length * fontHeight * 0.5;
        rects.push([transform[4], transform[5], width, fontHeight]);
    }

    return rects;
}

async function renderPage(pageNumber) {
    if (!pdfDoc || rendering) return;
    rendering = true;
    currentPage = pageNumber;

    try {
        const page = await pdfDoc.getPage(pageNumber);
        const unscaled = page.getViewport({ scale: 1 });
        const fitWidth = Math.max(320, el.container.clientWidth - 32);
        const scale = Math.min(1.75, fitWidth / unscaled.width);
        const viewport = page.getViewport({ scale });

        el.pdfCanvas.width = viewport.width;
        el.pdfCanvas.height = viewport.height;
        el.highlightCanvas.width = viewport.width;
        el.highlightCanvas.height = viewport.height;

        await page.render({
            canvasContext: el.pdfCanvas.getContext("2d"),
            viewport,
        }).promise;

        el.pageInfo.textContent = `Page ${pageNumber} / ${pdfDoc.numPages}`;
        el.prev.disabled = pageNumber <= 1;
        el.next.disabled = pageNumber >= pdfDoc.numPages;

        const rects = await findQuoteRects(page, quote);
        if (rects.length) {
            drawHighlights(rects, viewport);
            setStatus(`Highlighted ${rects.length} text region(s)`);
        } else if (quote) {
            clearHighlights();
            setStatus("Page opened — quote not found on this page");
        } else {
            clearHighlights();
            setStatus("");
        }
    } catch (error) {
        console.error(error);
        setStatus("Failed to render page");
    } finally {
        rendering = false;
    }
}

el.prev.addEventListener("click", () => {
    if (currentPage > 1) renderPage(currentPage - 1);
});

el.next.addEventListener("click", () => {
    if (pdfDoc && currentPage < pdfDoc.numPages) {
        renderPage(currentPage + 1);
    }
});

el.findAgain.addEventListener("click", () => renderPage(currentPage));

async function init() {
    if (!source || !pdfUrl) {
        el.container.innerHTML =
            '<div class="error">Missing <code>source</code> query parameter.</div>';
        return;
    }

    el.title.textContent = source;
    el.openRaw.href = pdfUrl;
    setStatus("Loading PDF…");

    try {
        pdfDoc = await pdfjsLib.getDocument(pdfUrl).promise;
        const pageNumber = Math.min(initialPage, pdfDoc.numPages);
        await renderPage(pageNumber);
    } catch (error) {
        console.error(error);
        const message = document.createElement("div");
        message.className = "error";
        message.textContent = `Could not load PDF for “${source}”.`;
        el.container.replaceChildren(message);
    }
}

init();
