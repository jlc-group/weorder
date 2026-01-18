import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import './Login.css';

/**
 * SSO Callback Handler
 * 
 * This component handles the redirect from JLC SSO Server.
 * It receives a JWT token in the URL and exchanges it for a WeOrder session.
 * 
 * Usage:
 * 1. User clicks "Login with JLC SSO" on login page
 * 2. User is redirected to SSO server
 * 3. After login, SSO redirects to /auth/callback?token=<JWT>
 * 4. This component sends the token to /api/auth/sso
 * 5. Backend verifies token and returns WeOrder session
 * 6. Frontend saves session and redirects to dashboard
 */
const AuthCallback: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [error, setError] = useState<string | null>(null);
    const [processing, setProcessing] = useState(true);

    useEffect(() => {
        const processCallback = async () => {
            try {
                const token = searchParams.get('token');
                const isDemo = searchParams.get('demo');

                if (!token && !isDemo) {
                    setError('ไม่พบ token จาก SSO Server');
                    setProcessing(false);
                    return;
                }

                // For demo/development - show info message
                if (isDemo) {
                    setError('SSO Demo Mode: ในการใช้งานจริง ระบบจะ redirect ไปยัง SSO Server');
                    setProcessing(false);
                    return;
                }

                // Exchange SSO token for WeOrder session
                const response = await api.post('/auth/sso', { token });

                const { access_token, user } = response.data;

                // Save to localStorage (same as normal login)
                localStorage.setItem('token', access_token);
                localStorage.setItem('user', JSON.stringify(user));

                // Reload to apply new session
                window.location.href = '/dashboard';

            } catch (err: unknown) {
                const errorMessage = err instanceof Error
                    ? err.message
                    : 'SSO Login failed';
                setError(errorMessage);
                setProcessing(false);
            }
        };

        processCallback();
    }, [searchParams, navigate]);

    return (
        <div className="login-container">
            <div className="login-card" style={{ textAlign: 'center' }}>
                <div className="login-header">
                    <div className="login-logo">
                        <i className="bi bi-shield-lock"></i>
                    </div>
                    <h1>SSO Login</h1>
                </div>

                {processing ? (
                    <div style={{ padding: '40px 0' }}>
                        <div className="spinner" style={{
                            width: '40px',
                            height: '40px',
                            margin: '0 auto 20px',
                            border: '3px solid #e5e7eb',
                            borderTopColor: '#667eea',
                            borderRadius: '50%'
                        }}></div>
                        <p style={{ color: '#666' }}>กำลังตรวจสอบข้อมูล...</p>
                    </div>
                ) : error ? (
                    <div style={{ padding: '20px 0' }}>
                        <div className="login-error" style={{ marginBottom: '20px' }}>
                            <i className="bi bi-exclamation-circle"></i>
                            {error}
                        </div>
                        <button
                            className="login-button"
                            onClick={() => navigate('/login')}
                        >
                            <i className="bi bi-arrow-left"></i>
                            กลับไปหน้า Login
                        </button>
                    </div>
                ) : null}

                <div className="login-footer">
                    <p>© 2026 WeOrder - JLC Group</p>
                </div>
            </div>
        </div>
    );
};

export default AuthCallback;
