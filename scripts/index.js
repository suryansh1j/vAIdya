// ==================== Global State ====================

let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let recordedBlob = null;
let currentPatientId = null;

const API_BASE = '/api/v1';

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
        loadPatientRecords();
      }
    });
  });

  initializeAudioProcessing();
});

// ==================== Audio Recording ====================

function initializeAudioProcessing() {
  const recordBtn = document.getElementById('recordBtn');
  const browseBtn = document.getElementById('browseBtn');
  const audioFile = document.getElementById('audioFile');
  const uploadZone = document.getElementById('uploadZone');
  const processBtn = document.getElementById('processBtn');

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
        recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
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
      recordBtn.innerHTML = '<div class="mic-icon">⏹️</div>';
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
    recordBtn.innerHTML = '<div class="mic-icon">🎙️</div>';
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

  const audioFile = document.getElementById('audioFile');
  let fileToUpload = null;

  if (recordedBlob) {
    // Use recorded audio
    fileToUpload = new File([recordedBlob], 'recording.webm', { type: 'audio/webm' });
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

  try {
    const response = await fetch(`${API_BASE}/upload-audio`, {
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
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    updateProgress(30, 'Transcribing audio...');

    // Simulate progress updates
    let progress = 30;
    const progressInterval = setInterval(() => {
      progress += 5;
      if (progress < 90) {
        updateProgress(progress, 'Processing...');
      }
    }, 3000);

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
    hideLoadingOverlay();
    showToast(error.message, 'error');
  }
}

function displayResults(data) {
  const resultsSection = document.getElementById('resultsSection');
  resultsSection.style.display = 'block';
  resultsSection.scrollIntoView({ behavior: 'smooth' });

  // Display transcript
  const transcriptText = document.getElementById('transcriptText');
  transcriptText.textContent = data.transcript || 'No transcript available';

  // Display patient info
  const patientInfoGrid = document.getElementById('patientInfoGrid');
  patientInfoGrid.innerHTML = '';

  const patientInfo = data.patient_info || {};
  const fields = [
    { key: 'name', label: 'Patient Name' },
    { key: 'age', label: 'Age' },
    { key: 'gender', label: 'Gender' },
    { key: 'chief_complaint', label: 'Chief Complaint' },
    { key: 'past_medical_history', label: 'Past Medical History' },
    { key: 'family_history', label: 'Family History' },
    { key: 'previous_surgeries', label: 'Previous Surgeries' },
    { key: 'lifestyle', label: 'Lifestyle' },
    { key: 'allergies', label: 'Allergies' },
    { key: 'current_medications', label: 'Current Medications' }
  ];

  fields.forEach(field => {
    const value = patientInfo[field.key] || 'Not provided';
    const item = document.createElement('div');
    item.className = 'info-item';
    item.innerHTML = `
      <div class="info-label">${field.label}</div>
      <div class="info-value">${value}</div>
    `;
    patientInfoGrid.appendChild(item);
  });

  // Display symptoms
  const symptoms = data.symptoms || { affirmed: [], negated: [] };

  const affirmedSymptoms = document.getElementById('affirmedSymptoms');
  affirmedSymptoms.innerHTML = '';
  if (symptoms.affirmed && symptoms.affirmed.length > 0) {
    symptoms.affirmed.forEach(symptom => {
      const badge = document.createElement('span');
      badge.className = 'symptom-badge symptom-affirmed';
      badge.textContent = symptom;
      affirmedSymptoms.appendChild(badge);
    });
  } else {
    affirmedSymptoms.innerHTML = '<p class="empty-state">No affirmed symptoms detected</p>';
  }

  const negatedSymptoms = document.getElementById('negatedSymptoms');
  negatedSymptoms.innerHTML = '';
  if (symptoms.negated && symptoms.negated.length > 0) {
    symptoms.negated.forEach(symptom => {
      const badge = document.createElement('span');
      badge.className = 'symptom-badge symptom-negated';
      badge.textContent = symptom;
      negatedSymptoms.appendChild(badge);
    });
  } else {
    negatedSymptoms.innerHTML = '<p class="empty-state">No negated symptoms detected</p>';
  }
}

// ==================== Patient Records ====================

async function loadPatientRecords() {
  if (!authManager.isAuthenticated()) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/patients`, {
      headers: authManager.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error('Failed to load patients');
    }

    const patients = await response.json();
    displayPatientList(patients);
  } catch (error) {
    console.error('Error loading patients:', error);
    showToast('Failed to load patient records', 'error');
  }
}

function displayPatientList(patients) {
  const patientList = document.getElementById('patientList');

  if (!patients || patients.length === 0) {
    patientList.innerHTML = '<p class="empty-state">No patients found. Process an audio file to create records.</p>';
    return;
  }

  patientList.innerHTML = '';

  patients.forEach(patient => {
    const card = document.createElement('div');
    card.className = 'patient-card';
    card.innerHTML = `
      <div class="patient-name">${patient.name || 'Unknown Patient'}</div>
      <div class="patient-meta">
        ${patient.age ? `Age: ${patient.age}` : ''} 
        ${patient.gender ? `• ${patient.gender}` : ''}
        ${patient.created_at ? `• ${new Date(patient.created_at).toLocaleDateString()}` : ''}
      </div>
      <div class="patient-preview">${patient.chief_complaint || 'No chief complaint'}</div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.patient-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      displayPatientDetail(patient);
    });

    patientList.appendChild(card);
  });
}

function displayPatientDetail(patient) {
  const patientDetail = document.getElementById('patientDetail');

  patientDetail.innerHTML = `
    <h3>${patient.name || 'Unknown Patient'}</h3>
    <div class="patient-meta" style="margin-bottom: 1.5rem;">
      ${patient.age ? `Age: ${patient.age}` : ''} 
      ${patient.gender ? `• ${patient.gender}` : ''}
    </div>
    
    <div class="info-item" style="margin-bottom: 1rem;">
      <div class="info-label">Chief Complaint</div>
      <div class="info-value">${patient.chief_complaint || 'N/A'}</div>
    </div>
    
    <div class="info-item" style="margin-bottom: 1rem;">
      <div class="info-label">Past Medical History</div>
      <div class="info-value">${patient.past_medical_history || 'N/A'}</div>
    </div>
    
    <div class="info-item" style="margin-bottom: 1rem;">
      <div class="info-label">Current Medications</div>
      <div class="info-value">${patient.current_medications || 'N/A'}</div>
    </div>
    
    <div class="info-item" style="margin-bottom: 1rem;">
      <div class="info-label">Allergies</div>
      <div class="info-value">${patient.allergies || 'N/A'}</div>
    </div>
    
    <button class="btn-primary" onclick="viewFullRecord(${patient.id})" style="margin-top: 1rem;">
      View Full Record
    </button>
  `;
}

function viewFullRecord(patientId) {
  localStorage.setItem('currentPatientId', patientId);
  window.location.href = 'doctor_notes.html';
}

// Make viewFullRecord globally available
window.viewFullRecord = viewFullRecord;

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

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('patientSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const searchTerm = e.target.value.toLowerCase();
      const patientCards = document.querySelectorAll('.patient-card');

      patientCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(searchTerm) ? 'block' : 'none';
      });
    });
  }
});
