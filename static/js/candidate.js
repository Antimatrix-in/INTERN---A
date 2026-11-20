// ANTI-MATRIX - Candidate Dashboard & Examination Session Scripts
document.addEventListener('DOMContentLoaded', function () {
  // 1. Candidate 48-Hour Credential Countdown Timer
  const countdownEl = document.getElementById('credentialCountdown');
  if (countdownEl) {
    let remainingSeconds = parseInt(countdownEl.dataset.remainingSeconds, 10) || 0;

    function updateCountdown() {
      if (remainingSeconds <= 0) {
        countdownEl.innerHTML = '<span class="text-danger fw-bold">EXPIRED</span>';
        const startBtn = document.getElementById('startAssessmentBtn');
        if (startBtn) {
          startBtn.disabled = true;
          startBtn.classList.add('disabled');
        }
        return;
      }

      const hours = Math.floor(remainingSeconds / 3600);
      const minutes = Math.floor((remainingSeconds % 3600) / 60);
      const seconds = remainingSeconds % 60;

      countdownEl.innerText = 
        String(hours).padStart(2, '0') + ':' + 
        String(minutes).padStart(2, '0') + ':' + 
        String(seconds).padStart(2, '0');

      remainingSeconds--;
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
  }

  // 2. Exam Session Timer & Autosave
  const examTimerEl = document.getElementById('examSessionTimer');
  if (examTimerEl) {
    let examSeconds = parseInt(examTimerEl.dataset.secondsRemaining, 10) || 0;

    function tickExamTimer() {
      if (examSeconds <= 0) {
        examTimerEl.innerHTML = '<span class="text-danger">TIME UP</span>';
        alert("Your examination time limit has expired. Submitting your answers now...");
        const submitForm = document.getElementById('examSubmitForm');
        if (submitForm) submitForm.submit();
        return;
      }

      const m = Math.floor(examSeconds / 60);
      const s = examSeconds % 60;
      examTimerEl.innerText = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
      examSeconds--;
    }

    tickExamTimer();
    setInterval(tickExamTimer, 1000);
  }
});

// Autosave helper for candidate answers
window.autosaveAnswer = function (questionId, selectedOption, csrfToken) {
  const statusEl = document.getElementById('autosaveStatus');
  if (statusEl) statusEl.innerHTML = '<span class="text-warning"><i class="bi bi-cloud-arrow-up me-1"></i>Saving...</span>';

  fetch('/candidate/api/autosave', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
      question_id: questionId,
      selected_option: selectedOption
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      if (statusEl) statusEl.innerHTML = '<span class="text-success"><i class="bi bi-check2-circle me-1"></i>Saved</span>';
      // Update question palette button
      const paletteBtn = document.getElementById('palette-btn-' + questionId);
      if (paletteBtn) {
        paletteBtn.classList.remove('btn-outline-secondary');
        paletteBtn.classList.add('btn-primary');
      }
    } else {
      if (statusEl) statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>Save error</span>';
    }
  })
  .catch(err => {
    if (statusEl) statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>Connection lost</span>';
  });
};
