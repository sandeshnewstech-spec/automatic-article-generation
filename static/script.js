// Global state
let currentArticle = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSavedSettings();
    log('System initialized', 'success');
});

// Toggle provider settings
function toggleProviderSettings() {
    const provider = document.getElementById('model-provider').value;
    const openaiSettings = document.getElementById('openai-settings');
    const ollamaSettings = document.getElementById('ollama-settings');
    const geminiSettings = document.getElementById('gemini-settings');

    // Hide all first
    openaiSettings.classList.add('hidden');
    ollamaSettings.classList.add('hidden');
    geminiSettings.classList.add('hidden');

    if (provider === 'google') {
        geminiSettings.classList.remove('hidden');
        log('Switched to Google Gemini provider', 'info');
    } else {
        ollamaSettings.classList.remove('hidden');
        log('Switched to Ollama (Local) provider', 'info');
    }
}

// Add URL input
function addUrlInput() {
    const container = document.getElementById('url-container');
    const div = document.createElement('div');
    div.className = 'relative group';
    div.innerHTML = `
        <input type="url" class="w-full text-xs px-4 py-3 font-mono pr-10" placeholder="https://example.com/article" onchange="validateUrl(this)">
        <button class="absolute right-3 top-2.5 text-[#444] hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" onclick="removeUrlInput(this)">
            <i class="ri-close-line"></i>
        </button>
    `;
    container.appendChild(div);
    log('URL input added', 'info');
}

// Remove URL input
function removeUrlInput(btn) {
    btn.closest('.relative').remove();
    log('URL input removed', 'info');
}

// Validate URL
function validateUrl(input) {
    try {
        new URL(input.value);
        input.style.borderColor = '#333';
        log(`URL validated: ${input.value}`, 'success');
    } catch {
        input.style.borderColor = '#ff4444';
        log('Invalid URL format', 'error');
    }
}

// Clear form
function clearForm() {
    document.getElementById('keypoints-input').value = '';
    document.getElementById('url-container').innerHTML = `
        <div class="relative group">
            <input type="url" class="w-full text-xs px-4 py-3 font-mono pr-10" placeholder="https://example.com/article" onchange="validateUrl(this)">
            <button class="absolute right-3 top-2.5 text-[#444] hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" onclick="removeUrlInput(this)">
                <i class="ri-close-line"></i>
            </button>
        </div>
    `;
    hidePreview();
    clearLogs();
    log('Form cleared', 'info');
}

// Log message
function log(message, type = 'info') {
    const logContent = document.getElementById('log-content');
    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });

    const colors = {
        info: '#666',
        success: '#0f0',
        error: '#f00',
        warning: '#fa0'
    };

    const icons = {
        info: '→',
        success: '✓',
        error: '✗',
        warning: '⚠'
    };

    const logEntry = document.createElement('div');
    logEntry.style.color = colors[type] || colors.info;
    logEntry.innerHTML = `[${timestamp}] ${icons[type]} ${message}`;

    logContent.appendChild(logEntry);
    logContent.scrollTop = logContent.scrollHeight;

    // Also log to browser console
    console.log(`[${timestamp}] ${message}`);
}

// Clear logs
function clearLogs() {
    document.getElementById('log-content').innerHTML = '';
}

// Show loading state
function showLoading() {
    document.getElementById('preview-empty').classList.add('hidden');
    document.getElementById('preview-content').classList.add('hidden');
    document.getElementById('preview-loading').classList.remove('hidden');
    document.getElementById('log-status').classList.remove('hidden');
}

// Hide preview
function hidePreview() {
    document.getElementById('preview-empty').classList.remove('hidden');
    document.getElementById('preview-content').classList.add('hidden');
    document.getElementById('preview-loading').classList.add('hidden');
    document.getElementById('log-status').classList.add('hidden');
}

// Show content
function showContent() {
    document.getElementById('preview-empty').classList.add('hidden');
    document.getElementById('preview-loading').classList.add('hidden');
    document.getElementById('preview-content').classList.remove('hidden');
    document.getElementById('log-status').classList.add('hidden');
}

// Update step UI
function updateStep(stepNumber, status = 'active') {
    const steps = ['scrape', 'process', 'generate'];
    const stepId = `step-${steps[stepNumber - 1]}`;
    const stepEl = document.getElementById(stepId);

    if (!stepEl) return;

    // Reset all steps
    steps.forEach((s, i) => {
        const el = document.getElementById(`step-${s}`);
        if (i < stepNumber - 1) {
            el.style.opacity = '1';
            el.querySelector('.step-icon').style.borderColor = '#0f0';
            el.querySelector('.step-icon').style.color = '#0f0';
        } else if (i === stepNumber - 1) {
            el.style.opacity = '1';
            el.querySelector('.step-icon').style.borderColor = status === 'active' ? '#fff' : '#0f0';
            el.querySelector('.step-icon').style.color = status === 'active' ? '#fff' : '#0f0';
        } else {
            el.style.opacity = '0.3';
        }
    });
}

// Generate article
async function generateArticle() {
    // Get inputs
    const keypoints = document.getElementById('keypoints-input').value.trim();
    const urlInputs = document.querySelectorAll('#url-container input[type="url"]');
    const urls = Array.from(urlInputs)
        .map(input => input.value.trim())
        .filter(url => url.length > 0);

    // Validate
    if (!keypoints) {
        log('Error: Keypoints are required', 'error');
        alert('કૃપા કરીને મુખ્ય મુદ્દાઓ દાખલ કરો (Please enter keypoints)');
        return;
    }

    if (urls.length === 0) {
        log('Warning: No source URLs provided', 'warning');
    }

    // Get provider settings
    const provider = document.getElementById('model-provider').value;
    let apiKey = null;
    let baseUrl = null;
    let model = null;

    if (provider === 'google') {
        apiKey = document.getElementById('gemini-key').value.trim();
        model = document.getElementById('gemini-model').value.trim() || 'gemini-1.5-flash';
        if (!apiKey) {
            log('Error: Gemini API key required', 'error');
            alert('Please enter Gemini API key');
            return;
        }
    } else {
        baseUrl = document.getElementById('ollama-url').value.trim() || 'http://localhost:11434/v1';
        model = document.getElementById('ollama-model').value.trim() || 'llama3:latest';
    }

    // Save settings
    saveSettings();

    // Clear previous logs
    clearLogs();

    // Show loading
    showLoading();

    log(`Starting generation process...`, 'info');
    log(`Provider: ${provider}, URLs: ${urls.length}`, 'info');
    log(`Model: ${model}`, 'info');

    // Step 1: Scraping
    updateStep(1, 'active');
    log('Step 1/3: Scraping source URLs...', 'info');

    try {
        const requestBody = {
            keypoints: keypoints,
            source_urls: urls,
            api_key: apiKey,
            base_url: baseUrl,
            model: model
        };

        console.log('Request payload:', requestBody);

        // Create AbortController for timeout (5 minutes)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutes

        let response;
        try {
            response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
        } catch (fetchError) {
            if (fetchError.name === 'AbortError') {
                throw new Error('Request timed out after 5 minutes. Server is taking too long.');
            }
            throw fetchError;
        }

        log('Received response from server', 'info');

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        // Step 2: Processing
        updateStep(2, 'active');
        log('Step 2/3: Processing scraped content...', 'info');

        const result = await response.json();
        console.log('Response data:', result);

        if (!result.success) {
            throw new Error(result.error || 'Generation failed');
        }

        // Step 3: Generating
        updateStep(3, 'active');
        log('Step 3/3: Generating article with LLM...', 'info');

        // Wait a bit to show the step
        await new Promise(resolve => setTimeout(resolve, 500));

        updateStep(3, 'complete');
        log('Generation complete!', 'success');

        // Display article
        displayArticle(result, urls.length);

    } catch (error) {
        log(`Generation Failed: ${error.message}`, 'error');
        console.error('Generation error:', error);
        hidePreview();
        alert(`સમાચાર જનરેશન નિષ્ફળ:\n${error.message}`);
    }
}

// Display article
function displayArticle(result, sourceCount) {
    currentArticle = result;

    // Update metadata
    const now = new Date();
    document.getElementById('meta-time').textContent = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit'
    });
    document.getElementById('meta-sources').textContent = `SOURCES: ${sourceCount}`;

    // Count words in content
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = result.content || '';
    const wordCount = tempDiv.textContent.trim().split(/\s+/).length;
    document.getElementById('meta-length').textContent = `WORDS: ${wordCount}`;

    // Set title and content
    document.getElementById('article-title').textContent = result.title || 'શીર્ષક ઉપલબ્ધ નથી';
    document.getElementById('article-body').innerHTML = result.content || '<p>સામગ્રી ઉપલબ્ધ નથી</p>';

    // Show content
    showContent();

    log(`Article displayed: ${wordCount} words`, 'success');
}

// Copy content
function copyContent() {
    if (!currentArticle) {
        log('No content to copy', 'warning');
        return;
    }

    const text = `${currentArticle.title}\n\n${document.getElementById('article-body').textContent}`;
    navigator.clipboard.writeText(text).then(() => {
        log('Content copied to clipboard', 'success');
    }).catch(err => {
        log('Failed to copy content', 'error');
        console.error('Copy error:', err);
    });
}

// Download JSON
function downloadJSON() {
    if (!currentArticle) {
        log('No content to download', 'warning');
        return;
    }

    const dataStr = JSON.stringify(currentArticle, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `article-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);

    log('Article downloaded as JSON', 'success');
}

// Save settings to localStorage
function saveSettings() {
    const settings = {
        provider: document.getElementById('model-provider').value,
        ollamaUrl: document.getElementById('ollama-url').value,
        ollamaModel: document.getElementById('ollama-model').value
    };
    localStorage.setItem('newsroom-settings', JSON.stringify(settings));
    log('Settings saved', 'info');
}

// Load settings from localStorage
function loadSavedSettings() {
    const saved = localStorage.getItem('newsroom-settings');
    if (!saved) return;

    try {
        const settings = JSON.parse(saved);

        if (settings.provider) {
            document.getElementById('model-provider').value = settings.provider;
            toggleProviderSettings();
        }
        if (settings.ollamaUrl) {
            document.getElementById('ollama-url').value = settings.ollamaUrl;
        }
        if (settings.ollamaModel) {
            document.getElementById('ollama-model').value = settings.ollamaModel;
        }

        log('Settings loaded from previous session', 'info');
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}
