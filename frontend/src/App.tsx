import React, { useState } from 'react';
import { Navbar, TabType } from './components/Navbar';
import { UploadView } from './components/UploadView';
import { ScreeningView } from './components/ScreeningView';
import { ResultsView } from './components/ResultsView';
import { ResultDetail } from './components/ResultDetail';
import { ScreeningResult } from './types/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('upload');
  const [currentResumeId, setCurrentResumeId] = useState<number>(1);
  const [activeScreeningResult, setActiveScreeningResult] = useState<ScreeningResult | null>(null);

  const handleUploadSuccess = (assignedId: number) => {
    setCurrentResumeId(assignedId);
    setActiveTab('screening');
  };

  const handleScreeningComplete = (result: ScreeningResult) => {
    setActiveScreeningResult(result);
    setActiveTab('results');
  };

  const handleSelectTab = (tab: TabType) => {
    if (tab === 'results' && activeTab !== 'results') {
      // If manually clicking Results tab, clear single detail view to show summary list first
      setActiveScreeningResult(null);
    }
    setActiveTab(tab);
  };

  return (
    <div className="app-container">
      <Navbar activeTab={activeTab} onSelectTab={handleSelectTab} />
      
      <main className="main-content">
        {activeTab === 'upload' && (
          <UploadView
            currentResumeId={currentResumeId}
            onUploadSuccess={handleUploadSuccess}
          />
        )}

        {activeTab === 'screening' && (
          <ScreeningView
            initialResumeId={currentResumeId}
            onScreeningComplete={handleScreeningComplete}
          />
        )}

        {activeTab === 'results' && (
          activeScreeningResult ? (
            <ResultDetail
              result={activeScreeningResult}
              onBack={() => setActiveScreeningResult(null)}
            />
          ) : (
            <ResultsView />
          )
        )}
      </main>

      <footer style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-dim)', fontSize: '0.85rem', borderTop: '1px solid var(--border-color)', marginTop: 'auto' }}>
        Smart Resume Screener &copy; {new Date().getFullYear()} — Production Recruiter Dashboard
      </footer>
    </div>
  );
};
