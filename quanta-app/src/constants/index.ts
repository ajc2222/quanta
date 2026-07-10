import type { NavSection, ReportFilterState } from '../types';

export const NAV_SECTIONS: NavSection[] = [
  {
    label: 'ICT REPORTS',
    items: [
      { id: 'fvg', label: 'Fair Value Gaps', path: '/reports/fvg' },
      { id: 'ob', label: 'Order Blocks', path: '/reports/order-blocks' },
      { id: 'killzones', label: 'Killzones', path: '/reports/killzones' },
      { id: 'liq-sweeps', label: 'Liquidity Sweeps', path: '/reports/liq-sweeps' },
      { id: 'po3', label: 'Power of 3', path: '/reports/power-of-3' },
      { id: 'key-opens', label: 'Key Opens', path: '/reports/key-opens' },
      { id: 'opening-gaps', label: 'Opening Gaps', path: '/reports/opening-gaps' },
      { id: 'news', label: 'News Data H/L', path: '/reports/news' },
      { id: 'macros', label: 'Macros', path: '/reports/macros' },
    ],
  },
  {
    label: 'OPTIONS & GEX',
    items: [
      { id: 'gex-levels', label: 'GEX Levels', path: '/options/gex-levels' },
      { id: 'gex-historical', label: 'Historical Stats', path: '/options/historical' },
      { id: 'put-call', label: 'Put/Call Ratio', path: '/options/put-call-ratio' },
      { id: 'oi-strike', label: 'OI by Strike', path: '/options/oi-by-strike' },
    ],
  },
  {
    label: 'QT REPORTS',
    items: [
      { id: 'qt-quarterly', label: 'Quarterly Shifts', path: '/qt/quarterly', badge: 'soon' },
      { id: 'qt-weekly', label: 'Weekly Range Stats', path: '/qt/weekly', badge: 'soon' },
      { id: 'qt-amd', label: 'AMD Cycle Data', path: '/qt/amd', badge: 'soon' },
      { id: 'qt-nwog', label: 'NWOG / NDOG', path: '/qt/nwog', badge: 'soon' },
    ],
  },
];

export const DEFAULT_FILTERS: ReportFilterState = {
  instruments: ['ES', 'NQ'],
  lookback: '1y',
  session: 'All',
};

export const INSTRUMENTS = ['ES', 'NQ', 'GC', 'CL', '6E', 'ZB', 'ZN'];

export const LOOKBACK_OPTIONS = [
  { value: '3mo' as const, label: '3mo' },
  { value: '6mo' as const, label: '6mo' },
  { value: '1y' as const, label: '1yr' },
  { value: 'custom' as const, label: 'Custom' },
];

export const SESSION_OPTIONS = [
  'All', 'London', 'NY AM', 'NY PM', 'Overnight', 'Globex',
];
