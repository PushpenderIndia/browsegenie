// voice_input.js — Web Speech API voice input module
//
// Usage:
//   VoiceInput.attach('ba-task', document.getElementById('ba-voice-container'));
//
// The module injects a mic button into `container` and wires it to the
// textarea identified by `textareaId`. No global state leaks; each call to
// attach() owns its own recognition instance.

const VoiceInput = (() => {

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition || null;

  // ── Public API ────────────────────────────────────────────────────────────

  function isSupported() {
    return !!SpeechRecognition;
  }

  /**
   * Inject a mic button into `container` and bind it to `textareaId`.
   * @param {string}      textareaId  ID of the target <textarea>
   * @param {HTMLElement} container   Element that will receive the button
   */
  function attach(textareaId, container) {
    if (!container) return;

    const btn = _createButton();
    container.appendChild(btn);

    if (!isSupported()) {
      btn.disabled = true;
      btn.classList.add('vi-btn--unsupported');
      btn.title = 'Voice input is not supported in this browser';
      return;
    }

    const recognition = _buildRecognition();
    let recording = false;
    let baseText  = '';   // textarea content captured at the moment recording starts
    let separator = '';   // space injected between existing text and new speech

    btn.addEventListener('click', () => {
      if (recording) {
        recognition.stop();
      } else {
        try {
          recognition.start();
        } catch (e) {
          // Recognition already started — ignore
        }
      }
    });

    recognition.onstart = () => {
      const textarea = document.getElementById(textareaId);
      baseText  = textarea ? textarea.value : '';
      separator = baseText && !/\s$/.test(baseText) ? ' ' : '';
      recording = true;
      btn.classList.add('vi-btn--recording');
      btn.title = 'Recording… click to stop';
      _setIcon(btn, _stopIcon());
    };

    recognition.onresult = (event) => {
      const textarea = document.getElementById(textareaId);
      if (!textarea) return;

      // Rebuild the full spoken transcript (final + interim) from all results.
      // Iterating from 0 each time is necessary because earlier results can
      // become final in later events and their text must stay in place.
      let finalTranscript   = '';
      let interimTranscript = '';
      for (let i = 0; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += t;
        } else {
          interimTranscript += t;
        }
      }

      textarea.value = baseText + separator + finalTranscript + interimTranscript;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    };

    recognition.onerror = (event) => {
      _reset(btn, recording);
      recording = false;
      const msg = _errorMessage(event.error);
      if (msg) _showToast(container, msg);
    };

    recognition.onend = () => {
      recording = false;
      _reset(btn, true);
    };
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  function _buildRecognition() {
    const r = new SpeechRecognition();
    r.continuous      = true;   // keep listening until user clicks stop
    r.interimResults  = true;   // capture partial results for responsiveness
    r.lang            = navigator.language || 'en-US';
    r.maxAlternatives = 1;
    return r;
  }

  function _createButton() {
    const btn = document.createElement('button');
    btn.type      = 'button';
    btn.className = 'vi-btn';
    btn.title     = 'Click to speak';
    _setIcon(btn, _micIcon());
    return btn;
  }

  function _setIcon(btn, svgHtml) {
    btn.innerHTML = svgHtml;
  }

  function _reset(btn, wasRecording) {
    if (!wasRecording) return;
    btn.classList.remove('vi-btn--recording');
    btn.title = 'Click to speak';
    _setIcon(btn, _micIcon());
  }

  function _errorMessage(code) {
    const map = {
      'not-allowed'   : 'Microphone access denied. Allow mic permissions and try again.',
      'audio-capture' : 'No microphone detected.',
      'network'       : 'Voice recognition needs a network connection.',
      'aborted'       : null,   // user-initiated, no message needed
      'no-speech'     : null,   // silence, no message needed
    };
    return code in map ? map[code] : `Voice error: ${code}`;
  }

  /** Brief inline toast anchored below the container. Auto-dismisses. */
  function _showToast(anchor, message) {
    const existing = anchor.querySelector('.vi-toast');
    if (existing) existing.remove();

    const toast = document.createElement('span');
    toast.className   = 'vi-toast';
    toast.textContent = message;
    anchor.appendChild(toast);

    setTimeout(() => toast.remove(), 4000);
  }

  // ── SVG icons ─────────────────────────────────────────────────────────────

  function _micIcon() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
              viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8"  y1="23" x2="16" y2="23"/>
    </svg>`;
  }

  function _stopIcon() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
              viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="3"/>
    </svg>`;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  return { attach, isSupported };

})();
