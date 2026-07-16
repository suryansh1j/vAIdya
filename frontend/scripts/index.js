// ==================== Global State ====================

let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let recordedBlob = null;
let currentPatientId = null;
let lastResult = null;
let nlpAvailable = true;

// Pagination + search state for patient records
const PAGE_SIZE = 20;
let recordsOffset = 0;
let recordsTotal = 0;
let recordsQuery = '';

// ==================== Utilities ====================

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

// Map a MediaRecorder mime type to a file extension the backend accepts.
function extForMimeType(mimeType) {
  const type = (mimeType || '').toLowerCase();
  if (type.includes('mp4') || type.includes('m4a') || type.includes('aac')) return 'm4a';
  if (type.includes('ogg')) return 'ogg';
  if (type.includes('wav')) return 'wav';
  if (type.includes('mpeg') || type.includes('mp3')) return 'mp3';
  return 'webm';
}

// ==================== Tab Switching ====================

document.addEventListener('DOMContentLoaded', () => {
  const navTabs = document.querySelectorAll('.nav-tab');
  const tabPanes = document.querySelectorAll('.tab-pane');

  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;

      // Update active states
      navTabs.forEach(t => t.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      document.getElementById(`${tabName}Tab`).classList.add('active');

      // Load data for specific tabs
      if (tabName === 'records') {
        loadPatientRecords(true);
      }
    });
  });

  initializeAudioProcessing();
  checkServiceStatus();
});

// ==================== Service Status ====================

async function checkServiceStatus() {
  try {
    const response = await fetch(`${window.API_BASE}/health`);
    if (!response.ok) return;

    const health = await response.json();
    nlpAvailable = !!health.nlp_available;

    if (!nlpAvailable) {
      const banner = document.getElementById('nlpBanner');
      if (banner) banner.style.display = 'flex';
    }
  } catch (error) {
    console.warn('Health check failed:', error);
  }
}

// ==================== Audio Recording ====================

function initializeAudioProcessing() {
  const recordBtn = document.getElementById('recordBtn');
  const browseBtn = document.getElementById('browseBtn');
  const audioFile = document.getElementById('audioFile');
  const uploadZone = document.getElementById('uploadZone');
  const processBtn = document.getElementById('processBtn');
  const downloadPdfBtn = document.getElementById('downloadPdfBtn');

  // Record button
  recordBtn.addEventListener('click', toggleRecording);

  // Browse button
  browseBtn.addEventListener('click', () => audioFile.click());

  // File input
  audioFile.addEventListener('change', handleFileSelect);

  // Drag and drop
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      audioFile.files = files;
      handleFileSelect({ target: { files } });
    }
  });

  // Process button
  processBtn.addEventListener('click', processAudio);

  // PDF download button
  if (downloadPdfBtn) {
    downloadPdfBtn.addEventListener('click', downloadResultsPdf);
  }
}

async function toggleRecording() {
  const recordBtn = document.getElementById('recordBtn');
  const recordingStatus = document.getElementById('recordingStatus');

  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    // Start recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        // Use the mime type the browser actually recorded (Chrome/Firefox:
        // audio/webm, Safari: audio/mp4) rather than assuming webm.
        const recordedType = mediaRecorder.mimeType || 'audio/webm';
        recordedBlob = new Blob(audioChunks, { type: recordedType });
        const audioURL = URL.createObjectURL(recordedBlob);

        const audioPlayback = document.getElementById('audioPlayback');
        audioPlayback.src = audioURL;
        audioPlayback.style.display = 'block';

        // Enable process button
        document.getElementById('processBtn').disabled = false;

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      recordingStartTime = Date.now();
      startTimer();

      recordBtn.classList.add('recording');
      recordBtn.innerHTML = '<svg class="mic-svg"><use href="#i-stop"></use></svg>';
      recordingStatus.textContent = 'Recording...';
      recordingStatus.classList.add('active');

      showToast('Recording started', 'info');
    } catch (error) {
      console.error('Error accessing microphone:', error);
      showToast('Error accessing microphone: ' + error.message, 'error');
    }
  } else {
    // Stop recording
    mediaRecorder.stop();
    stopTimer();

    recordBtn.classList.remove('recording');
    recordBtn.innerHTML = '<svg class="mic-svg"><use href="#i-mic"></use></svg>';
    recordingStatus.textContent = 'Recording stopped';
    recordingStatus.classList.remove('active');

    showToast('Recording stopped', 'success');
  }
}

function startTimer() {
  const timerDisplay = document.getElementById('timerDisplay');
  timerInterval = setInterval(() => {
    const elapsed = Date.now() - recordingStartTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  const fileName = document.getElementById('fileName');
  fileName.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;

  // Enable process button
  document.getElementById('processBtn').disabled = false;

  showToast('File selected successfully', 'success');
}

// ==================== Audio Processing ====================

async function processAudio() {
  if (!authManager.isAuthenticated()) {
    showToast('Please login first', 'error');
    showAuthModal();
    return;
  }

  if (!nlpAvailable) {
    showToast('Audio processing is unavailable on this deployment right now.', 'error');
    return;
  }

  const audioFile = document.getElementById('audioFile');
  let fileToUpload = null;

  if (recordedBlob) {
    // Use recorded audio, naming the file to match the recorded format so the
    // backend's extension check accepts it.
    const ext = extForMimeType(recordedBlob.type);
    fileToUpload = new File([recordedBlob], `recording.${ext}`, { type: recordedBlob.type });
  } else if (audioFile.files.length > 0) {
    // Use uploaded file
    fileToUpload = audioFile.files[0];
  } else {
    showToast('Please record or upload an audio file', 'error');
    return;
  }

  // Validate file size (50MB max)
  const maxSize = 50 * 1024 * 1024;
  if (fileToUpload.size > maxSize) {
    showToast('File size exceeds 50MB limit', 'error');
    return;
  }

  showLoadingOverlay('Uploading audio...');
  updateProgress(10, 'Uploading...');

  const formData = new FormData();
  formData.append('file', fileToUpload);

  // Simulate progress while the server works
  let progress = 10;
  const progressInterval = setInterval(() => {
    progress += 5;
    if (progress < 90) {
      updateProgress(progress, 'Processing...');
    }
  }, 3000);

  try {
    const response = await fetch(`${window.API_BASE}/upload-audio`, {
      method: 'POST',
      headers: authManager.getAuthHeaders(),
      body: formData
    });

    if (!response.ok) {
      if (response.status === 401) {
        authManager.logout();
        showAuthModal();
        throw new Error('Session expired. Please login again.');
      }
      if (response.status === 503) {
        nlpAvailable = false;
        checkServiceStatus();
        throw new Error('Audio processing is unavailable on this deployment right now.');
      }
      if (response.status === 429) {
        throw new Error('Too many requests — please wait a minute and try again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    const result = await response.json();

    clearInterval(progressInterval);
    updateProgress(100, 'Complete!');

    setTimeout(() => {
      hideLoadingOverlay();
      displayResults(result);
      showToast('Processing complete!', 'success');

      // Save patient ID for notes page
      if (result.patient_id) {
        currentPatientId = result.patient_id;
        localStorage.setItem('currentPatientId', result.patient_id);
      }
    }, 500);

  } catch (error) {
    console.error('Processing error:', error);
    clearInterval(progressInterval);
    hideLoadingOverlay();
    showToast(error.message, 'error');
  }
}

// Fields as returned in the upload response's patient_info (PascalCase)
const PATIENT_INFO_FIELDS = [
  { key: 'PatientName', label: 'Patient Name' },
  { key: 'Age', label: 'Age' },
  { key: 'Gender', label: 'Gender' },
  { key: 'ChiefComplaint', label: 'Chief Complaint' },
  { key: 'PastMedicalHistory', label: 'Past Medical History' },
  { key: 'FamilyHistory', label: 'Family History' },
  { key: 'PreviousSurgeries', label: 'Previous Surgeries' },
  { key: 'Lifestyle', label: 'Lifestyle' },
  { key: 'Allergies', label: 'Allergies' },
  { key: 'CurrentMedications', label: 'Current Medications' }
];

function displayResults(data) {
  lastResult = data;

  const resultsSection = document.getElementById('resultsSection');
  resultsSection.style.display = 'flex';
  resultsSection.scrollIntoView({ behavior: 'smooth' });

  // Display transcript
  const transcriptText = document.getElementById('transcriptText');
  transcriptText.textContent = data.transcript || 'No transcript available';

  // Display patient info
  const patientInfoGrid = document.getElementById('patientInfoGrid');
  patientInfoGrid.innerHTML = '';

  const patientInfo = data.patient_info || {};

  PATIENT_INFO_FIELDS.forEach(field => {
    const value = patientInfo[field.key] || 'Not provided';
    const item = document.createElement('div');
    item.className = 'info-item';
    item.innerHTML = `
      <div class="info-label">${escapeHtml(field.label)}</div>
      <div class="info-value">${escapeHtml(value)}</div>
    `;
    patientInfoGrid.appendChild(item);
  });

  // Display symptoms
  const symptoms = data.symptoms || { affirmed: [], negated: [] };
  renderSymptomList('affirmedSymptoms', symptoms.affirmed, 'symptom-affirmed', 'No affirmed symptoms detected');
  renderSymptomList('negatedSymptoms', symptoms.negated, 'symptom-negated', 'No negated symptoms detected');
}

function renderSymptomList(elementId, items, badgeClass, emptyText) {
  const container = document.getElementById(elementId);
  container.innerHTML = '';

  if (items && items.length > 0) {
    items.forEach(symptom => {
      const badge = document.createElement('span');
      badge.className = `symptom-badge ${badgeClass}`;
      badge.textContent = symptom;
      container.appendChild(badge);
    });
  } else {
    container.innerHTML = `<p class="empty-state">${escapeHtml(emptyText)}</p>`;
  }
}

// ==================== PDF Export ====================

function downloadResultsPdf() {
  if (!lastResult) {
    showToast('No results to export yet', 'error');
    return;
  }
  if (!window.jspdf) {
    showToast('PDF library failed to load', 'error');
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text('vAIdya - Consultation Summary', 105, 20, { align: 'center' });

  doc.setFontSize(11);
  let y = 35;

  const patientInfo = lastResult.patient_info || {};
  PATIENT_INFO_FIELDS.forEach(field => {
    const value = patientInfo[field.key] || 'N/A';
    const lines = doc.splitTextToSize(String(value), 115);

    doc.setFont('helvetica', 'bold');
    doc.text(`${field.label}:`, 20, y);
    doc.setFont('helvetica', 'normal');
    doc.text(lines, 75, y);

    y += Math.max(lines.length * 5, 7);
    if (y > 265) {
      doc.addPage();
      y = 20;
    }
  });

  const symptoms = lastResult.symptoms || {};
  const affirmed = (symptoms.affirmed || []).join(', ') || 'None detected';
  const negated = (symptoms.negated || []).join(', ') || 'None detected';

  for (const [label, text] of [['Affirmed Symptoms', affirmed], ['Negated Symptoms', negated]]) {
    const lines = doc.splitTextToSize(text, 115);
    doc.setFont('helvetica', 'bold');
    doc.text(`${label}:`, 20, y);
    doc.setFont('helvetica', 'normal');
    doc.text(lines, 75, y);
    y += Math.max(lines.length * 5, 7);
    if (y > 265) {
      doc.addPage();
      y = 20;
    }
  }

  doc.setFontSize(9);
  doc.setTextColor(120);
  doc.text('Generated by vAIdya', 105, 285, { align: 'center' });

  doc.save('Consultation_Summary.pdf');
}

// ==================== Patient Records ====================

async function loadPatientRecords(reset = false) {
  if (!authManager.isAuthenticated()) {
    return;
  }

  if (reset) {
    recordsOffset = 0;
  }

  try {
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset: recordsOffset });
    if (recordsQuery) params.set('q', recordsQuery);

    const response = await fetch(
      `${window.API_BASE}/patients?${params}`,
      { headers: authManager.getAuthHeaders() }
    );

    if (!response.ok) {
      if (response.status === 401) {
        authManager.logout();
        showAuthModal();
        return;
      }
      throw new Error('Failed to load patients');
    }

    const data = await response.json();
    recordsTotal = data.count;
    displayPatientList(data.patients, reset);
    recordsOffset += data.patients.length;
    updateLoadMoreButton();
  } catch (error) {
    console.error('Error loading patients:', error);
    showToast('Failed to load patient records', 'error');
  }
}

function displayPatientList(patients, reset) {
  const patientList = document.getElementById('patientList');

  if (reset) {
    patientList.innerHTML = '';
  }

  if ((!patients || patients.length === 0) && patientList.children.length === 0) {
    const message = recordsQuery
      ? 'No patients match your search.'
      : 'No patients found. Process an audio file to create records.';
    patientList.innerHTML = `<p class="empty-state">${escapeHtml(message)}</p>`;
    return;
  }

  patients.forEach(patient => {
    const card = document.createElement('div');
    card.className = 'patient-card';

    const meta = [
      patient.age ? `Age: ${patient.age}` : null,
      patient.gender || null,
      patient.created_at ? new Date(patient.created_at).toLocaleDateString() : null
    ].filter(Boolean).join(' • ');

    card.innerHTML = `
      <div class="patient-name">${escapeHtml(patient.patient_name || 'Unknown Patient')}</div>
      <div class="patient-meta">${escapeHtml(meta)}</div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.patient-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      loadPatientDetail(patient.id);
    });

    patientList.appendChild(card);
  });
}

function updateLoadMoreButton() {
  let btn = document.getElementById('loadMoreBtn');
  const patientList = document.getElementById('patientList');

  if (!btn) {
    btn = document.createElement('button');
    btn.id = 'loadMoreBtn';
    btn.className = 'btn-secondary';
    btn.textContent = 'Load More';
    btn.style.margin = '1rem auto';
    btn.style.display = 'block';
    btn.addEventListener('click', () => loadPatientRecords(false));
    patientList.insertAdjacentElement('afterend', btn);
  }

  btn.style.display = recordsOffset < recordsTotal ? 'block' : 'none';
}

async function loadPatientDetail(patientId) {
  try {
    const response = await fetch(`${window.API_BASE}/patients/${patientId}`, {
      headers: authManager.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error('Failed to load patient details');
    }

    displayPatientDetail(await response.json());
  } catch (error) {
    console.error('Error loading patient detail:', error);
    showToast('Failed to load patient details', 'error');
  }
}

function displayPatientDetail(patient) {
  const patientDetail = document.getElementById('patientDetail');

  const meta = [
    patient.age ? `Age: ${patient.age}` : null,
    patient.gender || null,
    patient.created_at ? new Date(patient.created_at).toLocaleDateString() : null
  ].filter(Boolean).join(' • ');

  const detailFields = [
    ['Chief Complaint', patient.chief_complaint],
    ['Past Medical History', patient.past_medical_history],
    ['Family History', patient.family_history],
    ['Previous Surgeries', patient.previous_surgeries],
    ['Lifestyle', patient.lifestyle],
    ['Allergies', patient.allergies],
    ['Current Medications', patient.current_medications]
  ];

  const symptoms = patient.symptoms || {};
  const affirmed = (symptoms.affirmed || []).join(', ');
  const negated = (symptoms.negated || []).join(', ');

  patientDetail.innerHTML = `
    <h3>${escapeHtml(patient.patient_name || 'Unknown Patient')}</h3>
    <div class="patient-meta" style="margin-bottom: 1.5rem;">${escapeHtml(meta)}</div>

    ${detailFields.map(([label, value]) => `
      <div class="info-item" style="margin-bottom: 1rem;">
        <div class="info-label">${escapeHtml(label)}</div>
        <div class="info-value">${escapeHtml(value || 'N/A')}</div>
      </div>
    `).join('')}

    <div class="info-item" style="margin-bottom: 1rem;">
      <div class="info-label">Affirmed Symptoms</div>
      <div class="info-value">${escapeHtml(affirmed || 'None')}</div>
    </div>

    <div class="info-item" style="margin-bottom: 1rem;">
      <div class="info-label">Negated Symptoms</div>
      <div class="info-value">${escapeHtml(negated || 'None')}</div>
    </div>

    <div style="display: flex; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap;">
      <button class="btn-primary" id="viewFullRecordBtn">Open in Doctor Notes</button>
      <button class="btn-secondary" id="deletePatientBtn">Delete Record</button>
    </div>
  `;

  document.getElementById('viewFullRecordBtn').addEventListener('click', () => {
    localStorage.setItem('currentPatientId', patient.id);
    window.location.href = 'doctor_notes.html';
  });

  document.getElementById('deletePatientBtn').addEventListener('click', () => {
    deletePatient(patient.id, patient.patient_name);
  });
}

async function deletePatient(patientId, patientName) {
  const label = patientName || 'this patient';
  if (!confirm(`Delete the record for ${label}? This cannot be undone.`)) {
    return;
  }

  try {
    const response = await fetch(`${window.API_BASE}/patients/${patientId}`, {
      method: 'DELETE',
      headers: authManager.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error('Failed to delete patient record');
    }

    showToast('Patient record deleted', 'success');
    document.getElementById('patientDetail').innerHTML = `
      <div class="empty-state-large">
        <div class="empty-icon">📄</div>
        <p>Select a patient to view details</p>
      </div>
    `;
    loadPatientRecords(true);
  } catch (error) {
    console.error('Error deleting patient:', error);
    showToast(error.message, 'error');
  }
}

// ==================== Loading Overlay ====================

function showLoadingOverlay(message = 'Processing...') {
  const overlay = document.getElementById('loadingOverlay');
  const loadingText = overlay.querySelector('.loading-text');
  loadingText.textContent = message;
  overlay.style.display = 'flex';
}

function hideLoadingOverlay() {
  document.getElementById('loadingOverlay').style.display = 'none';
}

function updateProgress(percent, text) {
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');

  progressFill.style.width = `${percent}%`;
  progressText.textContent = text;
}

// ==================== Search Functionality ====================
// Server-side search (matches name, chief complaint, and transcript),
// debounced so we don't fire a request per keystroke.

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('patientSearch');
  if (!searchInput) return;

  let debounceTimer = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      recordsQuery = e.target.value.trim();
      loadPatientRecords(true);
    }, 300);
  });
});
