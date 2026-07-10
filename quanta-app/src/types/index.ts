export interface ReportFilterState {
  instruments: string[];
  lookback: '3mo' | '6mo' | '1y' | 'custom';
  session: string;
}

export interface StatCardData {
  label: string;
  value: string;
  secondary?: string;
  status?: 'healthy' | 'low' | 'warning';
}

export interface DataRow {
  [key: string]: string | number;
}

export interface DataTableColumn {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
  renderBar?: boolean;
}

export interface SubreportTab {
  id: string;
  label: string;
}

export interface ChartBar {
  label: string;
  value: number;
  color?: string;
}

export interface NavItem {
  id: string;
  label: string;
  path: string;
  badge?: 'soon';
}

export interface NavSection {
  label: string;
  items: NavItem[];
}
