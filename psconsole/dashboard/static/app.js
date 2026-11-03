/**
 * PlayStation Console OS Frontend Engine
 * Handles 60fps Carousel Navigation, HTML5 Gamepad API,
 * Web Audio FX Synthesis, Ambient Particle Wave, and REST sync.
 */

// Global State
let currentIndex = 0;
let cards = [];
let libraryGames = [];
let discState = { present: false, title: "No Disc Inserted", type: "OPTICAL", serial: "" };
let isAudioEnabled = false;
let audioMuted = false;

// DOM Elements
const carouselTrack = document.getElementById("carouselTrack");
const heroTitle = document.getElementById("heroTitle");
const heroDescription = document.getElementById("heroDescription");
const heroPlatformBadge = document.getElementById("heroPlatformBadge");
const heroSerialBadge = document.getElementById("heroSerialBadge");
const heroFormatBadge = document.getElementById("heroFormatBadge");
const heroPlayBtn = document.getElementById("heroPlayBtn");
const heroPlayBtnText = document.getElementById("heroPlayBtnText");
const heroPlayIcon = document.getElementById("heroPlayIcon");
const btnAudioToggle = document.getElementById("btnAudioToggle");
const btnExitGameplayReturn = document.getElementById("btnExitGameplayReturn");
const opticalDrivePill = document.getElementById("opticalDrivePill");
const statusDiscText = document.getElementById("statusDiscText");
const statusDiscIcon = document.getElementById("statusDiscIcon");
const systemClock = document.getElementById("systemClock");

// ==========================================================================
// 1. Web Audio API Synthesizer (Authentic Console Sound FX)
// ==========================================================================
let audioCtx = null;

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        isAudioEnabled = true;
    }
    if (audioCtx && audioCtx.state === "suspended") {
        audioCtx.resume();
    }
}

function playTickSound() {
    if (!audioCtx || audioMuted) return;
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(840, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(420, audioCtx.currentTime + 0.04);
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.04);
    } catch (e) {}
}

function playLaunchSound() {
    if (!audioCtx || audioMuted) return;
    try {
        const now = audioCtx.currentTime;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.18); // C6
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(now + 0.35);
    } catch (e) {}
}

function playTrophySound() {
    if (!audioCtx || audioMuted) return;
    try {
        const now = audioCtx.currentTime;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.setValueAtTime(880.00, now + 0.08); // A5
        osc.frequency.setValueAtTime(1174.66, now + 0.16); // D6
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(now + 0.4);
    } catch (e) {}
}

function toggleAudio() {
    initAudio();
    audioMuted = !audioMuted;
    if (btnAudioToggle) {
        if (audioMuted) {
            btnAudioToggle.classList.add("muted");
            btnAudioToggle.textContent = "🔇 Sound OFF";
        } else {
            btnAudioToggle.classList.remove("muted");
            btnAudioToggle.textContent = "🔊 Sound ON";
            playTrophySound();
        }
    }
}

// GameStation Toast Notification System
function showToast(message, type = "info", icon = null, duration = 3500) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `ps-toast ${type}`;

    const iconMap = {
        "info": "🎮",
        "warning": "⚠️",
        "error": "❌",
        "disc": "💿"
    };

    const iconChar = icon || iconMap[type] || "🎮";
    const titleText = type === "error" ? "System Alert" : (type === "warning" ? "Notice" : "GameStation");

    toast.innerHTML = `
        <div class="ps-toast-icon">${iconChar}</div>
        <div class="ps-toast-body">
            <div class="ps-toast-title">${titleText}</div>
            <div class="ps-toast-msg">${message}</div>
        </div>
    `;

    container.appendChild(toast);
    playTrophySound();

    requestAnimationFrame(() => {
        toast.classList.add("show");
    });

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

// Optical Disc Modal Handlers (Module Scope)
function openTestDiscModal() {
    initAudio();
    const modal = document.getElementById("testDiscModal");
    if (modal) modal.classList.add("visible");
}

function closeTestDiscModal() {
    initAudio();
    const modal = document.getElementById("testDiscModal");
    if (modal) modal.classList.remove("visible");
}

// ==========================================================================
// 2. Ambient Canvas: Flowing PlayStation Wave
// ==========================================================================
function initAmbientWave() {
    const canvas = document.getElementById("psWaveCanvas");
    const ctx = canvas.getContext("2d");

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    window.addEventListener("resize", resize);
    resize();

    let step = 0;
    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Render soft gradient waves
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, "rgba(0, 67, 156, 0.15)");
        gradient.addColorStop(0.5, "rgba(0, 112, 209, 0.08)");
        gradient.addColorStop(1, "rgba(6, 10, 20, 0.4)");

        ctx.fillStyle = gradient;
        ctx.beginPath();

        const waveHeight = canvas.height * 0.45;
        ctx.moveTo(0, canvas.height);

        for (let x = 0; x <= canvas.width; x += 20) {
            const y = Math.sin(x * 0.0025 + step) * 45 + Math.cos(x * 0.0015 + step * 0.8) * 30 + waveHeight;
            ctx.lineTo(x, y);
        }

        ctx.lineTo(canvas.width, canvas.height);
        ctx.closePath();
        ctx.fill();

        step += 0.012;
        requestAnimationFrame(render);
    }
    render();
}

// ==========================================================================
// 3. Carousel Navigation & Focus Management
// ==========================================================================
function updateSelection(newIndex, playAudio = true) {
    if (cards.length === 0) return;
    if (newIndex < 0) newIndex = 0;
    if (newIndex >= cards.length) newIndex = cards.length - 1;

    currentIndex = newIndex;
    if (playAudio) playTickSound();

    cards.forEach((card, idx) => {
        if (idx === currentIndex) {
            card.classList.add("active");
            card.focus();
        } else {
            card.classList.remove("active");
        }
    });

    // Translate track so active card is comfortably centered
    const cardWidth = 274; // 250px + 24px gap
    const targetOffset = -currentIndex * cardWidth;
    carouselTrack.style.transform = `translateX(${targetOffset}px)`;

    updateHeroDetails();
}

function updateHeroDetails() {
    if (currentIndex === 0) {
        // Physical Disc Slot
        if (discState.present) {
            heroPlatformBadge.textContent = discState.type;
            heroPlatformBadge.style.display = "inline-block";
            heroSerialBadge.textContent = discState.serial || "RETAIL DISC";
            heroSerialBadge.style.display = "inline-block";
            heroFormatBadge.textContent = "OPTICAL MEDIA";
            heroTitle.textContent = discState.title;
            heroDescription.textContent = `Physical original ${discState.type} game disc detected in optical drive. Press (✕) / (A) or tap Play Disc to boot.`;
            if (heroPlayBtnText) heroPlayBtnText.textContent = "Play Disc";
            if (heroPlayIcon) heroPlayIcon.textContent = "▶";
        } else {
            heroPlatformBadge.style.display = "none";
            heroSerialBadge.style.display = "none";
            heroFormatBadge.textContent = "OPTICAL DRIVE EMPTY";
            heroTitle.textContent = "Insert Game Disc";
            heroDescription.textContent = "Insert an original PlayStation or Xbox physical disc into your drive to start playing automatically.";
            if (heroPlayBtnText) heroPlayBtnText.textContent = "Open Disc Tray";
            if (heroPlayIcon) heroPlayIcon.textContent = "⏏";
        }
    } else {
        // Digital Game Slot
        const game = libraryGames[currentIndex - 1];
        if (game) {
            const sizeStr = game.file_size_mb >= 1024 
                ? (game.file_size_mb / 1024).toFixed(1) + " GB" 
                : game.file_size_mb + " MB";
            heroPlatformBadge.textContent = game.platform;
            heroPlatformBadge.style.display = "inline-block";
            heroSerialBadge.textContent = game.serial ? `[${game.serial}]` : `SIZE: ${sizeStr}`;
            heroSerialBadge.style.display = "inline-block";
            heroFormatBadge.textContent = `${game.format} FILE`;
            heroTitle.textContent = game.title;
            heroDescription.textContent = `Downloaded ${game.platform} title located in your GameStation library. Press (✕) / (A) or tap Play Game.`;
            if (heroPlayBtnText) heroPlayBtnText.textContent = "Play Game";
            if (heroPlayIcon) heroPlayIcon.textContent = "▶";
        }
    }
}

// ==========================================================================
// 4. Game Launch Execution
// ==========================================================================
async function launchSelectedGame() {
    playLaunchSound();

    if (currentIndex === 0) {
        // Launch Physical Disc
        if (!discState.present) {
            showToast("Opening Optical Disc Tray...", "info", "💿");
            openTestDiscModal();
            return;
        }
        try {
            showToast(`Loading ${discState.title}...`, "info", "💿");
            const res = await fetch("/api/launch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type: "disc" })
            });
            const data = await res.json();
            if (data.success) {
                setTimeout(fetchStatus, 150);
            } else {
                showToast(`Could not start disc: ${data.error || data.status}`, "error", "⚠️");
            }
        } catch (e) {
            console.error("Launch error:", e);
            showToast("Failed to communicate with console service.", "error", "⚠️");
        }
    } else {
        // Launch Digital Game
        const game = libraryGames[currentIndex - 1];
        if (!game) return;

        try {
            showToast(`Starting ${game.title}...`, "info", "🎮");
            const res = await fetch("/api/launch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    type: "digital",
                    platform: game.platform,
                    file_path: game.file_path,
                    title: game.title
                })
            });
            const data = await res.json();
            if (data.success) {
                setTimeout(fetchStatus, 150);
            } else {
                showToast(`Could not launch ${game.title}: ${data.error || data.status}`, "error", "⚠️");
            }
        } catch (e) {
            console.error("Launch error:", e);
            showToast("Failed to communicate with console service.", "error", "⚠️");
        }
    }
}

// Ingestion Modal DOM
const ingestionModal = document.getElementById("ingestionModal");
const ingestionPercent = document.getElementById("ingestionPercent");
const ingestionPlatform = document.getElementById("ingestionPlatform");
const ingestionTitle = document.getElementById("ingestionTitle");
const ingestionStep = document.getElementById("ingestionStep");
const ingestionProgressBar = document.getElementById("ingestionProgressBar");
const ingestionSvgRing = document.getElementById("ingestionSvgRing");
const ingestionBytes = document.getElementById("ingestionBytes");
const ingestionTime = document.getElementById("ingestionTime");
let wasIngesting = false;

// Gameplay Viewport DOM
const gameplayViewport = document.getElementById("gameplayViewport");
const gameplayPlatform = document.getElementById("gameplayPlatform");
const gameplayTitle = document.getElementById("gameplayTitle");
const gameplayLargeTitle = document.getElementById("gameplayLargeTitle");
const gameplayIconLarge = document.getElementById("gameplayIconLarge");
const btnExitGameplay = document.getElementById("btnExitGameplay");

// ==========================================================================
// 5. REST Polling & Library Sync
// ==========================================================================
async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();

        // Update Gameplay Session Viewport
        if (data.is_playing) {
            gameplayViewport.classList.add("active");
            gameplayTitle.textContent = data.active_game || "Console Game";
            gameplayLargeTitle.textContent = data.active_game || "Console Game";
            const plat = (data.active_platform || "CONSOLE").toUpperCase();
            gameplayPlatform.textContent = plat;
            const iconMap = {
                "PS1": "🕹️",
                "PS2": "🎮",
                "PS3": "⚡",
                "PS4": "🩸",
                "XBOX": "🟢",
                "XBOX360": "🟢",
                "PSP": "📱",
                "GAMECUBE": "🎲",
                "WII": "🏸",
                "DREAMCAST": "🌀",
                "N64": "🕹️",
                "SNES": "👾",
                "GBA": "🎮"
            };
            gameplayIconLarge.textContent = iconMap[plat] || "🎮";
        } else {
            gameplayViewport.classList.remove("active");
        }

        // Update Ingestion / Installation Modal
        if (data.ingestion && data.ingestion.is_active) {
            wasIngesting = true;
            ingestionModal.classList.add("visible");
            const pct = Math.max(0, Math.min(100, data.ingestion.progress_percent || 0));

            ingestionPercent.textContent = `${pct}%`;
            ingestionPlatform.textContent = data.ingestion.platform || "CONSOLE";
            ingestionTitle.textContent = data.ingestion.game_title || "Installing Disc...";
            ingestionStep.textContent = data.ingestion.current_step || "Reading optical sectors...";
            ingestionProgressBar.style.width = `${pct}%`;

            // Circumference of r=70 is ~439.82
            const offset = 439.82 * (1 - pct / 100);
            if (ingestionSvgRing) {
                ingestionSvgRing.style.strokeDashoffset = offset;
            }

            if (data.ingestion.bytes_read > 0) {
                const mb = (data.ingestion.bytes_read / (1024 * 1024)).toFixed(1);
                ingestionBytes.textContent = `${mb} MB transferred`;
            } else {
                ingestionBytes.textContent = "Streaming optical data...";
            }
            ingestionTime.textContent = `Processing • ${pct}%`;
        } else {
            if (wasIngesting) {
                wasIngesting = false;
                ingestionModal.classList.remove("visible");
                fetchLibrary(); // Refresh library with newly cached game
            }
        }

        // Update disc state
        if (data.disc && data.disc.present) {
            discState = data.disc;
            opticalDrivePill.classList.add("disc-ready");
            statusDiscIcon.textContent = "💿";
            statusDiscText.textContent = `${discState.type}: ${discState.title}`;

            // Update Disc Card
            document.getElementById("discCardBadge").textContent = discState.type;
            document.getElementById("discCardType").textContent = discState.serial || "DISC READY";
            document.getElementById("discCardTitle").textContent = discState.title;
            document.getElementById("discCardSubtitle").textContent = discState.requires_ingestion ? "Press (✕) to Install & Play" : "Press (✕) to Play Disc";
            document.getElementById("spinningDiscGraphic").classList.add("spinning");
        } else {
            discState = { present: false, title: "No Disc Inserted", type: "OPTICAL", serial: "" };
            opticalDrivePill.classList.remove("disc-ready");
            statusDiscIcon.textContent = "⏏";
            statusDiscText.textContent = "Optical Drive Empty";

            document.getElementById("discCardBadge").textContent = "DRIVE D:";
            document.getElementById("discCardType").textContent = "EMPTY";
            document.getElementById("discCardTitle").textContent = "No Disc Inserted";
            document.getElementById("discCardSubtitle").textContent = "Insert Game Disc";
            document.getElementById("spinningDiscGraphic").classList.remove("spinning");
        }

        if (currentIndex === 0) {
            updateHeroDetails();
        }
    } catch (e) {
        console.warn("Status fetch failed:", e);
    }
}

async function fetchLibrary() {
    try {
        const res = await fetch("/api/library");
        const data = await res.json();
        libraryGames = data.games || [];

        // Remove existing digital cards
        const existingDigitalCards = carouselTrack.querySelectorAll(".digital-card");
        existingDigitalCards.forEach(c => c.remove());

        // Append new digital cards
        libraryGames.forEach((game, idx) => {
            const card = document.createElement("div");
            card.className = "game-card digital-card";
            card.dataset.index = idx + 1;
            card.tabIndex = 0;

            const bgGradients = {
                "PS1": "linear-gradient(135deg, #00439C, #001A3D)",
                "PS2": "linear-gradient(135deg, #002244, #0B132B)",
                "PS3": "linear-gradient(135deg, #8A0000, #2B0505)",
                "PS4": "linear-gradient(135deg, #0070D1, #003666)",
                "PSP": "linear-gradient(135deg, #022047, #010D1F)",
                "GAMECUBE": "linear-gradient(135deg, #6A0DAD, #2E0854)",
                "WII": "linear-gradient(135deg, #009ACD, #004F6B)",
                "DREAMCAST": "linear-gradient(135deg, #E65100, #4A1B00)",
                "N64": "linear-gradient(135deg, #D32F2F, #4A0000)",
                "SNES": "linear-gradient(135deg, #7C4DFF, #311B92)",
                "GBA": "linear-gradient(135deg, #4A148C, #1A0033)",
                "XBOX": "linear-gradient(135deg, #107C10, #063806)",
                "XBOX360": "linear-gradient(135deg, #2E7D32, #0D3810)"
            };
            const grad = bgGradients[game.platform] || bgGradients["PS1"];

            const platformIcons = {
                "PS1": "🕹️",
                "PS2": "🎮",
                "PS3": "⚡",
                "PS4": "🩸",
                "PSP": "📱",
                "GAMECUBE": "🎲",
                "WII": "🏸",
                "DREAMCAST": "🌀",
                "N64": "🕹️",
                "SNES": "👾",
                "GBA": "🎮",
                "XBOX": "🟢",
                "XBOX360": "🟢"
            };
            const icon = platformIcons[game.platform] || "🎮";
            const sizeStr = game.file_size_mb >= 1024 
                ? (game.file_size_mb / 1024).toFixed(1) + " GB" 
                : game.file_size_mb + " MB";

            card.innerHTML = `
                <div class="poster-art" style="background: ${grad};"></div>
                <div class="card-inner">
                    <div class="card-header">
                        <span class="card-badge">${game.platform}</span>
                        <span class="card-type">${game.format}</span>
                    </div>
                    <div class="disc-visual">
                        <div style="font-size: 54px; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.5));">
                            ${icon}
                        </div>
                    </div>
                    <div class="card-footer">
                        <h3 class="card-title">${game.title}</h3>
                        <span class="card-subtitle">${sizeStr} • Installed</span>
                    </div>
                </div>
            `;

            card.addEventListener("click", () => {
                initAudio();
                const cardIndex = idx + 1;
                if (currentIndex === cardIndex) {
                    launchSelectedGame();
                } else {
                    updateSelection(cardIndex);
                }
            });

            carouselTrack.appendChild(card);
        });

        // Re-index cards array
        cards = Array.from(carouselTrack.querySelectorAll(".game-card"));
        updateSelection(currentIndex, false);
    } catch (e) {
        console.warn("Library fetch failed:", e);
    }
}

// ==========================================================================
// 6. Gamepad API Input Loop
// ==========================================================================
let lastNavTime = 0;
let buttonPressed = {};

function pollGamepad() {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    let gp = null;
    for (let i = 0; i < gamepads.length; i++) {
        if (gamepads[i]) {
            gp = gamepads[i];
            break;
        }
    }

    if (gp) {
        document.getElementById("controllerStatus").style.color = "#10B981";
        const now = Date.now();

        // D-Pad or Left Stick X navigation
        const axisX = gp.axes[0] || 0;
        const dpadLeft = gp.buttons[14] && gp.buttons[14].pressed;
        const dpadRight = gp.buttons[15] && gp.buttons[15].pressed;

        if (now - lastNavTime > 220) {
            if (axisX < -0.5 || dpadLeft) {
                initAudio();
                updateSelection(currentIndex - 1);
                lastNavTime = now;
            } else if (axisX > 0.5 || dpadRight) {
                initAudio();
                updateSelection(currentIndex + 1);
                lastNavTime = now;
            }
        }

        // Button 0: Cross / A -> Launch
        if (gp.buttons[0] && gp.buttons[0].pressed) {
            if (!buttonPressed[0]) {
                initAudio();
                launchSelectedGame();
                buttonPressed[0] = true;
            }
        } else {
            buttonPressed[0] = false;
        }

        // Button 1: Circle / B -> Exit Game, Cancel Ingestion, or Reset to Disc Slot
        if (gp.buttons[1] && gp.buttons[1].pressed) {
            if (!buttonPressed[1]) {
                initAudio();
                if (gameplayViewport && gameplayViewport.classList.contains("active")) {
                    fetch("/api/exit", { method: "POST" });
                    setTimeout(fetchStatus, 200);
                } else if (ingestionModal && ingestionModal.classList.contains("visible")) {
                    fetch("/api/ingestion/cancel", { method: "POST" });
                } else {
                    updateSelection(0);
                }
                buttonPressed[1] = true;
            }
        } else {
            buttonPressed[1] = false;
        }

        // Button 3: Triangle / Y -> Refresh Library
        if (gp.buttons[3] && gp.buttons[3].pressed) {
            if (!buttonPressed[3]) {
                initAudio();
                fetchLibrary();
                buttonPressed[3] = true;
            }
        } else {
            buttonPressed[3] = false;
        }
    }

    requestAnimationFrame(pollGamepad);
}

// ==========================================================================
// 7. Keyboard Navigation (Arrows, Enter, Escape)
// ==========================================================================
window.addEventListener("keydown", (e) => {
    initAudio();
    if (e.key === "ArrowLeft") {
        updateSelection(currentIndex - 1);
    } else if (e.key === "ArrowRight") {
        updateSelection(currentIndex + 1);
    } else if (e.key === "Enter" || e.key === " ") {
        launchSelectedGame();
    } else if (e.key === "Escape") {
        if (gameplayViewport && gameplayViewport.classList.contains("active")) {
            fetch("/api/exit", { method: "POST" });
            setTimeout(fetchStatus, 200);
        } else if (ingestionModal && ingestionModal.classList.contains("visible")) {
            fetch("/api/ingestion/cancel", { method: "POST" });
        } else {
            updateSelection(0);
        }
    } else if (e.key.toLowerCase() === "r") {
        fetchLibrary();
    }
});

// Update Clock
function updateClock() {
    const d = new Date();
    systemClock.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ==========================================================================
// Initialization & Touch / Remote Controls
// ==========================================================================
window.addEventListener("DOMContentLoaded", () => {
    initAmbientWave();
    cards = Array.from(carouselTrack.querySelectorAll(".game-card"));

    // Disc Card Click
    document.getElementById("discCard").addEventListener("click", () => {
        initAudio();
        if (currentIndex === 0) {
            launchSelectedGame();
        } else {
            updateSelection(0);
        }
    });

    // Touch Swipe Support for iPad / Mobile
    let touchStartX = 0;
    let touchStartY = 0;
    window.addEventListener("touchstart", (e) => {
        initAudio();
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    window.addEventListener("touchend", (e) => {
        const diffX = e.changedTouches[0].clientX - touchStartX;
        const diffY = e.changedTouches[0].clientY - touchStartY;
        if (Math.abs(diffX) > 45 && Math.abs(diffX) > Math.abs(diffY)) {
            if (diffX < 0) {
                updateSelection(currentIndex + 1);
            } else {
                updateSelection(currentIndex - 1);
            }
        }
    }, { passive: true });

    // Top Action Buttons
    if (btnAudioToggle) btnAudioToggle.addEventListener("click", toggleAudio);
    if (heroPlayBtn) {
        heroPlayBtn.addEventListener("click", () => {
            initAudio();
            if (currentIndex === 0 && !discState.present) {
                openTestDiscModal();
            } else {
                launchSelectedGame();
            }
        });
    }

    // Test Disc Modal Controls (iPad Friendly)
    const btnTestDisc = document.getElementById("btnTestDisc");
    const btnCloseTestDisc = document.getElementById("btnCloseTestDisc");
    const testDiscBackdrop = document.getElementById("testDiscBackdrop");

    if (btnTestDisc) btnTestDisc.addEventListener("click", openTestDiscModal);
    if (btnCloseTestDisc) btnCloseTestDisc.addEventListener("click", closeTestDiscModal);
    if (testDiscBackdrop) testDiscBackdrop.addEventListener("click", closeTestDiscModal);

    // Bottom Action Prompt Click Handlers (Touch Friendly)
    const btnPromptPlay = document.getElementById("btnPromptPlay");
    const btnPromptBack = document.getElementById("btnPromptBack");
    const btnPromptSquare = document.getElementById("btnPromptSquare");
    const btnPromptRefresh = document.getElementById("btnPromptRefresh");

    if (btnPromptPlay) btnPromptPlay.addEventListener("click", () => { initAudio(); launchSelectedGame(); });
    if (btnPromptBack) btnPromptBack.addEventListener("click", () => {
        initAudio();
        if (ingestionModal && ingestionModal.classList.contains("visible")) {
            fetch("/api/ingestion/cancel", { method: "POST" });
        } else {
            updateSelection(0);
        }
    });
    if (btnPromptSquare) btnPromptSquare.addEventListener("click", openTestDiscModal);
    if (btnPromptRefresh) btnPromptRefresh.addEventListener("click", () => { initAudio(); fetchLibrary(); });

    // Exit Gameplay Viewport
    if (btnExitGameplay) {
        btnExitGameplay.addEventListener("click", async () => {
            initAudio();
            await fetch("/api/exit", { method: "POST" });
            setTimeout(fetchStatus, 200);
        });
    }
    if (btnExitGameplayReturn) {
        btnExitGameplayReturn.addEventListener("click", async () => {
            initAudio();
            await fetch("/api/exit", { method: "POST" });
            setTimeout(fetchStatus, 200);
        });
    }

    // Disc Simulation Action Buttons
    document.querySelectorAll(".disc-sim-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            initAudio();
            const gen = btn.dataset.gen;
            const action = btn.dataset.action || "insert";
            closeTestDiscModal();

            try {
                await fetch("/api/test/insert_disc", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ generation: gen, action: action })
                });
                setTimeout(fetchStatus, 300);
            } catch (err) {
                console.warn("Disc simulation failed:", err);
            }
        });
    });

    updateClock();
    setInterval(updateClock, 10000);

    fetchStatus();
    setInterval(fetchStatus, 1500);

    fetchLibrary();

    // Start gamepad polling
    requestAnimationFrame(pollGamepad);
});
