// Mobile Feedback Utilities
// Haptic Vibration and Voice Feedback for mobile scanning

/**
 * Trigger haptic vibration (if supported)
 * @param pattern - 'success' | 'error' | 'light'
 */
export const vibrate = (pattern: 'success' | 'error' | 'light' = 'light') => {
    if (!navigator.vibrate) return;

    switch (pattern) {
        case 'success':
            // Short double vibration
            navigator.vibrate([50, 50, 50]);
            break;
        case 'error':
            // Long single vibration
            navigator.vibrate([200]);
            break;
        case 'light':
        default:
            // Very short tap
            navigator.vibrate(30);
            break;
    }
};

/**
 * Speak text using Web Speech API (if supported)
 * @param text - Text to speak
 * @param lang - Language code (default: 'th-TH')
 */
export const speak = (text: string, lang: string = 'th-TH') => {
    if (!window.speechSynthesis) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 1.1; // Slightly faster
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
};

/**
 * Combined feedback for scan results
 */
export const scanFeedback = {
    success: (message?: string) => {
        vibrate('success');
        speak(message || 'สำเร็จ');
    },
    error: (message?: string) => {
        vibrate('error');
        speak(message || 'ผิดพลาด');
    },
    info: (message: string) => {
        vibrate('light');
        speak(message);
    }
};
