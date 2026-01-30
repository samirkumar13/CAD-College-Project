document.addEventListener("DOMContentLoaded", () => {
  console.log("✓ SYSTEM INITIALIZED - DEFENSE MODULE LOADED");

  // DOM Elements - Updated for new ID structure
  const els = {
    uploadBtn: document.getElementById("uploadBtn"),
    detectBtn: document.getElementById("detectBtn"),
    fileInput: document.getElementById("fileInput"),
    fileInfo: document.getElementById("fileInfo"),
    previewImg: document.getElementById("previewImg"),
    resultImg: document.getElementById("resultImg"),
    downloadLink: document.getElementById("downloadLink"),
    processingText: document.getElementById("processingText"),
    detectionList: document.getElementById("detectionList"),
    totalCount: document.getElementById("totalCount"),
    boxesContainer: document.getElementById("boxesContainer"),
    previewBox: document.getElementById("previewBox"),
    resultBox: document.getElementById("resultBox"),
    placeholderState: document.getElementById("placeholderState"),
    ollamaStatus: document.getElementById("ollamaStatus"),
    semanticSection: document.getElementById("semanticSection")
  };

  // Check critical elements
  if (!els.uploadBtn || !els.detectBtn) {
    console.error("CRITICAL GUI FAILURE: Missing control elements");
    return;
  }

  let currentFile = null;

  // --- SYSTEM STATUS CHECK ---
  fetch('/api/status')
    .then(res => res.json())
    .then(data => {
      if (els.ollamaStatus) {
        if (data.ollama_available) {
          els.ollamaStatus.textContent = 'ONLINE';
          els.ollamaStatus.className = 'value online';
          els.ollamaStatus.title = `Model: ${data.ollama_model}`;
        } else {
          els.ollamaStatus.textContent = 'OFFLINE';
          els.ollamaStatus.className = 'value offline';
        }
      }
    })
    .catch(() => {
      if (els.ollamaStatus) {
        els.ollamaStatus.textContent = 'ERROR';
        els.ollamaStatus.className = 'value offline';
      }
    });

  // --- EVENT HANDLERS ---

  // Upload Interaction
  els.uploadBtn.addEventListener("click", () => els.fileInput.click());

  els.fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    currentFile = file;
    els.fileInfo.textContent = `File: ${file.name}`;

    // Show Preview
    els.previewImg.src = URL.createObjectURL(file);
    els.placeholderState.style.display = 'none';
    els.previewBox.style.display = 'flex';
    els.resultBox.style.display = 'none';

    // Enable Detection
    els.detectBtn.disabled = false;

    // Reset Intel Panel
    els.totalCount.textContent = "0";
    els.detectionList.innerHTML = '<li class="empty-state">-- AWAITING ANALYSIS --</li>';
    if (els.semanticSection) {
      els.semanticSection.innerHTML = '<p class="semantic-text typing-effect">Target acquired. Ready to initiate analysis...</p>';
    }
  });

  // Detection Process
  els.detectBtn.addEventListener("click", async () => {
    if (!currentFile) return;

    // GUI Lock
    els.detectBtn.disabled = true;
    els.processingText.style.display = 'block';
    els.previewBox.style.display = 'none'; // Hide preview, show processing result layer
    els.resultBox.style.display = 'flex';
    els.resultImg.style.display = 'none'; // Hide result image until ready

    if (els.semanticSection) {
      els.semanticSection.innerHTML = '<p class="semantic-text typing-effect">PROCESSING IMAGE...</p>';
    }

    const fd = new FormData();
    fd.append("images[]", currentFile);

    try {
      const res = await fetch("/api/process", { method: "POST", body: fd });

      if (!res.ok) throw new Error(`Status ${res.status}`);

      const data = await res.json();

      if (data.error) throw new Error(data.error);

      // Success - Render Results
      const imgData = data.processedImages[0];
      const imgUrlWithLabels = imgData?.url || "";
      const imgUrlNoLabels = imgData?.urlNoLabels || imgUrlWithLabels;

      if (imgUrlWithLabels) {
        // Store both URLs for toggle
        els.resultImg.dataset.urlLabels = imgUrlWithLabels;
        els.resultImg.dataset.urlNoLabels = imgUrlNoLabels;

        // Default: show with labels
        els.resultImg.src = imgUrlWithLabels;
        els.resultImg.style.display = 'block';
        els.processingText.style.display = 'none';

        // Setup Download
        els.downloadLink.setAttribute('download', 'analysis_result.jpg');
        els.downloadLink.href = imgData?.downloadUrl || imgUrlWithLabels;
        els.downloadLink.style.display = 'inline-block';

        // Show label toggle
        const toggleWrapper = document.getElementById('labelToggleWrapper');
        const labelToggle = document.getElementById('labelToggle');
        if (toggleWrapper) toggleWrapper.style.display = 'flex';
        if (labelToggle) {
          labelToggle.checked = true; // Default to labels on
          labelToggle.onchange = () => {
            els.resultImg.src = labelToggle.checked ? imgUrlWithLabels : imgUrlNoLabels;
            els.downloadLink.href = labelToggle.checked ? imgUrlWithLabels : imgUrlNoLabels;
          };
        }
      }

      // Render Metrics
      els.totalCount.textContent = data.total;
      renderDetections(data.detections, data.classColors);

      // Render Semantic Analysis
      renderSemanticAnalysis(data);

    } catch (err) {
      console.error("EXECUTION FAIL", err);
      alert(`ANALYSIS FAILED: ${err.message}`);
      els.processingText.style.display = 'none';
      els.previewBox.style.display = 'flex'; // Revert to preview
      els.resultBox.style.display = 'none';
    } finally {
      els.detectBtn.disabled = false;
    }
  });

  // --- RENDERING HELPERS ---

  function renderDetections(detections, colors) {
    if (!els.detectionList) return;

    els.detectionList.innerHTML = "";
    const sorted = Object.entries(detections || {}).sort((a, b) => b[1] - a[1]);

    if (sorted.length === 0) {
      els.detectionList.innerHTML = '<li class="empty-state">-- NO DETECTIONS --</li>';
      return;
    }

    sorted.forEach(([cls, cnt]) => {
      const li = document.createElement("li");
      if (cnt > 0) li.classList.add("detected");

      li.innerHTML = `
        <span class="color-box" style="background:${colors[cls] || '#555'}"></span>
        <span class="name">${cls.toUpperCase()}</span>
        <span class="count-pill">${cnt}</span>
      `;
      els.detectionList.appendChild(li);
    });
  }

  function renderSemanticAnalysis(data) {
    if (!els.semanticSection) return;

    if (data.semantic_explanation && typeof data.semantic_explanation === 'object') {
      const analysis = data.semantic_explanation;

      // Threat Color Mapping for Badge
      const threatColors = {
        'LOW': '#4ade80',
        'MEDIUM': '#fbbf24',
        'HIGH': '#f97316',
        'CRITICAL': '#ef4444',
        'UNKNOWN': '#9ca3af'
      };

      const tLevel = analysis.threat_level?.toUpperCase() || 'UNKNOWN';
      const tColor = threatColors[tLevel] || '#9ca3af';

      // Build Dashboard HTML using simpler headers without //
      let html = `
        <div class="analysis-threat" style="border-left-color: ${tColor}">
           <div class="threat-header">
             <span class="threat-badge" style="color:${tColor}">${tLevel} THREAT</span>
           </div>
           <p class="threat-text">${analysis.threat_justification || ''}</p>
        </div>
      `;

      if (analysis.infrastructure_analysis) {
        html += `<div class="analysis-section"><h4>INFRASTRUCTURE SCAN</h4><p>${analysis.infrastructure_analysis}</p></div>`;
      }

      if (analysis.strategic_assessment) {
        html += `<div class="analysis-section"><h4>STRATEGIC ASSESSMENT</h4><p>${analysis.strategic_assessment}</p></div>`;
      }

      if (analysis.spatial_patterns) {
        html += `<div class="analysis-section"><h4>SPATIAL RELATIONSHIPS</h4><p>${analysis.spatial_patterns}</p></div>`;
      }

      if (analysis.key_observations && analysis.key_observations.length > 0) {
        html += `<div class="analysis-section"><h4>INTEL OBSERVATIONS</h4><ul class="observation-list">`;
        analysis.key_observations.forEach(obs => {
          html += `<li>${obs}</li>`;
        });
        html += `</ul></div>`;
      }

      els.semanticSection.innerHTML = html;

    } else if (data.semantic_explanation) {
      els.semanticSection.innerHTML = `<p class="semantic-text">${data.semantic_explanation}</p>`;
    } else if (data.total > 0 && !data.ollama_available) {
      els.semanticSection.innerHTML = '<p class="semantic-text offline-msg">AI MODULE OFFLINE</p>';
    } else {
      els.semanticSection.innerHTML = '<p class="semantic-text">-- NO INTELLIGENCE GENERATED --</p>';
    }
  }

});
