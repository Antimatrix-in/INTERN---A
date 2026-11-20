// ANTI-MATRIX - Authentication Page Scripts
document.addEventListener('DOMContentLoaded', function () {
  // Password Show / Hide toggle
  const toggleBtn = document.getElementById('passwordToggleBtn');
  const passwordInput = document.getElementById('passwordInput');

  if (toggleBtn && passwordInput) {
    toggleBtn.addEventListener('click', function () {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);
      const icon = toggleBtn.querySelector('i');
      if (icon) {
        if (type === 'text') {
          icon.classList.remove('bi-eye');
          icon.classList.add('bi-eye-slash');
        } else {
          icon.classList.remove('bi-eye-slash');
          icon.classList.add('bi-eye');
        }
      }
    });
  }

  // Client-side quick validation feedback
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      const submitBtn = document.getElementById('loginSubmitBtn');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Authenticating...';
      }
    });
  }
});
