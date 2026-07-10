import type { DataTableColumn, DataRow } from '../../types';

interface DataTableProps {
  columns: DataTableColumn[];
  rows: DataRow[];
}

export default function DataTable({ columns, rows }: DataTableProps) {
  const maxValues: Record<string, number> = {};
  for (const col of columns) {
    if (col.renderBar) {
      maxValues[col.key] = Math.max(...rows.map(r => Number(r[col.key]) || 0), 1);
    }
  }

  const alignClass = (align?: 'left' | 'right' | 'center') => {
    if (align === 'right') return 'text-right';
    if (align === 'center') return 'text-center';
    return 'text-left';
  };

  return (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          {columns.map(col => (
            <th
              key={col.key}
              className={`text-[10px] uppercase tracking-wider text-muted font-normal pb-2 px-3 ${alignClass(col.align)}`}
            >
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="hover:bg-hover transition-colors duration-100">
            {columns.map(col => {
              const val = row[col.key];
              const isNumber = typeof val === 'number';
              const displayVal = isNumber ? val.toLocaleString() : String(val);

              return (
                <td
                  key={col.key}
                  className={`py-2.5 px-3 text-[13px] border-b border-border ${isNumber ? 'font-mono text-right' : ''} ${alignClass(col.align)}`}
                >
                  {col.renderBar && isNumber ? (
                    <span className="inline-flex items-center gap-2 w-full justify-end">
                      <span>{displayVal}</span>
                      <span className="inline-block w-12 h-[6px] bg-border">
                        <span
                          className="block h-full bg-accent"
                          style={{ width: `${(Number(val) / maxValues[col.key]) * 100}%` }}
                        />
                      </span>
                    </span>
                  ) : (
                    displayVal
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
