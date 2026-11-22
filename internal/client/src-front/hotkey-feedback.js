export function setupHotkeyFeedback() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return () => {};

    let context;
    let pendingResume;

    const resume = () => {
        try {
            context ??= new AudioContext();
            if (context.state === "running") return;
            pendingResume ??= context.resume()
                .catch(() => {})
                .finally(() => { pendingResume = undefined; });
            return pendingResume;
        } catch {
            // Feedback is optional; audio policy must not prevent the shortcut.
        }
    };

    const unlock = (event) => {
        if (event.isTrusted) void resume();
    };
    // A shortcut coming from the tray is not a WebView user gesture.
    window.addEventListener("pointerup", unlock, { capture: true });
    window.addEventListener("keydown", unlock, { capture: true });

    const play = () => {
        if (context?.state !== "running") return;
        const start = context.currentTime;
        const tone = context.createOscillator();
        const gain = context.createGain();
        tone.frequency.setValueAtTime(880, start);
        tone.frequency.exponentialRampToValueAtTime(660, start + 0.06);
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(0.045, start + 0.008);
        gain.gain.linearRampToValueAtTime(0, start + 0.07);
        tone.connect(gain).connect(context.destination);
        tone.start(start);
        tone.stop(start + 0.07);
    };

    return () => {
        if (context?.state === "running") {
            play();
            return;
        }
        const pressedAt = performance.now();
        void resume()?.then(() => {
            if (performance.now() - pressedAt < 200) play();
        });
    };
}
