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

// DOM Elements
const carouselTrack = document.getElementById("carouselTrack");
const heroTitle = document.getElementById("heroTitle");
const heroDescription = document.getElementById("heroDescription");
const heroPlatformBadge = document.getElementById("heroPlatformBadge");
const heroSerialBadge = document.getElementById("heroSerialBadge");
const heroFormatBadge = document.getElementById("heroFormatBadge");
const opticalDrivePill = document.getElementById("opticalDrivePill");
const statusDiscText = document.getElementById("statusDiscText");
const statusDiscIcon = document.getElementById("statusDiscIcon");
const systemClock = document.getElementById("systemClock");

// ==========================================================================
// 1. Web Audio API Synthesizer (Authentic PlayStation Sound FX)
// ==========================================================================
let audioCtx = null;

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        isAudioEnabled = true;
    }
}

function playTickSound() {
    if (!audioCtx) return;
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
    if (!audioCtx) return;
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
            heroDescription.textContent = `Physical original ${discState.type} game disc detected in optical drive. Press (✕) / (A) to boot into fullscreen emulator.`;
        } else {
            heroPlatformBadge.style.display = "none";
            heroSerialBadge.style.display = "none";
            heroFormatBadge.textContent = "OPTICAL DRIVE EMPTY";
            heroTitle.textContent = "Insert PlayStation Disc";
            heroDescription.textContent = "Insert an original PlayStation 1 or 2 physical disc into your USB drive to start playing automatically.";
        }
    } else {
        // Digital Game Slot
        const game = libraryGames[currentIndex - 1];
        if (game) {
            heroPlatformBadge.textContent = game.platform;
            heroPlatformBadge.style.display = "inline-block";
            heroSerialBadge.textContent = game.serial ? `[${game.serial}]` : `SIZE: ${game.file_size_mb} MB`;
            heroSerialBadge.style.display = "inline-block";
            heroFormatBadge.textContent = `${game.format} FILE`;
            heroTitle.textContent = game.title;
            heroDescription.textContent = `Downloaded ${game.platform} title located in your PlayStation storage library. Press (✕) / (A) to play.`;
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
            alert("No disc in drive. Please insert an original PS1 or PS2 disc.");
            return;
        }
        try {
            const res = await fetch("/api/launch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ type: "disc" })
            });
            const data = await res.json();
            if (!data.success) {
                alert(`Could not start disc: ${data.error || data.status}`);
            }
        } catch (e) {
            console.error("Launch error:", e);
        }
    } else {
        // Launch Digital Game
        const game = libraryGames[currentIndex - 1];
        if (!game) return;

        try {
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
            if (!data.success) {
                alert(`Could not launch ${game.title}: ${data.error || data.status}`);
            }
        } catch (e) {
            console.error("Launch error:", e);
        }
    }
}

// ==========================================================================
// 5. REST Polling & Library Sync
// ==========================================================================
async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();

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
            document.getElementById("discCardSubtitle").textContent = "Press (✕) to Play Disc";
            document.getElementById("spinningDiscGraphic").classList.add("spinning");
        } else {
            discState = { present: false, title: "No Disc Inserted", type: "OPTICAL", serial: "" };
            opticalDrivePill.classList.remove("disc-ready");
            statusDiscIcon.textContent = "⏏";
            statusDiscText.textContent = "Optical Drive Empty";

            document.getElementById("discCardBadge").textContent = "DRIVE D:";
            document.getElementById("discCardType").textContent = "EMPTY";
            document.getElementById("discCardTitle").textContent = "No Disc Inserted";
            document.getElementById("discCardSubtitle").textContent = "Insert PS1/PS2 Disc";
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
                "PS4": "linear-gradient(135deg, #0070D1, #003666)"
            };
            const grad = bgGradients[game.platform] || bgGradients["PS1"];

            card.innerHTML = `
                <div class="poster-art" style="background: ${grad};"></div>
                <div class="card-inner">
                    <div class="card-header">
                        <span class="card-badge">${game.platform}</span>
                        <span class="card-type">${game.format}</span>
                    </div>
                    <div class="disc-visual">
                        <div style="font-size: 54px; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.5));">
                            ${game.platform === "PS1" ? "🕹" : (game.platform === "PS2" ? "🎮" : "⚡")}
                        </div>
                    </div>
                    <div class="card-footer">
                        <h3 class="card-title">${game.title}</h3>
                        <span class="card-subtitle">${game.file_size_mb} MB • Installed</span>
                    </div>
                </div>
            `;

            card.addEventListener("click", () => {
                initAudio();
                updateSelection(idx + 1);
                launchSelectedGame();
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

        // Button 1: Circle / B -> Reset to Disc Slot
        if (gp.buttons[1] && gp.buttons[1].pressed) {
            if (!buttonPressed[1]) {
                initAudio();
                updateSelection(0);
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
        updateSelection(0);
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
// Initialization
// ==========================================================================
window.addEventListener("DOMContentLoaded", () => {
    initAmbientWave();
    cards = Array.from(carouselTrack.querySelectorAll(".game-card"));

    document.getElementById("discCard").addEventListener("click", () => {
        initAudio();
        updateSelection(0);
        launchSelectedGame();
    });

    updateClock();
    setInterval(updateClock, 10000);

    fetchStatus();
    setInterval(fetchStatus, 2000);

    fetchLibrary();

    // Start gamepad polling
    requestAnimationFrame(pollGamepad);
});
