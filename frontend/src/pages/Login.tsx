import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Login.css';

const Login: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await login(username, password);
            navigate('/dashboard');
        } catch (err: any) {
            const message = err.response?.data?.detail || 'เข้าสู่ระบบไม่สำเร็จ';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <div className="login-logo">
                        <i className="bi bi-box-seam"></i>
                    </div>
                    <h1>WeOrder</h1>
                    <p>ระบบจัดการคำสั่งซื้อ</p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    {error && (
                        <div className="login-error">
                            <i className="bi bi-exclamation-circle"></i>
                            {error}
                        </div>
                    )}

                    <div className="form-group">
                        <label htmlFor="username">
                            <i className="bi bi-person"></i>
                            ชื่อผู้ใช้
                        </label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="กรอกชื่อผู้ใช้"
                            required
                            disabled={loading}
                            autoComplete="username"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">
                            <i className="bi bi-lock"></i>
                            รหัสผ่าน
                        </label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="กรอกรหัสผ่าน"
                            disabled={loading}
                            autoComplete="current-password"
                        />
                    </div>

                    <button type="submit" className="login-button" disabled={loading}>
                        {loading ? (
                            <>
                                <span className="spinner"></span>
                                กำลังเข้าสู่ระบบ...
                            </>
                        ) : (
                            <>
                                <i className="bi bi-box-arrow-in-right"></i>
                                เข้าสู่ระบบ
                            </>
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <p>© 2026 WeOrder - JulaHerb</p>
                </div>
            </div>
        </div>
    );
};

export default Login;
