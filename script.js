/* ============================================
   DIYA — AI VOICE ASSISTANT
   Frontend JavaScript v2.0 (Enhanced)
   ============================================ */

(function () {
    'use strict';

    // Auto-detect: local dev or Vercel deployment
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const API_BASE = isLocal ? 'http://localhost:5000/api' : '/api';

    // ========== DOM ==========
    const $ = s => document.querySelector(s);
    const $$ = s => document.querySelectorAll(s);

    const orbContainer = $('#orbContainer');
    const orbCore = $('#orbCore');
    const orbGlow = $('#orbGlow');
    const orbHint = $('#orbHint');
    const statusText = $('#statusText');
    const statusDot = $('#statusDot');
    const waveform = $('#waveform');
    const transcriptBox = $('#transcriptBox');
    const transcriptText = $('#transcriptText');
    const responseBox = $('#responseBox');
    const responseText = $('#responseText');
    const responseLabel = $('#responseLabel');
    const typingIndicator = $('#typingIndicator');
    const suggestionChips = $('#suggestionChips');
    const textInput = $('#textInput');
    const sendBtn = $('#sendBtn');
    const voiceInputBtn = $('#voiceInputBtn');
    const historyList = $('#historyList');
    const historyEmpty = $('#historyEmpty');
    const clearHistoryBtn = $('#clearHistoryBtn');
    const themeToggle = $('#themeToggle');
    const settingsBtn = $('#settingsBtn');
    const notesQuickBtn = $('#notesQuickBtn');
    const particles = $('#particles');
    const liveClock = $('#liveClock');
    const connectionStatus = $('#connectionStatus');
    const greetingText = $('#greetingText');
    const greetingSub = $('#greetingSub');

    // Panels
    const notesPanel = $('#notesPanel');
    const notesOverlay = $('#notesOverlay');
    const notesBody = $('#notesBody');
    const closeNotesBtn = $('#closeNotesBtn');
    const settingsPanel = $('#settingsPanel');
    const settingsOverlay = $('#settingsOverlay');
    const closeSettingsBtn = $('#closeSettingsBtn');
    const saveSettingsBtn = $('#saveSettingsBtn');

    // Settings Inputs
    const voiceSpeedInput = $('#voiceSpeed');
    const voicePitchInput = $('#voicePitch');
    const voiceSpeedVal = $('#voiceSpeedVal');
    const voicePitchVal = $('#voicePitchVal');
    const weatherCityInput = $('#weatherCity');
    const weatherApiKeyInput = $('#weatherApiKey');
    const assistantNameInput = $('#assistantName');

    // ========== STATE ==========
    let isListening = false;
    let isSpeaking = false;
    let passiveListening = false;
    let wakeWordActive = false;
    let recognition = null;
    let synth = window.speechSynthesis;
    let hasMessages = false;
    let backendAvailable = false;
    let assistantName = 'Diya';
    let restartTimer = null;
    let commandCount = 0;

    let settings = {
        voiceSpeed: 1,
        voicePitch: 1.2,
        weatherCity: 'Delhi',
        weatherApiKey: '',
        assistantName: 'Diya',
        theme: 'dark'
    };

    // ========== SOUND EFFECTS ==========
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    let audioCtx;

    function playTone(freq, duration, type = 'sine', volume = 0.08) {
        try {
            if (!audioCtx) audioCtx = new AudioCtx();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = type;
            osc.frequency.value = freq;
            gain.gain.value = volume;
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
            osc.connect(gain).connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + duration);
        } catch (e) { /* silent */ }
    }

    function sfxWakeWord() { playTone(880, 0.12); setTimeout(() => playTone(1100, 0.15), 100); }
    function sfxResponse() { playTone(660, 0.1, 'triangle', 0.05); }
    function sfxClick() { playTone(500, 0.06, 'sine', 0.04); }

    // ========== INIT ==========
    async function init() {
        loadLocalSettings();
        applyTheme();
        createParticles();
        setupClock();
        setupSpeechRecognition();
        setupEventListeners();
        await checkBackend();
        showGreeting();

        setTimeout(() => startPassiveListening(), 2500);
    }

    // ========== CLOCK ==========
    function setupClock() {
        function update() {
            const now = new Date();
            liveClock.textContent = now.toLocaleTimeString('en-IN', {
                hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
            });
        }
        update();
        setInterval(update, 1000);
    }

    // ========== GREETING ==========
    function showGreeting() {
        const hour = new Date().getHours();
        let g, emoji;
        if (hour < 12) { g = 'Good Morning'; emoji = '🌅'; }
        else if (hour < 17) { g = 'Good Afternoon'; emoji = '☀️'; }
        else { g = 'Good Evening'; emoji = '🌙'; }

        greetingText.textContent = `${emoji} ${g}!`;
        greetingSub.textContent = `I'm ${assistantName}, your AI assistant. How can I help?`;

        const mode = backendAvailable ? '🟢 Connected' : '🟡 Frontend mode';
        connectionStatus.textContent = mode;
        connectionStatus.classList.toggle('connected', backendAvailable);
    }

    // ========== BACKEND ==========
    async function checkBackend() {
        try {
            const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
            if (res.ok) {
                const data = await res.json();
                backendAvailable = true;
                assistantName = data.assistant || 'Diya';
                console.log(`✅ Connected to ${assistantName} v${data.version}`);
                await loadBackendSettings();
            }
        } catch (e) {
            backendAvailable = false;
            console.warn('⚠️ Backend unavailable');
        }
        connectionStatus.textContent = backendAvailable ? '🟢 Connected' : '🟡 Offline';
        connectionStatus.classList.toggle('connected', backendAvailable);
    }

    async function loadBackendSettings() {
        try {
            const res = await fetch(`${API_BASE}/settings`);
            if (res.ok) {
                const d = await res.json();
                assistantName = d.assistant_name || 'Diya';
                settings.weatherCity = d.weather_city || 'Delhi';
                settings.weatherApiKey = d.weather_api_key || '';
                settings.assistantName = assistantName;
                weatherCityInput.value = settings.weatherCity;
                weatherApiKeyInput.value = settings.weatherApiKey;
                assistantNameInput.value = settings.assistantName;
                responseLabel.textContent = assistantName;
            }
        } catch (e) { /* silent */ }
    }

    // ========== PARTICLES ==========
    function createParticles() {
        const colors = [
            'rgba(124,58,237,.25)', 'rgba(6,182,212,.25)',
            'rgba(236,72,153,.2)', 'rgba(245,158,11,.15)'
        ];
        for (let i = 0; i < 35; i++) {
            const p = document.createElement('div');
            p.classList.add('particle');
            p.style.left = Math.random() * 100 + '%';
            p.style.animationDuration = (10 + Math.random() * 15) + 's';
            p.style.animationDelay = (Math.random() * 12) + 's';
            const size = (2 + Math.random() * 3) + 'px';
            p.style.width = size;
            p.style.height = size;
            p.style.background = colors[Math.floor(Math.random() * colors.length)];
            particles.appendChild(p);
        }
    }

    // ========== SPEECH RECOGNITION WITH WAKE WORD ==========
    function setupSpeechRecognition() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            setStatus('⚠️ Speech not supported', 'error');
            return;
        }

        recognition = new SR();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-IN';
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            isListening = true;
            console.log('🎤 Recognition active');
        };

        recognition.onresult = (event) => {
            let final = '', interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) final += event.results[i][0].transcript;
                else interim += event.results[i][0].transcript;
            }

            const combined = (final || interim).toLowerCase().trim();

            // Wake word patterns
            const wakeWords = [
                'hey diya', 'hey dia', 'a diya', 'hey dea', 'he diya',
                'hey ' + assistantName.toLowerCase(),
                'ok diya', 'okay diya', 'hi diya'
            ];
            const hasWake = wakeWords.some(w => combined.includes(w));

            if (hasWake && !wakeWordActive) {
                wakeWordActive = true;
                sfxWakeWord();
                orbContainer.classList.add('listening');
                waveform.classList.add('active');
                setStatus('🎧 Yes? I\'m listening...', 'listening');
                orbHint.textContent = 'Listening...';

                if (final) {
                    let cmd = final.trim();
                    for (const w of wakeWords) {
                        const idx = cmd.toLowerCase().indexOf(w);
                        if (idx !== -1) { cmd = cmd.substring(idx + w.length).trim(); break; }
                    }
                    if (cmd.length > 1) handleWakeCommand(cmd);
                }
                return;
            }

            if (wakeWordActive) {
                showTranscript(final || interim);
                if (final) handleWakeCommand(final.trim());
                return;
            }

            // Manual mic click mode
            if (orbContainer.classList.contains('listening') && !passiveListening) {
                showTranscript(final || interim);
                if (final) sendCommand(final.trim());
            }
        };

        recognition.onerror = (event) => {
            console.warn('Speech error:', event.error);
            if (event.error === 'not-allowed') {
                setStatus('🔒 Mic access denied', 'error');
                passiveListening = false;
            }
        };

        recognition.onend = () => {
            isListening = false;
            if (passiveListening && !isSpeaking) {
                clearTimeout(restartTimer);
                restartTimer = setTimeout(() => {
                    if (passiveListening && !isSpeaking) {
                        try { recognition.start(); } catch (e) {
                            setTimeout(() => { if (passiveListening) startPassiveListening(); }, 2000);
                        }
                    }
                }, 500);
            }
        };
    }

    function handleWakeCommand(cmd) {
        wakeWordActive = false;
        orbContainer.classList.remove('listening');
        waveform.classList.remove('active');
        orbHint.textContent = 'Tap to speak';
        showTranscript(cmd);
        sendCommand(cmd);
    }

    function startPassiveListening() {
        if (!recognition || isSpeaking) return;
        passiveListening = true;
        wakeWordActive = false;
        setStatus(`🎤 Say <strong>"Hey ${assistantName}"</strong>`, 'passive');
        orbHint.textContent = `Say "Hey ${assistantName}"`;
        orbContainer.classList.remove('listening', 'speaking');
        try { recognition.start(); } catch (e) { /* already running */ }
    }

    function stopPassiveListening() {
        passiveListening = false;
        wakeWordActive = false;
        clearTimeout(restartTimer);
        try { recognition?.stop(); } catch (e) { /* */ }
        isListening = false;
        orbContainer.classList.remove('listening');
        waveform.classList.remove('active');
    }

    function startManualListening() {
        if (!recognition) return;
        if (isSpeaking) { synth.cancel(); isSpeaking = false; }
        passiveListening = false;
        wakeWordActive = false;
        clearTimeout(restartTimer);
        try { recognition.stop(); } catch (e) { /* */ }

        setTimeout(() => {
            sfxClick();
            orbContainer.classList.add('listening');
            waveform.classList.add('active');
            setStatus('🎧 Listening...', 'listening');
            orbHint.textContent = 'Listening...';
            try { recognition.start(); } catch (e) { /* */ }
        }, 300);
    }

    function stopManualListening() {
        wakeWordActive = false;
        orbContainer.classList.remove('listening');
        waveform.classList.remove('active');
        orbHint.textContent = 'Tap to speak';
        try { recognition?.stop(); } catch (e) { /* */ }
        setTimeout(() => { if (!isSpeaking) startPassiveListening(); }, 1000);
    }

    // ========== TTS (Female Voice) ==========
    function speak(text, callback) {
        if (!synth) return;
        synth.cancel();

        const utt = new SpeechSynthesisUtterance(text);
        utt.rate = settings.voiceSpeed;
        utt.pitch = settings.voicePitch;
        utt.lang = 'en-IN';

        const voices = synth.getVoices();
        let voice = null;
        const femaleKeys = ['zira', 'female', 'woman', 'girl', 'hazel', 'susan', 'jenny', 'aria', 'sara'];
        for (const k of femaleKeys) {
            voice = voices.find(v => v.lang.startsWith('en') && v.name.toLowerCase().includes(k));
            if (voice) break;
        }
        if (!voice) {
            const en = voices.filter(v => v.lang.startsWith('en'));
            voice = en.length > 1 ? en[1] : en[0];
        }
        if (voice) { utt.voice = voice; console.log('Voice:', voice.name); }
        if (settings.voicePitch <= 1) utt.pitch = 1.2;

        utt.onstart = () => {
            isSpeaking = true;
            passiveListening = false;
            clearTimeout(restartTimer);
            try { recognition?.stop(); } catch (e) { /* */ }
            orbContainer.classList.add('speaking');
            orbContainer.classList.remove('listening');
            setStatus(`🔊 ${assistantName} speaking...`, 'speaking');
            orbHint.textContent = 'Speaking...';
        };

        utt.onend = () => {
            isSpeaking = false;
            orbContainer.classList.remove('speaking');
            orbHint.textContent = 'Tap to speak';
            if (callback) callback();
            setTimeout(() => startPassiveListening(), 600);
        };

        utt.onerror = () => {
            isSpeaking = false;
            orbContainer.classList.remove('speaking');
            setTimeout(() => startPassiveListening(), 600);
        };

        synth.speak(utt);
    }

    // ========== SEND COMMAND ==========
    async function sendCommand(input) {
        if (!input) return;
        commandCount++;

        setStatus('🤔 Processing...', 'processing');
        orbContainer.classList.remove('listening');
        waveform.classList.remove('active');
        showTyping();

        // Stop passive listening during processing
        passiveListening = false;
        clearTimeout(restartTimer);
        try { recognition?.stop(); } catch (e) { /* */ }

        if (backendAvailable) {
            try {
                const res = await fetch(`${API_BASE}/command`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: input, use_server_tts: false })
                });

                if (res.ok) {
                    const data = await res.json();
                    hideTyping();
                    typeResponse(data.response, () => {
                        sfxResponse();
                        speak(data.response);
                    });
                    addToHistory(input, data.response);
                    showSuggestions(data.response, input);

                    // Handle special actions
                    if (data.action === 'show_notes') openNotes(data.data?.notes || []);
                    else if (data.action === 'note_saved') {
                        toast('📝 Note saved!', 'success');
                        if (notesPanel.classList.contains('active')) fetchAndShowNotes();
                    } else if (data.action === 'notes_cleared') renderNotes([]);
                    else if (data.action === 'play_youtube' && data.data) {
                        showYouTubePlayer(data.data);
                        toast(`🎵 Playing: ${data.data.title}`, 'success');
                    } else if (data.action === 'play_music' && data.data?.fallback) {
                        toast('🎵 Opening YouTube...', 'info');
                    } else if (data.action === 'open_website' && data.data?.url) {
                        window.open(data.data.url, '_blank');
                        toast(`🌐 Opening ${data.data.name || 'website'}...`, 'info');
                    }
                    return;
                }
            } catch (e) {
                console.warn('Backend error:', e);
            }
        }

        hideTyping();
        processClientSide(input);
    }

    // ========== YOUTUBE PLAYER ==========
    function showYouTubePlayer(data) {
        // Remove any existing player
        closeYouTubePlayer();

        const player = document.createElement('div');
        player.id = 'youtubePlayer';
        player.className = 'youtube-player';
        player.innerHTML = `
            <div class="yt-header">
                <div class="yt-info">
                    <div class="yt-title">🎵 ${data.title}</div>
                    <div class="yt-channel">${data.channel}</div>
                </div>
                <button class="btn-icon btn-sm yt-close" onclick="window.__closeYTPlayer()" title="Close">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="yt-embed">
                <iframe src="${data.embed}" frameborder="0" allow="autoplay; encrypted-media"
                    allowfullscreen></iframe>
            </div>
            ${data.results && data.results.length > 1 ? `
                <div class="yt-related">
                    <div class="yt-related-label">More results:</div>
                    <div class="yt-related-list">
                        ${data.results.slice(1).map(r => `
                            <button class="yt-result-chip" data-vid="${r.videoId}" data-title="${r.title.replace(/"/g, '&quot;')}" data-channel="${r.channel.replace(/"/g, '&quot;')}">
                                <img src="${r.thumbnail}" alt="" class="yt-thumb">
                                <div class="yt-result-info">
                                    <div class="yt-result-title">${r.title.length > 40 ? r.title.slice(0, 40) + '...' : r.title}</div>
                                    <div class="yt-result-ch">${r.channel}</div>
                                </div>
                            </button>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;

        // Insert after response box
        const voiceSection = document.querySelector('.voice-section');
        const responseBoxRef = document.getElementById('responseBox');
        if (responseBoxRef && responseBoxRef.nextSibling) {
            voiceSection.insertBefore(player, responseBoxRef.nextSibling);
        } else {
            voiceSection.appendChild(player);
        }

        // Bind related video clicks
        player.querySelectorAll('.yt-result-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const vid = chip.dataset.vid;
                const title = chip.dataset.title;
                const channel = chip.dataset.channel;
                const iframe = player.querySelector('iframe');
                iframe.src = `https://www.youtube.com/embed/${vid}?autoplay=1`;
                player.querySelector('.yt-title').textContent = `🎵 ${title}`;
                player.querySelector('.yt-channel').textContent = channel;
                toast(`🎵 Now playing: ${title}`, 'info');
            });
        });

        // Scroll into view
        setTimeout(() => player.scrollIntoView({ behavior: 'smooth', block: 'center' }), 300);
    }

    function closeYouTubePlayer() {
        const existing = document.getElementById('youtubePlayer');
        if (existing) existing.remove();
    }

    window.__closeYTPlayer = closeYouTubePlayer;

    // ========== TYPING ANIMATION ==========
    function showTyping() {
        responseBox.classList.add('visible');
        responseText.textContent = '';
        typingIndicator.style.display = 'flex';
    }

    function hideTyping() {
        typingIndicator.style.display = 'none';
    }

    function typeResponse(text, callback) {
        responseBox.classList.add('visible');
        responseText.textContent = '';
        typingIndicator.style.display = 'none';
        const clean = text.replace(/\s{2,}/g, ' ').trim();
        let i = 0;
        const speed = Math.max(12, 40 - clean.length / 5);
        function type() {
            if (i < clean.length) {
                responseText.textContent += clean[i];
                i++;
                setTimeout(type, speed);
            } else {
                if (callback) callback();
            }
        }
        type();
    }

    // ========== SMART SUGGESTIONS ==========
    function showSuggestions(response, input) {
        const lower = input.toLowerCase();
        const suggestions = [];

        if (lower.includes('weather')) {
            suggestions.push('Open weather forecast', 'What\'s the temperature tomorrow?');
        } else if (lower.includes('time')) {
            suggestions.push('What\'s today\'s date?', 'Set a reminder');
        } else if (lower.includes('joke')) {
            suggestions.push('Tell me another joke', 'Tell me a fun fact');
        } else if (lower.includes('note')) {
            suggestions.push('Show my notes', 'Clear all notes');
        } else if (lower.includes('music') || lower.includes('play')) {
            suggestions.push('Play Bollywood music', 'Stop music');
        } else {
            const defaults = ['Tell me a joke', 'What\'s the weather?', 'Open YouTube', 'What can you do?'];
            suggestions.push(...defaults.slice(0, 3));
        }

        suggestionChips.innerHTML = suggestions.map(s =>
            `<button class="chip" data-cmd="${s}">${s}</button>`
        ).join('');

        suggestionChips.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const cmd = chip.dataset.cmd;
                showTranscript(cmd);
                sendCommand(cmd);
                suggestionChips.innerHTML = '';
            });
        });
    }

    // ========== CLIENT-SIDE FALLBACK ==========
    function processClientSide(input) {
        const lower = input.toLowerCase().trim();

        // Wake word
        if (lower.startsWith('hey diya') || lower.startsWith('hey ' + assistantName.toLowerCase())) {
            const after = input.substring(input.indexOf(' ', 4) + 1).trim();
            if (after && after.toLowerCase() !== assistantName.toLowerCase()) {
                sendCommand(after);
                return;
            }
            respond("Hey! I'm here. What do you need?", input);
            return;
        }

        // Time
        if (lower.includes('time') && (lower.includes('what') || lower.includes('tell'))) {
            const t = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
            respond(`It's currently ${t}.`, input);
            return;
        }

        // Date
        if (lower.includes('date') || lower.includes('today')) {
            const d = new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            respond(`Today is ${d}.`, input);
            return;
        }

        // Websites
        const sites = {
            'youtube': 'https://www.youtube.com', 'gmail': 'https://mail.google.com',
            'google': 'https://www.google.com', 'github': 'https://github.com',
            'instagram': 'https://www.instagram.com', 'whatsapp': 'https://web.whatsapp.com',
            'twitter': 'https://twitter.com', 'linkedin': 'https://www.linkedin.com',
            'facebook': 'https://www.facebook.com', 'spotify': 'https://open.spotify.com',
            'netflix': 'https://www.netflix.com', 'reddit': 'https://www.reddit.com'
        };
        for (const [key, url] of Object.entries(sites)) {
            if (lower.includes('open ' + key)) {
                window.open(url, '_blank');
                respond(`Opening ${key.charAt(0).toUpperCase() + key.slice(1)} for you! 🌐`, input);
                return;
            }
        }

        // Search
        if (lower.startsWith('search') || lower.startsWith('google')) {
            const q = input.replace(/^(search|google)\s*/i, '').trim();
            if (q) {
                window.open(`https://www.google.com/search?q=${encodeURIComponent(q)}`, '_blank');
                respond(`Searching for "${q}" 🔍`, input);
                return;
            }
        }

        // Greetings
        if (/^(hi|hello|hey|namaste|hola)/i.test(lower)) {
            const hour = new Date().getHours();
            const g = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
            respond(`${g}! I'm ${assistantName}. How can I help you today? 😊`, input);
            return;
        }

        // Joke
        if (lower.includes('joke')) {
            const jokes = [
                "Why don't scientists trust atoms? Because they make up everything! 😄",
                "I told my computer I needed a break, and it said 'No problem, I'll crash!' 💻",
                "Why did the developer go broke? Because he used up all his cache! 🤣",
                "What's a computer's favourite snack? Microchips! 🍟",
                "Why was the JavaScript developer sad? Because he didn't Node how to Express himself! 😂"
            ];
            respond(jokes[Math.floor(Math.random() * jokes.length)], input);
            return;
        }

        // Default: Google search
        window.open(`https://www.google.com/search?q=${encodeURIComponent(input)}`, '_blank');
        respond("I searched Google for you! 🔍", input);
    }

    function respond(text, userInput) {
        typeResponse(text, () => {
            sfxResponse();
            speak(text);
        });
        addToHistory(userInput || '', text);
        showSuggestions(text, userInput);
    }

    // ========== NOTES ==========
    async function fetchAndShowNotes() {
        if (backendAvailable) {
            try {
                const res = await fetch(`${API_BASE}/notes`);
                if (res.ok) { renderNotes(await res.json()); return; }
            } catch (e) { /* */ }
        }
        renderNotes([]);
    }

    function openNotes(notes) {
        notesPanel.classList.add('active');
        notesOverlay.classList.add('active');
        if (notes) renderNotes(notes); else fetchAndShowNotes();
    }

    function renderNotes(notes) {
        if (!notes || !notes.length) {
            notesBody.innerHTML = '<p class="empty-state">No notes yet. Say "Take a note" to add one!</p>';
            return;
        }
        notesBody.innerHTML = notes.map(n => `
            <div class="note-card" data-id="${n.id}">
                <div class="note-time">${n.time}</div>
                <div class="note-content">${n.content}</div>
                <button class="note-del" onclick="window.__deleteNote(${n.id})" title="Delete">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
        `).join('');
    }

    window.__deleteNote = async function (id) {
        if (backendAvailable) {
            try { await fetch(`${API_BASE}/notes/${id}`, { method: 'DELETE' }); } catch (e) { /* */ }
        }
        fetchAndShowNotes();
        toast('🗑 Note deleted', 'info');
    };

    function closeNotes() {
        notesPanel.classList.remove('active');
        notesOverlay.classList.remove('active');
    }

    // ========== SETTINGS ==========
    function loadLocalSettings() {
        const saved = localStorage.getItem('diya_settings');
        if (saved) settings = { ...settings, ...JSON.parse(saved) };
        voiceSpeedInput.value = settings.voiceSpeed;
        voicePitchInput.value = settings.voicePitch;
        voiceSpeedVal.textContent = settings.voiceSpeed + 'x';
        voicePitchVal.textContent = settings.voicePitch;
        weatherCityInput.value = settings.weatherCity;
        weatherApiKeyInput.value = settings.weatherApiKey;
        assistantNameInput.value = settings.assistantName;
        assistantName = settings.assistantName;
    }

    async function saveAllSettings() {
        settings.voiceSpeed = parseFloat(voiceSpeedInput.value);
        settings.voicePitch = parseFloat(voicePitchInput.value);
        settings.weatherCity = weatherCityInput.value.trim() || 'Delhi';
        settings.weatherApiKey = weatherApiKeyInput.value.trim();
        settings.assistantName = assistantNameInput.value.trim() || 'Diya';
        assistantName = settings.assistantName;
        responseLabel.textContent = assistantName;

        localStorage.setItem('diya_settings', JSON.stringify(settings));

        if (backendAvailable) {
            try {
                await fetch(`${API_BASE}/settings`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        assistant_name: settings.assistantName,
                        weather_city: settings.weatherCity,
                        weather_api_key: settings.weatherApiKey,
                        voice_speed: Math.round(settings.voiceSpeed * 150)
                    })
                });
            } catch (e) { /* */ }
        }

        closeSettings();
        toast('⚙️ Settings saved!', 'success');
        speak(`Settings saved! My name is now ${assistantName}.`);
    }

    function openSettings() {
        settingsPanel.classList.add('active');
        settingsOverlay.classList.add('active');
    }
    function closeSettings() {
        settingsPanel.classList.remove('active');
        settingsOverlay.classList.remove('active');
    }

    // ========== THEME ==========
    function applyTheme() {
        const isLight = settings.theme === 'light';
        document.body.classList.toggle('light', isLight);
        const moonIcon = themeToggle.querySelector('.icon-moon');
        const sunIcon = themeToggle.querySelector('.icon-sun');
        if (moonIcon && sunIcon) {
            moonIcon.style.display = isLight ? 'none' : 'block';
            sunIcon.style.display = isLight ? 'block' : 'none';
        }
    }

    function toggleTheme() {
        settings.theme = settings.theme === 'dark' ? 'light' : 'dark';
        applyTheme();
        localStorage.setItem('diya_settings', JSON.stringify(settings));
        sfxClick();
    }

    // ========== UI HELPERS ==========
    function setStatus(html, state = '') {
        statusText.innerHTML = html;
        statusDot.className = 'status-dot';
        if (state) statusDot.classList.add(state);
    }

    function showTranscript(text) {
        transcriptText.textContent = text;
        transcriptBox.classList.add('visible');
        suggestionChips.innerHTML = '';
    }

    function addToHistory(userText, botText) {
        if (!hasMessages) {
            historyList.innerHTML = '';
            hasMessages = true;
        }
        if (historyEmpty) historyEmpty.remove();

        const time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
        const item = document.createElement('div');
        item.classList.add('history-item');
        item.innerHTML = `
            <div class="h-user">${userText || 'Text input'}</div>
            <div class="h-bot">${botText}</div>
            <div class="h-time">${time}</div>
        `;
        historyList.prepend(item);
    }

    function clearHistory() {
        historyList.innerHTML = `
            <div class="history-empty" id="historyEmpty">
                <div class="empty-icon">💬</div>
                <p>Start a conversation!</p>
                <small>Say "Hey Diya" or click the mic</small>
            </div>
        `;
        hasMessages = false;
        sfxClick();
        toast('🗑 History cleared', 'info');
    }

    // ========== TOAST NOTIFICATIONS ==========
    function toast(text, type = 'info') {
        const container = $('#toastContainer');
        const el = document.createElement('div');
        el.classList.add('toast', type);
        el.textContent = text;
        container.appendChild(el);
        setTimeout(() => {
            el.style.animation = 'toastOut .3s forwards';
            setTimeout(() => el.remove(), 300);
        }, 3000);
    }

    // ========== FEATURE CARD CLICK ==========
    function handleFeatureClick(feature) {
        sfxClick();
        const card = document.querySelector(`[data-feature="${feature}"]`);
        if (card) { card.classList.add('active'); setTimeout(() => card.classList.remove('active'), 1200); }

        switch (feature) {
            case 'weather': sendCommand('What is the weather today?'); break;
            case 'time': sendCommand('What is the time?'); break;
            case 'wiki': sendCommand('Tell me about artificial intelligence'); break;
            case 'joke': sendCommand('Tell me a joke'); break;
            case 'system': sendCommand('System info'); break;
            case 'help': sendCommand('What can you do?'); break;
            case 'search':
                textInput.focus();
                textInput.placeholder = 'Type what to search...';
                break;
            case 'music':
                textInput.focus();
                textInput.placeholder = 'Which song to play...';
                break;
            case 'calculate':
                textInput.focus();
                textInput.placeholder = 'Enter calculation, e.g. 25 * 4';
                break;
            case 'website': sendCommand('What websites can you open?'); break;
            case 'notes': openNotes(); break;
            case 'apps': sendCommand('Open calculator'); break;
        }
    }

    // ========== EVENT LISTENERS ==========
    function setupEventListeners() {
        // Orb click
        orbContainer.addEventListener('click', () => {
            if (orbContainer.classList.contains('listening')) stopManualListening();
            else startManualListening();
        });

        // Text input
        textInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && textInput.value.trim()) {
                const val = textInput.value.trim();
                showTranscript(val);
                sendCommand(val);
                textInput.value = '';
                textInput.placeholder = 'Type a command or question...';
            }
        });

        sendBtn.addEventListener('click', () => {
            if (textInput.value.trim()) {
                const val = textInput.value.trim();
                showTranscript(val);
                sendCommand(val);
                textInput.value = '';
            }
        });

        voiceInputBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            startManualListening();
        });

        // Quick chips
        $$('.quick-chips .chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const cmd = chip.dataset.cmd;
                showTranscript(cmd);
                sendCommand(cmd);
            });
        });

        // Feature cards
        $$('.feature-card').forEach(card => {
            card.addEventListener('click', () => handleFeatureClick(card.dataset.feature));
        });

        // History
        clearHistoryBtn.addEventListener('click', clearHistory);

        // Theme
        themeToggle.addEventListener('click', toggleTheme);

        // Settings
        settingsBtn.addEventListener('click', openSettings);
        closeSettingsBtn.addEventListener('click', closeSettings);
        settingsOverlay.addEventListener('click', closeSettings);
        saveSettingsBtn.addEventListener('click', saveAllSettings);

        voiceSpeedInput.addEventListener('input', () => {
            voiceSpeedVal.textContent = voiceSpeedInput.value + 'x';
        });
        voicePitchInput.addEventListener('input', () => {
            voicePitchVal.textContent = voicePitchInput.value;
        });

        // Notes
        notesQuickBtn.addEventListener('click', () => openNotes());
        closeNotesBtn.addEventListener('click', closeNotes);
        notesOverlay.addEventListener('click', closeNotes);

        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeSettings();
                closeNotes();
            }
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                textInput.focus();
            }
        });

        // Voices
        if (synth) synth.onvoiceschanged = () => synth.getVoices();
    }

    // ========== START ==========
    document.addEventListener('DOMContentLoaded', init);

})();
