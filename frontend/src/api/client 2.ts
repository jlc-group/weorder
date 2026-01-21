import axios from 'axios';

const api = axios.create({
    baseURL: '/api',  // Use relative path - works for both dev (via Vite proxy) and production
    timeout: 60000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add interceptor for response handling (e.g. logging)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error);
        return Promise.reject(error);
    }
);

export default api;
