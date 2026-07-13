import React from 'react';
import { UploadCloud, FileCheck2, LayoutList, ShieldCheck } from 'lucide-react';

export type TabType = 'upload' | 'screening' | 'results';

interface NavbarProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onSelectTab }) => {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">
          <ShieldCheck className="navbar-brand-icon" size={28} />
          <span>Smart Screener</span>
        </div>
        <nav className="nav-tabs">
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => onSelectTab('upload')}
          >
            <UploadCloud size={16} />
            Upload Resume
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'screening' ? 'active' : ''}`}
            onClick={() => onSelectTab('screening')}
          >
            <FileCheck2 size={16} />
            Screening
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => onSelectTab('results')}
          >
            <LayoutList size={16} />
            Results
          </button>
        </nav>
      </div>
    </header>
  );
};
