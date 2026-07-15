/**
 * Captures the browser's geolocation and submits an attendance record to
 * the API. Kept as a single reusable function so the mark_attendance page
 * can wire it to any button.
 */
function captureLocationAndSubmit({ sessionId, onStatus, onSuccess, onError }) {
    if (!('geolocation' in navigator)) {
        onError('Your browser does not support geolocation. Please use a modern browser.');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function (position) {
            onStatus('Location captured. Submitting attendance...');

            const payload = {
                session_id: sessionId,
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                device_fingerprint: getDeviceFingerprint(),
            };

            fetch('/api/attendance/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
                .then(async (response) => {
                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to submit attendance.');
                    }
                    onSuccess(data);
                })
                .catch((err) => {
                    onError(err.message || 'Network error while submitting attendance.');
                });
        },
        function (error) {
            let message = 'Unable to retrieve your location.';
            if (error.code === error.PERMISSION_DENIED) {
                message = 'Location permission denied. Please enable location access to mark attendance.';
            } else if (error.code === error.TIMEOUT) {
                message = 'Location request timed out. Please try again.';
            }
            onError(message);
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
}
