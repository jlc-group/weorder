import React from 'react';
import { NavLink } from 'react-router-dom';

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
    return (
        <>
            <nav className={`sidebar ${isOpen ? 'show' : ''}`}>
                <button
                    className="btn text-white position-absolute top-0 end-0 d-lg-none mt-2 me-2"
                    onClick={onClose}
                    aria-label="Close"
                >
                    <i className="bi bi-x-lg"></i>
                </button>

                <div className="sidebar-brand">
                    <h4><i className="bi bi-box-seam me-2"></i>WeOrder</h4>
                    <small>Order Management System</small>
                </div>

                <div className="sidebar-nav">
                    <div className="nav-section">หลัก</div>
                    <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-speedometer2"></i>Dashboard
                    </NavLink>
                    <NavLink to="/orders" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-receipt"></i>ออเดอร์
                    </NavLink>
                    <NavLink to="/returns" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-arrow-return-left"></i>สินค้าตีคืน
                    </NavLink>

                    <div className="nav-section">สินค้า & สต๊อก</div>
                    <NavLink to="/products" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-box"></i>สินค้า
                    </NavLink>
                    <NavLink to="/bundles" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-diagram-3"></i>Platform Bundles
                    </NavLink>
                    <NavLink to="/stock" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-stack"></i>สต๊อก
                    </NavLink>
                    <NavLink to="/report/outbound" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-truck"></i>รายงานส่งสินค้า
                    </NavLink>

                    <div className="nav-section">ปฏิบัติการ</div>
                    <NavLink to="/packing" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-box2"></i>แพ็คสินค้า
                    </NavLink>
                    <NavLink to="/promotions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-gift"></i>โปรโมชั่น
                    </NavLink>

                    <div className="nav-section">การเงิน</div>
                    <NavLink to="/finance" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-cash-stack"></i>สรุปรายวัน
                    </NavLink>
                    <NavLink to="/finance/performance" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-graph-up-arrow"></i>วิเคราะห์กำไร
                    </NavLink>
                    <NavLink to="/invoice-manager" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-receipt-cutoff"></i>ใบกำกับภาษี
                    </NavLink>

                    <div className="nav-section">ตั้งค่า</div>
                    <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={onClose}>
                        <i className="bi bi-plug"></i>Platform Integrations
                    </NavLink>
                </div>
            </nav>

            <div className={`sidebar-overlay ${isOpen ? 'show' : ''}`} onClick={onClose}></div>
        </>
    );
};

export default Sidebar;
