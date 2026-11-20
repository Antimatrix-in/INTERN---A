// ANTI-MATRIX - Admin Dashboard Scripts
document.addEventListener('DOMContentLoaded', function () {
  // Mobile sidebar toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.admin-sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // Copy to clipboard helper
  window.copyToClipboard = function (text, btnElement) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        showCopyFeedback(btnElement);
      }).catch(err => {
        fallbackCopy(text, btnElement);
      });
    } else {
      fallbackCopy(text, btnElement);
    }
  };

  function fallbackCopy(text, btnElement) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      showCopyFeedback(btnElement);
    } catch (err) {
      alert("Failed to copy automatically. Please select and copy manually.");
    }
    document.body.removeChild(textarea);
  }

  function showCopyFeedback(btnElement) {
    if (!btnElement) return;
    const originalText = btnElement.innerHTML;
    btnElement.innerHTML = '<i class="bi bi-check2 me-1"></i>Copied!';
    btnElement.classList.add('btn-success');
    setTimeout(() => {
      btnElement.innerHTML = originalText;
      btnElement.classList.remove('btn-success');
    }, 2000);
  }
});
