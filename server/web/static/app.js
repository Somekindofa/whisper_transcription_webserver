const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const queueList = document.getElementById("queueList");
const transcribeButton = document.getElementById("transcribeButton");
// Language & speakers are now per-queue-item; default values used on upload
const DEFAULT_LANGUAGE = 'fr';
const DEFAULT_SPEAKERS = 1;

let pollingInterval = null;
const activeWebSockets = {}; // Track WebSocket connections by file_id
const progressState = {}; // Track progress for each file_id
// Per-file pollers used as a fallback when WebSocket handshake fails
const perFilePollers = {}; // file_id -> intervalId
// Track failed WS attempts per file so we avoid retry storms
const wsFailureCount = {}; // file_id -> number
const MAX_WS_RETRIES = 2; // after this, rely on polling fallback

function formatTime(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

function renderQueue(items) {
  queueList.innerHTML = "";
  
  if (items.length === 0) {
    queueList.innerHTML = "<p>No files in queue</p>";
    return;
  }
  
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = `queue-card status-${item.status}`;
    card.id = `card-${item.id}`;
    
    const spinner = (item.status === "active" || item.status === "uploading") 
      ? '<span class="spinner"></span>' 
      : "";
    
    const preview = item.preview 
      ? `<div class="queue-card__preview">${item.preview}</div>` 
      : "";
    
    const errorMsg = item.error_message 
      ? `<div class="queue-card__error">Error: ${item.error_message}</div>` 
      : "";
    
    const downloadBtn = item.status === "complete" && item.preview
      ? `<button data-download="${item.id}">Download</button>`
      : "";
    
    // Show progress bar for active/uploading items (also show for queued
    // items that have an explicit `progressState` entry so the UI can
    // display immediate feedback right after the user clicks "Transcribe").
    const progress = progressState[item.id] || 0;
    const phase = (progressState[`phase_${item.id}`] || "");
    const phaseDisplay = phase ? `<div class="queue-card__phase">${phase}</div>` : "";

    const showProgressBar = item.status === "active" || item.status === "uploading" || (item.status === "queued" && progressState[item.id] !== undefined);

    const progressBar = showProgressBar
      ? `<div class="queue-card__progress-container">
           <div class="queue-card__progress-bar" style="width: ${progress}%"></div>
           <span class="queue-card__progress-text">${Math.round(progress)}%</span>
         </div>
         ${phaseDisplay}`
      : "";

    const elapsedDisplay = (item.status === 'complete' && item.processing_seconds)
      ? `<div class="queue-card__elapsed">⏱️ ${formatTime(item.processing_seconds)}</div>`
      : "";
    
    card.innerHTML = `
      <div class="queue-card__header">
        <strong>${item.original_name}</strong>
        <span>${(item.size_bytes / 1024 / 1024).toFixed(2)} MB ${spinner}</span>
      </div>
      <div class="queue-card__meta">
        <label style="display:inline-block; margin-right:0.75rem;">
          Language
          <select class="per-item-language" data-file-id="${item.id}">
            <option value="en" ${item.language === 'en' ? 'selected' : ''}>English</option>
            <option value="fr" ${item.language === 'fr' ? 'selected' : ''}>French</option>
            <option value="es" ${item.language === 'es' ? 'selected' : ''}>Spanish</option>
            <option value="de" ${item.language === 'de' ? 'selected' : ''}>German</option>
            <option value="it" ${item.language === 'it' ? 'selected' : ''}>Italian</option>
            <option value="pt" ${item.language === 'pt' ? 'selected' : ''}>Portuguese</option>
            <option value="ja" ${item.language === 'ja' ? 'selected' : ''}>Japanese</option>
            <option value="ko" ${item.language === 'ko' ? 'selected' : ''}>Korean</option>
            <option value="zh" ${item.language === 'zh' ? 'selected' : ''}>Chinese</option>
          </select>
        </label>
        <label style="display:inline-block;">
          Speakers
          <input type="number" class="per-item-speakers" data-file-id="${item.id}" min="1" max="5" value="${item.speakers}" style="width:4.5rem;" />
        </label>
        <div style="display:inline-block; margin-left:1rem; color:#666;">Status: ${item.status}</div>
        ${item.speakers === 1 ? `<div class="queue-card__note">Speaker count is 1 — this item will be transcribed only (no diarization).</div>` : ''}
      </div>
      ${progressBar}
      ${preview}
      ${elapsedDisplay}
      ${errorMsg}
      <div class="queue-card__actions">
        <button data-remove="${item.id}">Remove</button>
        ${downloadBtn}
      </div>
    `;
    queueList.appendChild(card);

    // Attach per-item option listeners (language/speakers)
    const langEl = card.querySelector('.per-item-language');
    const spkEl = card.querySelector('.per-item-speakers');
    const fileId = item.id;

    if (langEl) {
      langEl.addEventListener('change', async (e) => {
        const value = e.target.value;
        await updateQueueItem(fileId, { language: value });
      });
    }

    if (spkEl) {
      spkEl.addEventListener('change', async (e) => {
        let val = parseInt(e.target.value) || 1;
        if (val < 1) val = 1;
        if (val > 5) val = 5;
        e.target.value = val;
        await updateQueueItem(fileId, { speakers: val });
      });
    }

    // Listen for `progress` CustomEvents on this card so startTranscription
    // (which dispatches that event) immediately updates the DOM without
    // waiting for renderQueue to re-run.
    card.addEventListener('progress', (ev) => {
      const d = ev.detail || {};
      const progressVal = typeof d.progress === 'number' ? d.progress : (progressState[fileId] || 0);
      const phaseText = d.phase || progressState[`phase_${fileId}`] || '';

      // Ensure progressState mirrors the event
      progressState[fileId] = progressVal;
      if (phaseText) progressState[`phase_${fileId}`] = phaseText;

      // Update/create progress bar elements
      let container = card.querySelector('.queue-card__progress-container');
      if (!container) {
        // insert progress container after meta
        const meta = card.querySelector('.queue-card__meta');
        container = document.createElement('div');
        container.className = 'queue-card__progress-container';
        container.innerHTML = `<div class="queue-card__progress-bar" style="width: ${progressVal}%"></div><span class="queue-card__progress-text">${Math.round(progressVal)}%</span>`;
        meta.parentNode.insertBefore(container, meta.nextSibling);
      } else {
        const bar = container.querySelector('.queue-card__progress-bar');
        const txt = container.querySelector('.queue-card__progress-text');
        if (bar) bar.style.width = `${progressVal}%`;
        if (txt) txt.textContent = `${Math.round(progressVal)}%`;
      }

      // Phase
      let phaseDiv = card.querySelector('.queue-card__phase');
      if (phaseText) {
        if (!phaseDiv) {
          phaseDiv = document.createElement('div');
          phaseDiv.className = 'queue-card__phase';
          container.parentNode.insertBefore(phaseDiv, container.nextSibling);
        }
        phaseDiv.textContent = phaseText;
      }
    });

    // Connect WebSocket for active/uploading items. Also connect for
    // queued items when we have a pre-existing progressState entry so the
    // client is already listening when the server starts processing.
    if ((item.status === "active" || item.status === "uploading" || (item.status === 'queued' && progressState[item.id] !== undefined)) && !activeWebSockets[item.id]) {
      connectProgressWebSocket(item.id);
    }
  });
}

async function fetchQueue() {
  try {
    const response = await fetch("/api/queue");
    const items = await response.json();
    renderQueue(items);
    
    // No global polling: UI relies on WebSocket + webhook updates. Keep
    // per-file polling only as a fallback when WS isn't available.
    
    // Clean up WebSocket connections for completed/errored items
    Object.keys(activeWebSockets).forEach(fileId => {
      const item = items.find(i => i.id == fileId);
      if (!item || (item.status !== "active" && item.status !== "uploading")) {
        disconnectProgressWebSocket(parseInt(fileId));
      }
    });
  } catch (error) {
    console.error("Failed to fetch queue:", error);
  }
}

function connectProgressWebSocket(fileId) {
  // Don't hammer the server if WS failed repeatedly for this file — fall
  // back to polling after MAX_WS_RETRIES attempts.
  if ((wsFailureCount[fileId] || 0) >= MAX_WS_RETRIES) {
    if (!perFilePollers[fileId]) startPerFilePolling(fileId);
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // WebSocket endpoint is mounted under the API router on the server.
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/progress/${fileId}`);

  ws.onopen = () => {
    console.info(`WebSocket open for file ${fileId}`);
    // Reset failure counter on successful open
    wsFailureCount[fileId] = 0;

    // If we had a fallback poller running, stop it now that WS is open
    if (perFilePollers[fileId]) {
      stopPerFilePolling(fileId);
    }
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Update progress state
    progressState[data.file_id] = data.progress;

    // Store phase information
    if (data.phase) {
      progressState[`phase_${data.file_id}`] = data.phase;
    }

    // Update progress bar in DOM
    const card = document.getElementById(`card-${data.file_id}`);
    if (card) {
      const progressBar = card.querySelector(".queue-card__progress-bar");
      const progressText = card.querySelector(".queue-card__progress-text");
      const phaseDiv = card.querySelector(".queue-card__phase");

      if (progressBar) {
        progressBar.style.width = `${data.progress}%`;
      }
      if (progressText) {
        progressText.textContent = `${Math.round(data.progress)}%`;
      }

      // Update phase text if present
      if (data.phase && phaseDiv) {
        phaseDiv.textContent = data.phase;
      } else if (data.phase) {
        // Create phase div if it doesn't exist
        const container = card.querySelector(".queue-card__progress-container");
        if (container && !container.querySelector(".queue-card__phase")) {
          const newPhaseDiv = document.createElement("div");
          newPhaseDiv.className = "queue-card__phase";
          newPhaseDiv.textContent = data.phase;
          container.parentNode.insertBefore(newPhaseDiv, container.nextSibling);
        }
      }

      // Dispatch a `progress` CustomEvent on the card so other code can hook into
      if (card) {
        const progressEvent = new CustomEvent('progress', { detail: data });
        card.dispatchEvent(progressEvent);
      }
    }

    // If complete, refresh queue to update status
    if (data.status === "complete" || data.status === "error") {
      setTimeout(fetchQueue, 500);
    }
  };

  ws.onerror = (error) => {
    console.error(`WebSocket error for file ${fileId}:`, error);
    wsFailureCount[fileId] = (wsFailureCount[fileId] || 0) + 1;
    // Fall back to per-file polling if we've reached the retry limit
    if ((wsFailureCount[fileId] || 0) >= MAX_WS_RETRIES) {
      startPerFilePolling(fileId);
    } else {
      // try polling briefly while the connection may recover
      startPerFilePolling(fileId);
    }
  };

  ws.onclose = () => {
    // When WS closes unexpectedly, fall back to polling and allow reconnects
    delete activeWebSockets[fileId];
    wsFailureCount[fileId] = (wsFailureCount[fileId] || 0) + 1;
    if ((wsFailureCount[fileId] || 0) >= MAX_WS_RETRIES) {
      startPerFilePolling(fileId);
    } else {
      // schedule a re-attempt after a short delay
      setTimeout(() => {
        if (!activeWebSockets[fileId]) connectProgressWebSocket(fileId);
      }, 1500);
    }
  };

  activeWebSockets[fileId] = ws;
}

function disconnectProgressWebSocket(fileId) {
  const ws = activeWebSockets[fileId];
  if (ws) {
    try { ws.close(); } catch (e) {}
    delete activeWebSockets[fileId];
  }
  stopPerFilePolling(fileId);
}

// Per-file polling fallback for when WebSocket is unavailable or fails.
function startPerFilePolling(fileId) {
  if (perFilePollers[fileId]) return;
  perFilePollers[fileId] = setInterval(async () => {
    try {
      const resp = await fetch('/api/queue');
      if (!resp.ok) return;
      const items = await resp.json();
      const item = items.find(i => i.id === fileId);
      if (!item) {
        stopPerFilePolling(fileId);
        return;
      }

      // Update progress state from server-side `progress_percent` if present
      if (typeof item.progress_percent === 'number') {
        progressState[fileId] = item.progress_percent;
      }
      if (item.status) {
        progressState[`phase_${fileId}`] = item.status === 'active' ? 'Processing...' : item.status;
      }

      const card = document.getElementById(`card-${fileId}`);
      if (card) {
        const detail = { file_id: fileId, progress: progressState[fileId] || 0, phase: progressState[`phase_${fileId}`] || '' , status: item.status };
        card.dispatchEvent(new CustomEvent('progress', { detail }));
      }

      if (item.status !== 'active' && item.status !== 'uploading' && (item.progress_percent || 0) >= 100) {
        stopPerFilePolling(fileId);
      }
    } catch (e) {
      // ignore transient errors
      console.warn('per-file poll error', e);
    }
  }, 3000);
}

function stopPerFilePolling(fileId) {
  if (perFilePollers[fileId]) {
    clearInterval(perFilePollers[fileId]);
    delete perFilePollers[fileId];
  }
}

// Update language/speakers for a queued item
async function updateQueueItem(fileId, data) {
  try {
    const resp = await fetch(`/api/queue/${fileId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!resp.ok) {
      const err = await resp.json();
      alert(`Failed to update item: ${err.detail || resp.statusText}`);
      return null;
    }

    // Refresh queue to reflect the change (simpler and keeps UI in sync)
    await fetchQueue();
    return await resp.json();
  } catch (error) {
    alert(`Failed to update item: ${error.message}`);
    return null;
  }
}

function startPolling() {
  if (pollingInterval) return;
  // Poll less frequently to reduce background traffic (3s)
  pollingInterval = setInterval(fetchQueue, 3000);
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

async function uploadFiles(files) {
  // Default per-item options: French (fr) and speakers = 1 (transcription-only)
  const language = DEFAULT_LANGUAGE;
  const speakers = DEFAULT_SPEAKERS;

  for (const file of files) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    formData.append("speakers", speakers);
    
    try {
      const response = await fetch("/api/queue", {
        method: "POST",
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        alert(`Failed to upload ${file.name}: ${error.detail}`);
      }
    } catch (error) {
      alert(`Failed to upload ${file.name}: ${error.message}`);
    }
  }
  
  // Refresh queue after upload
  await fetchQueue();
}

async function startTranscription() {
  try {
    transcribeButton.disabled = true;
    transcribeButton.textContent = "Transcribing...";

    // Pre-fetch queued items so we can show an immediate progress bar
    // for those items in the UI (avoid waiting for the server to flip
    // their status to `active`).
    try {
      const qc = await fetch('/api/queue');
      const queuedItems = await qc.json();
      // Mark all non-complete items as 'starting' so the UI displays a
      // progress bar immediately (this ensures the bar appears even if
      // the card hasn't been re-rendered yet).
      const toStart = queuedItems.filter(i => i.status !== 'complete');

      toStart.forEach(i => {
        progressState[i.id] = 0;
        progressState[`phase_${i.id}`] = 'Starting...';

        // If the card exists, dispatch a progress event so the DOM updates
        const card = document.getElementById(`card-${i.id}`);
        if (card) {
          const progressEvent = new CustomEvent('progress', { detail: { file_id: i.id, progress: 0, phase: 'Starting...', status: i.status } });
          card.dispatchEvent(progressEvent);
        }

        // Pre-open WS so client is listening when server starts streaming
        try {
          if (!activeWebSockets[i.id]) {
            connectProgressWebSocket(i.id);
          }
        } catch (wsErr) {
          console.warn('failed to pre-connect websocket for', i.id, wsErr);
        }
      });

      // Re-render queue to ensure any cards that weren't present yet show the
      // newly inserted progress bars immediately.
      await fetchQueue();
    } catch (e) {
      // If the pre-fetch fails (network / server error), fall back to
      // scanning the DOM for queued cards so we still show immediate
      // progress UI without relying on the API reply.
      console.warn('pre-fetch queue failed', e);

      try {
        document.querySelectorAll('.queue-card').forEach(card => {
          const meta = card.querySelector('.queue-card__meta');
          if (!meta) return;
          const txt = meta.textContent || '';
          if (txt.includes('Status: queued')) {
            const idMatch = (card.id || '').match(/card-(\d+)/);
            if (idMatch) {
              const id = parseInt(idMatch[1], 10);
              progressState[id] = 0;
              progressState[`phase_${id}`] = 'Starting...';
              const progressEvent = new CustomEvent('progress', { detail: { file_id: id, progress: 0, phase: 'Starting...', status: 'queued' } });
              card.dispatchEvent(progressEvent);
            }
          }
        });
      } catch (domErr) {
        console.warn('DOM fallback failed', domErr);
      }
    }

    const response = await fetch("/api/transcribe", {
      method: "POST",
    });

    const result = await response.json();

    if (result.count > 0) {
      // Fetch immediately to capture the "active" state — rely on WebSocket
      // (webhook -> server -> WS) for subsequent live updates instead of
      // global polling.
      await fetchQueue();
    } else {
      alert("No files in queue to transcribe");
    }
  } catch (error) {
    alert(`Failed to start transcription: ${error.message}`);
  } finally {
    transcribeButton.disabled = false;
    transcribeButton.textContent = "Transcribe";
  }
}

async function removeItem(fileId) {
  try {
    const response = await fetch(`/api/queue/${fileId}`, {
      method: "DELETE",
    });
    
    if (response.ok) {
      await fetchQueue();
    } else {
      alert("Failed to remove item");
    }
  } catch (error) {
    alert(`Failed to remove item: ${error.message}`);
  }
}

async function downloadTranscript(fileId) {
  try {
    const response = await fetch(`/api/download/${fileId}`);
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      // Get filename from Content-Disposition header
      const disposition = response.headers.get("Content-Disposition");
      const filename = disposition 
        ? disposition.split("filename=")[1].replace(/"/g, "")
        : `transcript_${fileId}.txt`;
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } else {
      alert("Failed to download transcript");
    }
  } catch (error) {
    alert(`Failed to download: ${error.message}`);
  }
}

// Event listeners
dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("is-active");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("is-active");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-active");
  const files = event.dataTransfer.files;
  uploadFiles(files);
});

dropzone.addEventListener("click", () => {
  fileInput.click();
});

fileInput.addEventListener("click", (event) => {
  event.stopPropagation(); // Prevent click from bubbling to dropzone
});

fileInput.addEventListener("change", (event) => {
  const files = event.target.files;
  uploadFiles(files);
  fileInput.value = ""; // Reset input
});

transcribeButton.addEventListener("click", () => {
  startTranscription();
});

queueList.addEventListener("click", (event) => {
  const removeId = event.target.getAttribute("data-remove");
  const downloadId = event.target.getAttribute("data-download");
  
  if (removeId) {
    removeItem(parseInt(removeId));
  }
  
  if (downloadId) {
    downloadTranscript(parseInt(downloadId));
  }
});

// Initial fetch
fetchQueue();
