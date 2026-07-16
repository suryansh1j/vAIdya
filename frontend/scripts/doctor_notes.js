// Doctor Notes page: loads the selected patient record (set by index.js via
// localStorage) and lets the doctor review/edit fields and export a PDF.

document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('patientInfoForm');

  // Make all textareas auto-resize
  const textareas = form.querySelectorAll('textarea');
  textareas.forEach(textarea => {
    textarea.style.height = textarea.scrollHeight + 'px';
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    });
  });

  const token = localStorage.getItem('vaidya_token');
  const patientId = localStorage.getItem('currentPatientId');

  if (!token || !patientId) {
    alert('No patient selected. Process an audio file or pick a patient from the records tab first.');
    window.location.href = 'index.html';
    return;
  }

  // Map API response fields (snake_case) to form field names (PascalCase)
  const fieldMap = {
    PatientName: 'patient_name',
    Age: 'age',
    Gender: 'gender',
    ChiefComplaint: 'chief_complaint',
    PastMedicalHistory: 'past_medical_history',
    FamilyHistory: 'family_history',
    PreviousSurgeries: 'previous_surgeries',
    Lifestyle: 'lifestyle',
    Allergies: 'allergies',
    CurrentMedications: 'current_medications',
  };

  try {
    const response = await fetch(`${window.API_BASE}/patients/${patientId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.status === 401) {
      alert('Session expired. Please login again.');
      window.location.href = 'index.html';
      return;
    }
    if (!response.ok) {
      throw new Error('Failed to fetch patient info');
    }

    const patient = await response.json();

    for (const [formName, apiName] of Object.entries(fieldMap)) {
      const field = form.elements.namedItem(formName);
      if (field) {
        field.value = patient[apiName] || '';
        if (field.tagName.toLowerCase() === 'textarea') {
          field.style.height = 'auto';
          field.style.height = field.scrollHeight + 'px';
        }
      }
    }
  } catch (err) {
    alert('Error loading patient info: ' + err.message);
  }

  // Save button — persists edits via PATCH
  const saveButton = document.createElement('button');
  saveButton.textContent = 'Save Changes';
  saveButton.type = 'button';
  saveButton.style.marginTop = '20px';
  saveButton.style.marginRight = '10px';
  form.insertAdjacentElement('afterend', saveButton);

  saveButton.addEventListener('click', async () => {
    const payload = {};
    for (const [formName, apiName] of Object.entries(fieldMap)) {
      const field = form.elements.namedItem(formName);
      if (field) {
        payload[apiName] = field.value || null;
      }
    }

    saveButton.disabled = true;
    saveButton.textContent = 'Saving...';

    try {
      const response = await fetch(`${window.API_BASE}/patients/${patientId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (response.status === 401) {
        alert('Session expired. Please login again.');
        window.location.href = 'index.html';
        return;
      }
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Save failed');
      }

      saveButton.textContent = 'Saved ✓';
      setTimeout(() => { saveButton.textContent = 'Save Changes'; }, 2000);
    } catch (err) {
      alert('Error saving changes: ' + err.message);
      saveButton.textContent = 'Save Changes';
    } finally {
      saveButton.disabled = false;
    }
  });

  // PDF export button
  const pdfButton = document.createElement('button');
  pdfButton.textContent = 'Download PDF';
  pdfButton.type = 'button';
  pdfButton.className = 'btn-ghost';
  saveButton.insertAdjacentElement('afterend', pdfButton);

  pdfButton.addEventListener('click', () => {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.text("Doctor's Notes - Patient Info", 105, 20, { align: 'center' });

    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');

    let y = 40;

    for (const element of form.elements) {
      if (!element.name) continue;

      const label = element.previousElementSibling?.innerText || element.name;
      const value = element.value || 'N/A';
      const lines = doc.splitTextToSize(value, 110);

      doc.setFont('helvetica', 'bold');
      doc.text(`${label}`, 20, y);
      doc.setFont('helvetica', 'normal');
      doc.text(lines, 80, y);

      const blockHeight = Math.max(lines.length * 5, 7);

      doc.setDrawColor(200, 200, 200);
      doc.setLineWidth(0.2);
      doc.line(20, y + blockHeight - 3, 190, y + blockHeight - 3);

      y += blockHeight + 4;

      if (y > 270) {
        doc.addPage();
        y = 30;
      }
    }

    doc.setFontSize(10);
    doc.setTextColor(120);
    doc.text('Generated by vAIdya', 105, 285, { align: 'center' });

    doc.save('Patient_Info.pdf');
  });
});
