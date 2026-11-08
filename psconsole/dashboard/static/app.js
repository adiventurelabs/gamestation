/**
 * PlayStation Console OS Frontend Engine
 * Handles 60fps Carousel Navigation, HTML5 Gamepad API,
 * Web Audio FX Synthesis, Ambient Particle Wave, and REST sync.
 */

// Global State
let isGameActive = false;
let gameLaunchTimestamp = 0;
let currentIndex = 0;
let cards = [];
let allLibraryGames = [];
let filteredGames = [];
let activeFilter = "all";
let searchQuery = "";
let discState = { present: false, title: "No Disc Inserted", type: "OPTICAL", serial: "" };
let isAudioEnabled = false;
let audioMuted = false;

// DOM Elements
const carouselTrack = document.getElementById("carouselTrack");
const heroTitle = document.getElementById("heroTitle");
const heroDescription = document.getElementById("heroDescription");
const heroPlatformBadge = document.getElementById("heroPlatformBadge");
const heroPlayersBadge = document.getElementById("heroPlayersBadge");
const heroGenreBadge = document.getElementById("heroGenreBadge");
const heroYearBadge = document.getElementById("heroYearBadge");
const heroRatingBadge = document.getElementById("heroRatingBadge");
const heroDevRow = document.getElementById("heroDevRow");
const heroDeveloper = document.getElementById("heroDeveloper");
const heroPublisher = document.getElementById("heroPublisher");
const heroPosterImg = document.getElementById("heroPosterImg");
const heroPosterFallback = document.getElementById("heroPosterFallback");
const heroPlayBtn = document.getElementById("heroPlayBtn");
const heroPlayBtnText = document.getElementById("heroPlayBtnText");
const heroPlayIcon = document.getElementById("heroPlayIcon");
const btnAudioToggle = document.getElementById("btnAudioToggle");
const btnExitGameplayReturn = document.getElementById("btnExitGameplayReturn");
const opticalDrivePill = document.getElementById("opticalDrivePill");
const statusDiscText = document.getElementById("statusDiscText");
const statusDiscIcon = document.getElementById("statusDiscIcon");
const systemClock = document.getElementById("systemClock");
const categoryPillsContainer = document.getElementById("categoryPills");
const searchInput = document.getElementById("searchInput");
const searchClearBtn = document.getElementById("searchClearBtn");
const countAll = document.getElementById("countAll");
const countMulti = document.getElementById("countMulti");

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

function isMultiplayerGame(game) {
    if (!game) return false;
    const str = `${game.players || ''} ${game.title || ''}`.toLowerCase();
    return str.includes("2") || str.includes("3") || str.includes("4") || 
           str.includes("multi") || str.includes("co-op") || str.includes("versus") || 
           str.includes("rumble") || str.includes("split-screen") || str.includes("free-for-all");
}

function updateHeroDetails() {
    if (currentIndex === 0) {
        // Physical Disc Slot
        if (discState.present) {
            if (heroPlatformBadge) {
                heroPlatformBadge.textContent = discState.type;
                heroPlatformBadge.style.display = "inline-block";
            }
            if (heroPlayersBadge) {
                heroPlayersBadge.textContent = "👥 1-4 Players";
                heroPlayersBadge.style.display = "inline-block";
            }
            if (heroGenreBadge) {
                heroGenreBadge.textContent = "OPTICAL DISC";
                heroGenreBadge.style.display = "inline-block";
            }
            if (heroYearBadge) {
                heroYearBadge.textContent = "RETAIL";
                heroYearBadge.style.display = "inline-block";
            }
            if (heroRatingBadge) {
                heroRatingBadge.textContent = discState.serial || "ORIGINAL DISC";
                heroRatingBadge.style.display = "inline-block";
            }
            if (heroDevRow) heroDevRow.style.display = "none";
            if (heroTitle) heroTitle.textContent = discState.title;
            if (heroDescription) {
                heroDescription.textContent = `Physical original ${discState.type} game disc detected in optical drive. Press (A) / (✕) to boot.`;
            }
            if (heroPlayBtnText) heroPlayBtnText.textContent = "Play Disc";
            if (heroPlayIcon) heroPlayIcon.textContent = "▶";
            if (heroPosterImg) heroPosterImg.style.display = "none";
            if (heroPosterFallback) heroPosterFallback.style.display = "flex";
        } else {
            if (heroPlatformBadge) heroPlatformBadge.style.display = "none";
            if (heroPlayersBadge) heroPlayersBadge.style.display = "none";
            if (heroGenreBadge) heroGenreBadge.style.display = "none";
            if (heroYearBadge) heroYearBadge.style.display = "none";
            if (heroRatingBadge) heroRatingBadge.style.display = "none";
            if (heroDevRow) heroDevRow.style.display = "none";
            if (heroTitle) heroTitle.textContent = "Insert Game Disc";
            if (heroDescription) {
                heroDescription.textContent = "Insert an original PlayStation or Xbox physical disc into your drive to start playing automatically, or pick a digital game from your library.";
            }
            if (heroPlayBtnText) heroPlayBtnText.textContent = "Open Disc Tray";
            if (heroPlayIcon) heroPlayIcon.textContent = "⏏";
            if (heroPosterImg) heroPosterImg.style.display = "none";
            if (heroPosterFallback) heroPosterFallback.style.display = "flex";
        }
    } else {
        // Digital Game Slot
        const game = filteredGames[currentIndex - 1];
        if (game) {
            const sizeStr = game.file_size_mb >= 1024 
                ? (game.file_size_mb / 1024).toFixed(1) + " GB" 
                : game.file_size_mb + " MB";
            if (heroPlatformBadge) {
                heroPlatformBadge.textContent = game.platform;
                heroPlatformBadge.style.display = "inline-block";
            }
            if (heroPlayersBadge) {
                heroPlayersBadge.textContent = game.players ? `👥 ${game.players}` : "👥 1 Player";
                heroPlayersBadge.style.display = "inline-block";
            }
            if (heroGenreBadge) {
                heroGenreBadge.textContent = game.genre ? game.genre.toUpperCase() : "CONSOLE GAME";
                heroGenreBadge.style.display = "inline-block";
            }
            if (heroYearBadge) {
                heroYearBadge.textContent = game.release_year || "CLASSIC";
                heroYearBadge.style.display = "inline-block";
            }
            if (heroRatingBadge) {
                heroRatingBadge.textContent = game.rating || "ESRB";
                heroRatingBadge.style.display = "inline-block";
            }
            if (heroDevRow) {
                if (game.developer || game.publisher) {
                    heroDevRow.style.display = "flex";
                    if (heroDeveloper) heroDeveloper.textContent = game.developer || "Original Developer";
                    if (heroPublisher) heroPublisher.textContent = game.publisher || "Publisher";
                } else {
                    heroDevRow.style.display = "none";
                }
            }
            if (heroTitle) heroTitle.textContent = game.title;
            if (heroDescription) {
                heroDescription.textContent = game.description || `Installed ${game.platform} title (${sizeStr}) located in your GameStation library. Press (A) / (✕) to launch.`;
            }
            if (heroPlayBtnText) heroPlayBtnText.textContent = "Play Game";
            if (heroPlayIcon) heroPlayIcon.textContent = "▶";

            // Cover Art Poster
            if (heroPosterImg && game.cover_art) {
                heroPosterImg.src = game.cover_art;
                heroPosterImg.style.display = "block";
                if (heroPosterFallback) heroPosterFallback.style.display = "none";
            } else {
                if (heroPosterImg) heroPosterImg.style.display = "none";
                if (heroPosterFallback) heroPosterFallback.style.display = "flex";
            }
        }
    }
}

// ==========================================================================
// 4. Game Launch Execution
// ==========================================================================
async function launchSelectedGame() {
    if (isGameActive || (gameplayViewport && gameplayViewport.classList.contains("active"))) {
        console.warn("Launch blocked: Active gameplay session currently in progress.");
        return;
    }
    playLaunchSound();
    isGameActive = true;
    gameLaunchTimestamp = Date.now();

    if (currentIndex === 0) {
        // Launch Physical Disc
        if (!discState.present) {
            showToast("Opening Optical Disc Tray...", "info", "💿");
            openTestDiscModal();
            return;
        }
        try {
            isGameActive = true;
            showToast(`Loading ${discState.title}...`, "info", "💿");
            const res = await fetch("/api/launch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type: "disc" })
            });
            const data = await res.json();
            if (data.success) {
                isGameActive = true;
                setTimeout(fetchStatus, 150);
            } else {
                isGameActive = false;
                showToast(`Could not start disc: ${data.error || data.status}`, "error", "⚠️");
            }
        } catch (e) {
            isGameActive = false;
            console.error("Launch error:", e);
            showToast("Failed to communicate with console service.", "error", "⚠️");
        }
    } else {
        // Launch Digital Game
        const game = filteredGames[currentIndex - 1];
        if (!game) return;

        try {
            isGameActive = true;
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
                isGameActive = true;
                setTimeout(fetchStatus, 150);
            } else {
                isGameActive = false;
                showToast(`Could not launch ${game.title}: ${data.error || data.status}`, "error", "⚠️");
            }
        } catch (e) {
            isGameActive = false;
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
        const now = Date.now();
        const inLaunchGracePeriod = (now - gameLaunchTimestamp) < 8000;

        if (data.is_playing) {
            isGameActive = true;
        } else if (!inLaunchGracePeriod) {
            isGameActive = false;
        }

        if (isGameActive) {
            gameplayViewport.classList.add("active");
            gameplayTitle.textContent = data.active_game || gameplayTitle.textContent || "Console Game";
            gameplayLargeTitle.textContent = data.active_game || gameplayLargeTitle.textContent || "Console Game";
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
        allLibraryGames = data.games || [];

        if (countAll) countAll.textContent = allLibraryGames.length;
        if (countMulti) {
            const multiCount = allLibraryGames.filter(g => isMultiplayerGame(g)).length;
            countMulti.textContent = multiCount;
        }

        applyFiltersAndRender(true);
    } catch (e) {
        console.warn("Library fetch failed:", e);
    }
}

function applyFiltersAndRender(maintainFocus = true) {
    const q = searchQuery.trim().toLowerCase();

    filteredGames = allLibraryGames.filter(game => {
        // Platform / category filter
        if (activeFilter === "multiplayer") {
            if (!isMultiplayerGame(game)) return false;
        } else if (activeFilter === "RETRO") {
            const retro = ["GAMECUBE", "WII", "DREAMCAST", "N64", "SNES", "GBA", "PSP"];
            if (!retro.includes(game.platform)) return false;
        } else if (activeFilter !== "all") {
            if (game.platform !== activeFilter) return false;
        }

        // Search text query
        if (q) {
            const haystack = `${game.title} ${game.platform} ${game.genre || ''} ${game.players || ''} ${game.developer || ''} ${game.publisher || ''}`.toLowerCase();
            if (!haystack.includes(q)) return false;
        }

        return true;
    });

    renderCarouselTrack(maintainFocus);
}

function renderCarouselTrack(maintainFocus = true) {
    // Keep disc card (index 0) and remove all existing digital cards
    const existingDigitalCards = carouselTrack.querySelectorAll(".digital-card");
    existingDigitalCards.forEach(c => c.remove());

    filteredGames.forEach((game, idx) => {
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
            "PS1": "🕹️", "PS2": "🎮", "PS3": "⚡", "PS4": "🩸", "PSP": "📱",
            "GAMECUBE": "🎲", "WII": "🏸", "DREAMCAST": "🌀", "N64": "🕹️",
            "SNES": "👾", "GBA": "🎮", "XBOX": "🟢", "XBOX360": "🟢"
        };
        const icon = platformIcons[game.platform] || "🎮";

        const sizeStr = game.file_size_mb >= 1024 
            ? (game.file_size_mb / 1024).toFixed(1) + " GB" 
            : game.file_size_mb + " MB";

        const isMulti = isMultiplayerGame(game);
        const multiBadgeHtml = isMulti 
            ? `<span class="multi-tag">👥 2-4P</span>`
            : `<span class="card-type">${game.format}</span>`;

        const posterStyle = game.cover_art 
            ? `background-image: url('${game.cover_art}');`
            : `background: ${grad};`;

        const centerVisual = game.cover_art 
            ? `<div style="height: 120px;"></div>`
            : `<div style="font-size: 54px; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.5));">${icon}</div>`;

        const genreLabel = game.genre ? game.genre.split('/')[0].trim() : game.platform;

        card.innerHTML = `
            <div class="poster-art" style="${posterStyle}"></div>
            <div class="card-inner">
                <div class="card-header">
                    <span class="card-badge platform-${game.platform.toLowerCase()}">${game.platform}</span>
                    ${multiBadgeHtml}
                </div>
                <div class="disc-visual">
                    ${centerVisual}
                </div>
                <div class="card-footer">
                    <h3 class="card-title">${game.title}</h3>
                    <span class="card-subtitle">${genreLabel} • ${sizeStr}</span>
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
    if (maintainFocus) {
        if (currentIndex >= cards.length) currentIndex = Math.max(0, cards.length - 1);
        updateSelection(currentIndex, false);
    } else {
        updateSelection(0, false);
    }
}

function cycleCategory(delta) {
    if (!categoryPillsContainer) return;
    const pills = Array.from(categoryPillsContainer.querySelectorAll(".cat-pill"));
    if (pills.length === 0) return;
    let currIdx = pills.findIndex(p => p.classList.contains("active"));
    if (currIdx < 0) currIdx = 0;
    let nextIdx = currIdx + delta;
    if (nextIdx < 0) nextIdx = pills.length - 1;
    if (nextIdx >= pills.length) nextIdx = 0;
    pills.forEach(p => p.classList.remove("active"));
    pills[nextIdx].classList.add("active");
    activeFilter = pills[nextIdx].dataset.filter || "all";
    initAudio();
    playTickSound();
    applyFiltersAndRender(false);
}

// ==========================================================================
// 6. Gamepad API Input Loop (Dual Xbox Controller Support)
// ==========================================================================
let lastNavTime = 0;
let buttonPressed = {};

function pollGamepad() {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    let anyConnected = false;
    for (let i = 0; i < gamepads.length; i++) {
        if (gamepads[i]) anyConnected = true;
    }
    updateControllerStatus(anyConnected);

    // CRITICAL: When a game is active or browser window is in the background,
    // suppress all UI navigation and button presses so gameplay inputs
    // go exclusively to the running emulator and never trigger menu launches!
    const isViewportActive = gameplayViewport && gameplayViewport.classList.contains("active");
    if (isGameActive || isViewportActive || document.hidden || (typeof document.hasFocus === "function" && !document.hasFocus())) {
        requestAnimationFrame(pollGamepad);
        return;
    }

    // Check all connected gamepads (Player 1, Player 2, etc.)
    for (let i = 0; i < gamepads.length; i++) {
        const gp = gamepads[i];
        if (!gp) continue;

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

        // LB (button 4) and RB (button 5) -> Cycle Categories
        if (gp.buttons[4] && gp.buttons[4].pressed) {
            if (!buttonPressed[`${i}_4`]) {
                cycleCategory(-1);
                buttonPressed[`${i}_4`] = true;
            }
        } else {
            buttonPressed[`${i}_4`] = false;
        }

        if (gp.buttons[5] && gp.buttons[5].pressed) {
            if (!buttonPressed[`${i}_5`]) {
                cycleCategory(1);
                buttonPressed[`${i}_5`] = true;
            }
        } else {
            buttonPressed[`${i}_5`] = false;
        }

        // Button 0: Cross / A -> Launch
        if (gp.buttons[0] && gp.buttons[0].pressed) {
            if (!buttonPressed[`${i}_0`]) {
                initAudio();
                launchSelectedGame();
                buttonPressed[`${i}_0`] = true;
            }
        } else {
            buttonPressed[`${i}_0`] = false;
        }

        // Button 1: Circle / B -> Exit Game, Cancel Ingestion, or Reset to Disc Slot
        if (gp.buttons[1] && gp.buttons[1].pressed) {
            if (!buttonPressed[`${i}_1`]) {
                initAudio();
                if (gameplayViewport && gameplayViewport.classList.contains("active")) {
                    fetch("/api/exit", { method: "POST" });
                    setTimeout(fetchStatus, 200);
                } else if (ingestionModal && ingestionModal.classList.contains("visible")) {
                    fetch("/api/ingestion/cancel", { method: "POST" });
                } else {
                    updateSelection(0);
                }
                buttonPressed[`${i}_1`] = true;
            }
        } else {
            buttonPressed[`${i}_1`] = false;
        }

        // Button 3: Triangle / Y -> Refresh Library
        if (gp.buttons[3] && gp.buttons[3].pressed) {
            if (!buttonPressed[`${i}_3`]) {
                initAudio();
                fetchLibrary();
                buttonPressed[`${i}_3`] = true;
            }
        } else {
            buttonPressed[`${i}_3`] = false;
        }
    }

    const ctrlStatusElem = document.getElementById("controllerStatus");
    if (ctrlStatusElem) {
        ctrlStatusElem.style.color = anyConnected ? "#10B981" : "";
    }

    requestAnimationFrame(pollGamepad);
}

// ==========================================================================
// 7. Keyboard Navigation (Arrows, Enter, Escape)
// ==========================================================================
window.addEventListener("keydown", (e) => {
    // Suppress keyboard UI navigation while a game is active (allow Escape to exit)
    if (isGameActive && e.key !== "Escape") return;

    // Prevent carousel jumping while typing in search box
    if (document.activeElement === searchInput) {
        if (e.key === "Escape") {
            searchInput.blur();
            if (searchClearBtn) searchClearBtn.click();
        }
        return;
    }

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

window.addEventListener("focus", () => {
    fetchStatus();
});

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
            isGameActive = false;
            gameLaunchTimestamp = 0;
            if (gameplayViewport) gameplayViewport.classList.remove("active");
            await fetch("/api/exit", { method: "POST" });
            setTimeout(fetchStatus, 200);
        });
    }
    if (btnExitGameplayReturn) {
        btnExitGameplayReturn.addEventListener("click", async () => {
            initAudio();
            isGameActive = false;
            gameLaunchTimestamp = 0;
            if (gameplayViewport) gameplayViewport.classList.remove("active");
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

    // Category Filter Pills
    if (categoryPillsContainer) {
        const pills = categoryPillsContainer.querySelectorAll(".cat-pill");
        pills.forEach(pill => {
            pill.addEventListener("click", () => {
                initAudio();
                pills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                activeFilter = pill.dataset.filter || "all";
                playTickSound();
                applyFiltersAndRender(false);
            });
        });
    }

    // Instant Search Input
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            searchQuery = e.target.value;
            if (searchClearBtn) {
                searchClearBtn.style.display = searchQuery ? "block" : "none";
            }
            applyFiltersAndRender(false);
        });
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener("click", () => {
            if (searchInput) searchInput.value = "";
            searchQuery = "";
            searchClearBtn.style.display = "none";
            applyFiltersAndRender(false);
        });
    }

    updateClock();
    setInterval(updateClock, 10000);

    fetchStatus();
    setInterval(fetchStatus, 1500);

    fetchLibrary();

    // Start gamepad polling
    requestAnimationFrame(pollGamepad);
});
