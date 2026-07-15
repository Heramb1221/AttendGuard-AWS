/**
 * Lightweight, privacy-conscious device fingerprint.
 *
 * This deliberately avoids invasive canvas/audio fingerprinting techniques.
 * It combines a handful of stable, non-identifying browser characteristics
 * with a value persisted in localStorage, which is enough to distinguish
 * "the same physical phone used across two student accounts" (our actual
 * fraud-detection need) without tracking users across sites.
 */
function getDeviceFingerprint() {
    const STORAGE_KEY = 'attendguard_device_id';

    let deviceId = localStorage.getItem(STORAGE_KEY);
    if (!deviceId) {
        deviceId = 'dev_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(STORAGE_KEY, deviceId);
    }

    const characteristics = [
        navigator.userAgent || '',
        navigator.language || '',
        screen.width + 'x' + screen.height,
        new Date().getTimezoneOffset(),
    ].join('|');

    // Simple non-cryptographic hash (djb2) so we don't ship a crypto dependency
    // just to combine a few strings into a fixed-length signal.
    let hash = 5381;
    for (let i = 0; i < characteristics.length; i++) {
        hash = ((hash << 5) + hash) + characteristics.charCodeAt(i);
        hash = hash & hash;
    }

    return `${deviceId}_${Math.abs(hash)}`;
}
