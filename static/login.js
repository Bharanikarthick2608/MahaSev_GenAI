// Login Page JavaScript

// Toggle between citizen and admin login
const citizenBtn = document.getElementById('citizenBtn');
const adminBtn = document.getElementById('adminBtn');
const citizenForm = document.getElementById('citizenForm');
const adminForm = document.getElementById('adminForm');

citizenBtn.addEventListener('click', () => {
    citizenBtn.classList.add('active');
    adminBtn.classList.remove('active');
    citizenForm.classList.remove('hidden');
    adminForm.classList.add('hidden');
});

adminBtn.addEventListener('click', () => {
    adminBtn.classList.add('active');
    citizenBtn.classList.remove('active');
    adminForm.classList.remove('hidden');
    citizenForm.classList.add('hidden');
});

// Toggle password visibility
document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target');
        const input = document.getElementById(targetId);
        
        if (input.type === 'password') {
            input.type = 'text';
            this.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
            `;
        } else {
            input.type = 'password';
            this.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                </svg>
            `;
        }
    });
});

// Handle citizen form submission
citizenForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const citizenId = document.getElementById('citizenId').value;
    const password = document.getElementById('citizenPassword').value;
    
    // Show loading state
    const submitBtn = citizenForm.querySelector('.submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>Signing in...</span>';
    submitBtn.disabled = true;
    
    // Create form data and submit to server
    try {
        const formData = new FormData();
        formData.append('citizenId', citizenId);
        formData.append('citizenPassword', password);
        
        const response = await fetch('/login', {
            method: 'POST',
            body: formData
        });
        
        if (response.redirected) {
            // Successful login - redirect to dashboard
            submitBtn.innerHTML = '<span>Success!</span>';
            setTimeout(() => {
                window.location.href = response.url;
            }, 500);
        } else if (response.ok) {
            // Check if we should redirect
            window.location.href = '/dashboard';
        } else {
            throw new Error('Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        
        // Show error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = 'background: #fee; color: #c33; padding: 12px; border-radius: 8px; margin-top: 16px; border: 1px solid #fcc;';
        errorDiv.innerHTML = '<strong>Login failed!</strong> Please try again.';
        
        // Remove existing error message if any
        const existingError = citizenForm.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        citizenForm.appendChild(errorDiv);
        
        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
});

// Handle admin form submission
adminForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const adminEmail = document.getElementById('adminEmail').value.trim();
    const password = document.getElementById('adminPassword').value;
    
    // Show loading state
    const submitBtn = adminForm.querySelector('.submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>Logging in...</span>';
    submitBtn.disabled = true;
    
    // Submit to server
    try {
        const formData = new FormData();
        formData.append('adminEmail', adminEmail);
        formData.append('adminPassword', password);
        
        const response = await fetch('/login', {
            method: 'POST',
            body: formData
        });
        
        if (response.redirected) {
            // Successful login - redirect to dashboard
            submitBtn.innerHTML = '<span>Success!</span>';
            setTimeout(() => {
                window.location.href = response.url;
            }, 500);
        } else if (response.ok) {
            // Check if we should redirect
            window.location.href = '/dashboard';
        } else {
            throw new Error('Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        
        // Show error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = 'background: #fee; color: #c33; padding: 12px; border-radius: 8px; margin-top: 16px; border: 1px solid #fcc;';
        errorDiv.innerHTML = '<strong>Invalid credentials!</strong> Please use:<br>Email: admin@maharashtra.gov.in<br>Password: admin123';
        
        // Remove existing error message if any
        const existingError = adminForm.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        adminForm.appendChild(errorDiv);
        
        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
});

// Add enter key support for forms
document.querySelectorAll('.login-form input').forEach(input => {
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const form = input.closest('.login-form');
            if (form && !form.classList.contains('hidden')) {
                form.dispatchEvent(new Event('submit'));
            }
        }
    });
});

// Console message
console.log('%cSecure Login Portal', 'font-size: 20px; font-weight: bold; color: #2563eb;');
console.log('%cAll authentication attempts are logged and monitored', 'font-size: 12px; color: #ef4444;');

