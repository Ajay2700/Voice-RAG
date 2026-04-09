const el = (id) => document.getElementById(id);

const qdrantUrl = el("qdrantUrl");
const qdrantKey = el("qdrantKey");
const openaiKey = el("openaiKey");
const voiceSelect = el("voiceSelect");
const saveConfigBtn = el("saveConfigBtn");
const statusPill = el("statusPill");

const pdfFile = el("pdfFile");
const uploadBtn = el("uploadBtn");
const uploadMsg = el("uploadMsg");
const uploadState = el("uploadState");
const docList = el("docList");

const queryInput = el("queryInput");
const searchScope = el("searchScope");
const askBtn = el("askBtn");
const responseText = el("responseText");
const sourcesWrap = el("sourcesWrap");
const audioPlayer = el("audioPlayer");

const toast = el("toast");

function showToast(message, ok = false) {
  toast.textContent = message;
  toast.classList.remove("hidden", "ok");
  if (ok) toast.classList.add("ok");
  setTimeout(() => toast.classList.add("hidden"), 3500);
}

function setUploadState(state, message) {
  uploadState.classList.remove("busy", "success", "error");
  uploadState.textContent = message;
  if (state === "busy") uploadState.classList.add("busy");
  if (state === "success") uploadState.classList.add("success");
  if (state === "error") uploadState.classList.add("error");
}

function escapeHtml(input) {
  return input
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatResponseText(raw) {
  if (!raw || !raw.trim()) return "<p>No response.</p>";

  let text = escapeHtml(raw.trim());

  // Bold markdown: **text**
  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Convert lines beginning with "-" into list items.
  const lines = text.split(/\r?\n/);
  let html = "";
  let inList = false;

  for (const lineRaw of lines) {
    const line = lineRaw.trim();
    if (!line) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      continue;
    }

    if (line.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${line.slice(2).trim()}</li>`;
    } else {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += `<p>${line}</p>`;
    }
  }
  if (inList) html += "</ul>";

  return html || "<p>No response.</p>";
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function renderDocuments(docs) {
  docList.innerHTML = "";
  searchScope.innerHTML = "";

  const all = document.createElement("option");
  all.value = "All documents";
  all.textContent = "All documents";
  searchScope.appendChild(all);

  for (const doc of docs) {
    const li = document.createElement("li");
    li.textContent = doc;
    docList.appendChild(li);

    const opt = document.createElement("option");
    opt.value = doc;
    opt.textContent = doc;
    searchScope.appendChild(opt);
  }
}

function setReadyPill(ready, backend) {
  if (ready) {
    statusPill.textContent = `Initialized (${backend || "unknown"} embeddings)`;
    statusPill.classList.add("ok");
  } else {
    statusPill.textContent = "Not initialized";
    statusPill.classList.remove("ok");
  }
}

async function refreshStatus() {
  const data = await api("/api/status");
  voiceSelect.innerHTML = "";
  for (const voice of data.voices || []) {
    const opt = document.createElement("option");
    opt.value = voice;
    opt.textContent = voice;
    if (voice === data.selected_voice) opt.selected = true;
    voiceSelect.appendChild(opt);
  }
  renderDocuments(data.documents || []);
  setReadyPill(data.ready, data.embed_backend);
}

saveConfigBtn.addEventListener("click", async () => {
  try {
    saveConfigBtn.disabled = true;
    await api("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        qdrant_url: qdrantUrl.value,
        qdrant_api_key: qdrantKey.value,
        openai_api_key: openaiKey.value,
        selected_voice: voiceSelect.value || "coral",
      }),
    });
    await refreshStatus();
    showToast("Configuration saved.", true);
  } catch (e) {
    showToast(e.message);
  } finally {
    saveConfigBtn.disabled = false;
  }
});

uploadBtn.addEventListener("click", async () => {
  if (!pdfFile.files.length) {
    showToast("Select a PDF file first.");
    return;
  }
  try {
    uploadBtn.disabled = true;
    setUploadState("busy", "Uploading file...");
    uploadMsg.textContent = "Uploading PDF to server...";

    // Brief UI state transition so users can clearly see indexing phase.
    setTimeout(() => {
      setUploadState("busy", "Indexing document...");
      uploadMsg.textContent = "Extracting text, creating embeddings, storing vectors...";
    }, 300);

    const form = new FormData();
    form.append("file", pdfFile.files[0]);
    const data = await api("/api/upload", {
      method: "POST",
      body: form,
    });

    setUploadState("success", "Indexed successfully");
    uploadMsg.textContent = `${data.message} (${data.chunks} chunks indexed)`;
    await refreshStatus();
    showToast("File uploaded and indexed successfully.", true);
  } catch (e) {
    setUploadState("error", "Indexing failed");
    uploadMsg.textContent = "";
    showToast(e.message);
  } finally {
    uploadBtn.disabled = false;
  }
});

askBtn.addEventListener("click", async () => {
  const query = queryInput.value.trim();
  if (!query) {
    showToast("Enter a question first.");
    return;
  }

  try {
    askBtn.disabled = true;
    responseText.textContent = "Thinking...";
    sourcesWrap.innerHTML = "";
    audioPlayer.removeAttribute("src");

    const data = await api("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        search_scope: searchScope.value,
      }),
    });

    responseText.innerHTML = formatResponseText(data.text_response || "");

    for (const src of data.sources || []) {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = src;
      sourcesWrap.appendChild(tag);
    }

    if (data.audio_path) {
      audioPlayer.src = `/api/audio?path=${encodeURIComponent(data.audio_path)}`;
      audioPlayer.load();
    }
  } catch (e) {
    responseText.innerHTML = "<p>Failed to answer your question.</p>";
    showToast(e.message);
  } finally {
    askBtn.disabled = false;
  }
});

refreshStatus().catch((e) => showToast(e.message));

