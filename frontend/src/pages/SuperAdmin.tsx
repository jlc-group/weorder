import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface User {
    id: string;
    username: string;
    email: string;
    full_name: string;
    is_active: boolean;
    roles: { id: string; code: string; name: string }[];
    department: { id: string; code: string; name: string } | null;
}

interface Role {
    id: string;
    code: string;
    name: string;
    allowed_pages: string[];
}

interface Department {
    id: string;
    code: string;
    name: string;
    allowed_pages: string[];
}

interface PageInfo {
    key: string;
    name: string;
    icon: string;
}

const SuperAdmin: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'users' | 'departments' | 'roles'>('users');
    const [users, setUsers] = useState<User[]>([]);
    const [roles, setRoles] = useState<Role[]>([]);
    const [departments, setDepartments] = useState<Department[]>([]);
    const [pages, setPages] = useState<PageInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [showUserModal, setShowUserModal] = useState(false);
    const [showRoleModal, setShowRoleModal] = useState(false);
    const [showDeptModal, setShowDeptModal] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [editingRole, setEditingRole] = useState<Role | null>(null);
    const [editingDept, setEditingDept] = useState<Department | null>(null);

    // User form
    const [userForm, setUserForm] = useState({
        username: '',
        email: '',
        full_name: '',
        password: '',
        role_ids: [] as string[],
        department_id: ''
    });

    // Role form
    const [roleForm, setRoleForm] = useState({
        code: '',
        name: '',
        allowed_pages: [] as string[]
    });

    // Department form
    const [deptForm, setDeptForm] = useState({
        code: '',
        name: '',
        allowed_pages: [] as string[]
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [usersRes, rolesRes, deptsRes, pagesRes] = await Promise.all([
                api.get('/users'),
                api.get('/roles'),
                api.get('/departments'),
                api.get('/roles/pages')
            ]);
            setUsers(usersRes.data);
            setRoles(rolesRes.data);
            setDepartments(deptsRes.data);
            setPages(pagesRes.data);
        } catch (err) {
            console.error('Failed to fetch data:', err);
        }
        setLoading(false);
    };

    // === Users ===
    const handleCreateUser = async () => {
        try {
            await api.post('/users', userForm);
            setShowUserModal(false);
            resetUserForm();
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to create user');
        }
    };

    const handleUpdateUser = async () => {
        if (!editingUser) return;
        try {
            await api.put(`/users/${editingUser.id}`, {
                email: userForm.email,
                full_name: userForm.full_name,
                department_id: userForm.department_id || null
            });
            // Update roles
            await api.post(`/users/${editingUser.id}/roles`, {
                role_ids: userForm.role_ids
            });
            setShowUserModal(false);
            setEditingUser(null);
            resetUserForm();
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to update user');
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm('ยืนยันลบผู้ใช้นี้?')) return;
        try {
            await api.delete(`/users/${userId}`);
            fetchData();
        } catch (err) {
            alert('Failed to delete user');
        }
    };

    const openEditUser = (user: User) => {
        setEditingUser(user);
        setUserForm({
            username: user.username,
            email: user.email || '',
            full_name: user.full_name || '',
            password: '',
            role_ids: user.roles.map(r => r.id),
            department_id: user.department?.id || ''
        });
        setShowUserModal(true);
    };

    const resetUserForm = () => {
        setUserForm({ username: '', email: '', full_name: '', password: '', role_ids: [], department_id: '' });
    };

    // === Roles ===
    const handleCreateRole = async () => {
        try {
            await api.post('/roles', roleForm);
            setShowRoleModal(false);
            resetRoleForm();
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to create role');
        }
    };

    const handleUpdateRole = async () => {
        if (!editingRole) return;
        try {
            await api.put(`/roles/${editingRole.id}`, {
                name: roleForm.name,
                allowed_pages: roleForm.allowed_pages
            });
            setShowRoleModal(false);
            setEditingRole(null);
            resetRoleForm();
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to update role');
        }
    };

    const handleDeleteRole = async (roleId: string) => {
        if (!window.confirm('ยืนยันลบ Role นี้?')) return;
        try {
            await api.delete(`/roles/${roleId}`);
            fetchData();
        } catch (err) {
            alert('Failed to delete role');
        }
    };

    const openEditRole = (role: Role) => {
        setEditingRole(role);
        setRoleForm({
            code: role.code,
            name: role.name,
            allowed_pages: role.allowed_pages
        });
        setShowRoleModal(true);
    };

    const resetRoleForm = () => {
        setRoleForm({ code: '', name: '', allowed_pages: [] });
    };

    const togglePage = (pageKey: string) => {
        setRoleForm(prev => ({
            ...prev,
            allowed_pages: prev.allowed_pages.includes(pageKey)
                ? prev.allowed_pages.filter(p => p !== pageKey)
                : [...prev.allowed_pages, pageKey]
        }));
    };

    const toggleRole = (roleId: string) => {
        setUserForm(prev => ({
            ...prev,
            role_ids: prev.role_ids.includes(roleId)
                ? prev.role_ids.filter(r => r !== roleId)
                : [...prev.role_ids, roleId]
        }));
    };

    // === Departments ===
    const handleCreateDept = async () => {
        try {
            await api.post('/departments', deptForm);
            setShowDeptModal(false);
            resetDeptForm();
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to create department');
        }
    };

    const handleUpdateDept = async () => {
        if (!editingDept) return;
        try {
            await api.put(`/departments/${editingDept.id}`, {
                name: deptForm.name,
                allowed_pages: deptForm.allowed_pages
            });
            setShowDeptModal(false);
            setEditingDept(null);
            resetDeptForm();
            fetchData();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to update department');
        }
    };

    const handleDeleteDept = async (deptId: string) => {
        if (!window.confirm('ยืนยันลบแผนกนี้?')) return;
        try {
            await api.delete(`/departments/${deptId}`);
            fetchData();
        } catch (err) {
            alert('Failed to delete department');
        }
    };

    const openEditDept = (dept: Department) => {
        setEditingDept(dept);
        setDeptForm({
            code: dept.code,
            name: dept.name,
            allowed_pages: dept.allowed_pages
        });
        setShowDeptModal(true);
    };

    const resetDeptForm = () => {
        setDeptForm({ code: '', name: '', allowed_pages: [] });
    };

    const toggleDeptPage = (pageKey: string) => {
        setDeptForm(prev => ({
            ...prev,
            allowed_pages: prev.allowed_pages.includes(pageKey)
                ? prev.allowed_pages.filter(p => p !== pageKey)
                : [...prev.allowed_pages, pageKey]
        }));
    };

    return (
        <Layout title="Super Admin">
            <div className="container-fluid">
                {/* Header */}
                <div className="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h4 className="mb-1">
                            <i className="bi bi-shield-lock me-2"></i>
                            จัดการผู้ใช้และสิทธิ์
                        </h4>
                        <small className="text-muted">Super Admin Panel</small>
                    </div>
                </div>

                {/* Tabs */}
                <ul className="nav nav-tabs mb-4">
                    <li className="nav-item">
                        <button
                            className={`nav-link ${activeTab === 'users' ? 'active' : ''}`}
                            onClick={() => setActiveTab('users')}
                        >
                            <i className="bi bi-people me-2"></i>
                            ผู้ใช้งาน ({users.length})
                        </button>
                    </li>
                    <li className="nav-item">
                        <button
                            className={`nav-link ${activeTab === 'departments' ? 'active' : ''}`}
                            onClick={() => setActiveTab('departments')}
                        >
                            <i className="bi bi-building me-2"></i>
                            แผนก ({departments.length})
                        </button>
                    </li>
                    <li className="nav-item">
                        <button
                            className={`nav-link ${activeTab === 'roles' ? 'active' : ''}`}
                            onClick={() => setActiveTab('roles')}
                        >
                            <i className="bi bi-person-badge me-2"></i>
                            Role & Permissions ({roles.length})
                        </button>
                    </li>
                </ul>

                {loading ? (
                    <div className="text-center py-5">
                        <div className="spinner-border text-primary"></div>
                    </div>
                ) : (
                    <>
                        {/* Users Tab */}
                        {activeTab === 'users' && (
                            <div className="card">
                                <div className="card-header d-flex justify-content-between align-items-center">
                                    <span>รายชื่อผู้ใช้งาน</span>
                                    <button
                                        className="btn btn-primary btn-sm"
                                        onClick={() => {
                                            setEditingUser(null);
                                            resetUserForm();
                                            setShowUserModal(true);
                                        }}
                                    >
                                        <i className="bi bi-plus-lg me-1"></i> เพิ่มผู้ใช้
                                    </button>
                                </div>
                                <div className="card-body p-0">
                                    <table className="table table-hover mb-0">
                                        <thead className="table-light">
                                            <tr>
                                                <th>Username</th>
                                                <th>ชื่อ</th>
                                                <th>แผนก</th>
                                                <th>Roles</th>
                                                <th>สถานะ</th>
                                                <th style={{ width: '100px' }}></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {users.map(user => (
                                                <tr key={user.id}>
                                                    <td className="fw-bold">{user.username}</td>
                                                    <td>{user.full_name || '-'}</td>
                                                    <td>
                                                        {user.department ? (
                                                            <span className="badge bg-info">{user.department.name}</span>
                                                        ) : (
                                                            <span className="text-muted">-</span>
                                                        )}
                                                    </td>
                                                    <td>
                                                        {user.roles.map(r => (
                                                            <span key={r.id} className="badge bg-primary me-1">{r.name}</span>
                                                        ))}
                                                    </td>
                                                    <td>
                                                        {user.is_active ? (
                                                            <span className="badge bg-success">Active</span>
                                                        ) : (
                                                            <span className="badge bg-secondary">Inactive</span>
                                                        )}
                                                    </td>
                                                    <td>
                                                        <button
                                                            className="btn btn-sm btn-outline-primary me-1"
                                                            onClick={() => openEditUser(user)}
                                                        >
                                                            <i className="bi bi-pencil"></i>
                                                        </button>
                                                        <button
                                                            className="btn btn-sm btn-outline-danger"
                                                            onClick={() => handleDeleteUser(user.id)}
                                                        >
                                                            <i className="bi bi-trash"></i>
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {users.length === 0 && (
                                                <tr>
                                                    <td colSpan={6} className="text-center text-muted py-4">
                                                        ยังไม่มีผู้ใช้งาน
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* Departments Tab */}
                        {activeTab === 'departments' && (
                            <div className="card">
                                <div className="card-header d-flex justify-content-between align-items-center">
                                    <span>แผนก & สิทธิ์การเข้าถึงหน้า</span>
                                    <button
                                        className="btn btn-primary btn-sm"
                                        onClick={() => {
                                            setEditingDept(null);
                                            resetDeptForm();
                                            setShowDeptModal(true);
                                        }}
                                    >
                                        <i className="bi bi-plus-lg me-1"></i> เพิ่มแผนก
                                    </button>
                                </div>
                                <div className="card-body p-0">
                                    <div className="table-responsive">
                                        <table className="table table-bordered mb-0">
                                            <thead className="table-light">
                                                <tr>
                                                    <th>แผนก</th>
                                                    {pages.map(p => (
                                                        <th key={p.key} className="text-center" style={{ fontSize: '12px' }}>
                                                            <i className={`bi ${p.icon} d-block mb-1`}></i>
                                                            {p.name}
                                                        </th>
                                                    ))}
                                                    <th style={{ width: '80px' }}></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {departments.map(dept => (
                                                    <tr key={dept.id}>
                                                        <td>
                                                            <strong>{dept.name}</strong>
                                                            <br />
                                                            <small className="text-muted">{dept.code}</small>
                                                        </td>
                                                        {pages.map(p => (
                                                            <td key={p.key} className="text-center">
                                                                {dept.allowed_pages.includes(p.key) ? (
                                                                    <i className="bi bi-check-circle-fill text-success fs-5"></i>
                                                                ) : (
                                                                    <i className="bi bi-x-circle text-muted"></i>
                                                                )}
                                                            </td>
                                                        ))}
                                                        <td>
                                                            <button
                                                                className="btn btn-sm btn-outline-primary me-1"
                                                                onClick={() => openEditDept(dept)}
                                                            >
                                                                <i className="bi bi-pencil"></i>
                                                            </button>
                                                            <button
                                                                className="btn btn-sm btn-outline-danger"
                                                                onClick={() => handleDeleteDept(dept.id)}
                                                            >
                                                                <i className="bi bi-trash"></i>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                                {departments.length === 0 && (
                                                    <tr>
                                                        <td colSpan={pages.length + 2} className="text-center text-muted py-4">
                                                            ยังไม่มีแผนก
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Roles Tab */}
                        {activeTab === 'roles' && (
                            <div className="card">
                                <div className="card-header d-flex justify-content-between align-items-center">
                                    <span>Roles & Page Permissions</span>
                                    <button
                                        className="btn btn-primary btn-sm"
                                        onClick={() => {
                                            setEditingRole(null);
                                            resetRoleForm();
                                            setShowRoleModal(true);
                                        }}
                                    >
                                        <i className="bi bi-plus-lg me-1"></i> เพิ่ม Role
                                    </button>
                                </div>
                                <div className="card-body p-0">
                                    <div className="table-responsive">
                                        <table className="table table-bordered mb-0">
                                            <thead className="table-light">
                                                <tr>
                                                    <th>Role</th>
                                                    {pages.map(p => (
                                                        <th key={p.key} className="text-center" style={{ fontSize: '12px' }}>
                                                            <i className={`bi ${p.icon} d-block mb-1`}></i>
                                                            {p.name}
                                                        </th>
                                                    ))}
                                                    <th style={{ width: '80px' }}></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {roles.map(role => (
                                                    <tr key={role.id}>
                                                        <td>
                                                            <strong>{role.name}</strong>
                                                            <br />
                                                            <small className="text-muted">{role.code}</small>
                                                        </td>
                                                        {pages.map(p => (
                                                            <td key={p.key} className="text-center">
                                                                {role.allowed_pages.includes(p.key) ? (
                                                                    <i className="bi bi-check-circle-fill text-success fs-5"></i>
                                                                ) : (
                                                                    <i className="bi bi-x-circle text-muted"></i>
                                                                )}
                                                            </td>
                                                        ))}
                                                        <td>
                                                            <button
                                                                className="btn btn-sm btn-outline-primary me-1"
                                                                onClick={() => openEditRole(role)}
                                                            >
                                                                <i className="bi bi-pencil"></i>
                                                            </button>
                                                            <button
                                                                className="btn btn-sm btn-outline-danger"
                                                                onClick={() => handleDeleteRole(role.id)}
                                                            >
                                                                <i className="bi bi-trash"></i>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )}

                {/* User Modal */}
                {showUserModal && (
                    <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                        <div className="modal-dialog">
                            <div className="modal-content">
                                <div className="modal-header">
                                    <h5 className="modal-title">
                                        {editingUser ? 'แก้ไขผู้ใช้' : 'เพิ่มผู้ใช้ใหม่'}
                                    </h5>
                                    <button className="btn-close" onClick={() => setShowUserModal(false)}></button>
                                </div>
                                <div className="modal-body">
                                    <div className="mb-3">
                                        <label className="form-label">Username *</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={userForm.username}
                                            onChange={e => setUserForm({ ...userForm, username: e.target.value })}
                                            disabled={!!editingUser}
                                        />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">ชื่อ-นามสกุล</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={userForm.full_name}
                                            onChange={e => setUserForm({ ...userForm, full_name: e.target.value })}
                                        />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">Email</label>
                                        <input
                                            type="email"
                                            className="form-control"
                                            value={userForm.email}
                                            onChange={e => setUserForm({ ...userForm, email: e.target.value })}
                                        />
                                    </div>
                                    {!editingUser && (
                                        <div className="mb-3">
                                            <label className="form-label">รหัสผ่าน</label>
                                            <input
                                                type="password"
                                                className="form-control"
                                                value={userForm.password}
                                                onChange={e => setUserForm({ ...userForm, password: e.target.value })}
                                            />
                                        </div>
                                    )}
                                    <div className="mb-3">
                                        <label className="form-label">Roles</label>
                                        <div className="d-flex flex-wrap gap-2">
                                            {roles.map(role => (
                                                <button
                                                    key={role.id}
                                                    type="button"
                                                    className={`btn btn-sm ${userForm.role_ids.includes(role.id) ? 'btn-primary' : 'btn-outline-secondary'}`}
                                                    onClick={() => toggleRole(role.id)}
                                                >
                                                    {userForm.role_ids.includes(role.id) && <i className="bi bi-check me-1"></i>}
                                                    {role.name}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">แผนก</label>
                                        <select
                                            className="form-select"
                                            value={userForm.department_id}
                                            onChange={e => setUserForm({ ...userForm, department_id: e.target.value })}
                                        >
                                            <option value="">-- ไม่ระบุแผนก --</option>
                                            {departments.map(dept => (
                                                <option key={dept.id} value={dept.id}>{dept.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button className="btn btn-secondary" onClick={() => setShowUserModal(false)}>
                                        ยกเลิก
                                    </button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={editingUser ? handleUpdateUser : handleCreateUser}
                                    >
                                        {editingUser ? 'บันทึก' : 'สร้างผู้ใช้'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Role Modal */}
                {showRoleModal && (
                    <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                        <div className="modal-dialog modal-lg">
                            <div className="modal-content">
                                <div className="modal-header">
                                    <h5 className="modal-title">
                                        {editingRole ? 'แก้ไข Role' : 'เพิ่ม Role ใหม่'}
                                    </h5>
                                    <button className="btn-close" onClick={() => setShowRoleModal(false)}></button>
                                </div>
                                <div className="modal-body">
                                    <div className="row">
                                        <div className="col-md-6 mb-3">
                                            <label className="form-label">Role Code *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={roleForm.code}
                                                onChange={e => setRoleForm({ ...roleForm, code: e.target.value })}
                                                disabled={!!editingRole}
                                                placeholder="e.g. manager"
                                            />
                                        </div>
                                        <div className="col-md-6 mb-3">
                                            <label className="form-label">ชื่อ Role *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={roleForm.name}
                                                onChange={e => setRoleForm({ ...roleForm, name: e.target.value })}
                                                placeholder="e.g. Manager"
                                            />
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">หน้าที่เข้าถึงได้</label>
                                        <div className="row g-2">
                                            {pages.map(page => (
                                                <div key={page.key} className="col-4 col-md-3">
                                                    <div
                                                        className={`card text-center p-2 cursor-pointer ${roleForm.allowed_pages.includes(page.key) ? 'border-primary bg-primary bg-opacity-10' : ''}`}
                                                        style={{ cursor: 'pointer' }}
                                                        onClick={() => togglePage(page.key)}
                                                    >
                                                        <i className={`bi ${page.icon} fs-4 ${roleForm.allowed_pages.includes(page.key) ? 'text-primary' : 'text-muted'}`}></i>
                                                        <small className={roleForm.allowed_pages.includes(page.key) ? 'text-primary fw-bold' : ''}>
                                                            {page.name}
                                                        </small>
                                                        {roleForm.allowed_pages.includes(page.key) && (
                                                            <i className="bi bi-check-circle-fill text-primary position-absolute top-0 end-0 m-1"></i>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button className="btn btn-secondary" onClick={() => setShowRoleModal(false)}>
                                        ยกเลิก
                                    </button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={editingRole ? handleUpdateRole : handleCreateRole}
                                    >
                                        {editingRole ? 'บันทึก' : 'สร้าง Role'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Department Modal */}
                {showDeptModal && (
                    <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                        <div className="modal-dialog modal-lg">
                            <div className="modal-content">
                                <div className="modal-header">
                                    <h5 className="modal-title">
                                        {editingDept ? 'แก้ไขแผนก' : 'เพิ่มแผนกใหม่'}
                                    </h5>
                                    <button className="btn-close" onClick={() => setShowDeptModal(false)}></button>
                                </div>
                                <div className="modal-body">
                                    <div className="row">
                                        <div className="col-md-6 mb-3">
                                            <label className="form-label">รหัสแผนก *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={deptForm.code}
                                                onChange={e => setDeptForm({ ...deptForm, code: e.target.value })}
                                                disabled={!!editingDept}
                                                placeholder="e.g. sales"
                                            />
                                        </div>
                                        <div className="col-md-6 mb-3">
                                            <label className="form-label">ชื่อแผนก *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                value={deptForm.name}
                                                onChange={e => setDeptForm({ ...deptForm, name: e.target.value })}
                                                placeholder="e.g. ฝ่ายขาย"
                                            />
                                        </div>
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">หน้าที่เข้าถึงได้</label>
                                        <div className="row g-2">
                                            {pages.map(page => (
                                                <div key={page.key} className="col-4 col-md-3">
                                                    <div
                                                        className={`card text-center p-2 cursor-pointer ${deptForm.allowed_pages.includes(page.key) ? 'border-info bg-info bg-opacity-10' : ''}`}
                                                        style={{ cursor: 'pointer' }}
                                                        onClick={() => toggleDeptPage(page.key)}
                                                    >
                                                        <i className={`bi ${page.icon} fs-4 ${deptForm.allowed_pages.includes(page.key) ? 'text-info' : 'text-muted'}`}></i>
                                                        <small className={deptForm.allowed_pages.includes(page.key) ? 'text-info fw-bold' : ''}>
                                                            {page.name}
                                                        </small>
                                                        {deptForm.allowed_pages.includes(page.key) && (
                                                            <i className="bi bi-check-circle-fill text-info position-absolute top-0 end-0 m-1"></i>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button className="btn btn-secondary" onClick={() => setShowDeptModal(false)}>
                                        ยกเลิก
                                    </button>
                                    <button
                                        className="btn btn-info"
                                        onClick={editingDept ? handleUpdateDept : handleCreateDept}
                                    >
                                        {editingDept ? 'บันทึก' : 'สร้างแผนก'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default SuperAdmin;
