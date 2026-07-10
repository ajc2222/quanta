import type { SubreportTab } from '../../types';

interface SubreportTabsProps {
  tabs: SubreportTab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export default function SubreportTabs({ tabs, activeTab, onTabChange }: SubreportTabsProps) {
  return (
    <div className="flex gap-0 border-b border-border">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`relative px-4 py-2.5 text-[13px] font-medium transition-colors duration-100 ${
            activeTab === tab.id
              ? 'text-text-primary'
              : 'text-muted hover:text-text-primary'
          }`}
        >
          {tab.label}
          {activeTab === tab.id && (
            <span className="absolute bottom-0 left-0 right-0 h-[3px] bg-accent" />
          )}
        </button>
      ))}
    </div>
  );
}
