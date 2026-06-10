import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Archive, ArrowLeft, BookMarked } from 'lucide-react';

const ROW_HEIGHT = 96;
const MAX_LIST_HEIGHT = 456;

export default function LibrarySurface({ entries, selectedSlug, onSelect }) {
  const listRef = useRef(null);
  const rowVirtualizer = useVirtualizer({
    count: entries.length,
    getScrollElement: () => listRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 6
  });

  const listHeight = Math.max(ROW_HEIGHT, Math.min(MAX_LIST_HEIGHT, entries.length * ROW_HEIGHT));

  return (
    <section className="library-surface">
      <div className="library-head">
        <div>
          <span>ספריה</span>
          <h2>מקורות וארכיון</h2>
        </div>
        <Archive size={24} aria-hidden="true" />
      </div>

      {entries.length ? (
        <div className="source-list" ref={listRef} role="list" style={{ height: listHeight }}>
          <div className="source-list__spacer" style={{ height: rowVirtualizer.getTotalSize() }}>
            {rowVirtualizer.getVirtualItems().map(virtualRow => {
              const entry = entries[virtualRow.index];

              return (
                <button
                  key={entry.slug}
                  type="button"
                  role="listitem"
                  className={`source-row${entry.slug === selectedSlug ? ' is-selected' : ''}`}
                  aria-current={entry.slug === selectedSlug ? 'true' : undefined}
                  onClick={() => onSelect(entry)}
                  style={{
                    height: virtualRow.size - 8,
                    transform: `translateY(${virtualRow.start}px)`
                  }}
                >
                  <span className="source-row__icon" aria-hidden="true">
                    <BookMarked size={18} />
                  </span>
                  <span className="source-row__main">
                    <strong>{entry.title}</strong>
                    <small>{entry.summary}</small>
                  </span>
                  <span className="source-row__meta">
                    <span>{entry.sourceKind}</span>
                    <span>{entry.sourceYear}</span>
                    <span>{entry.coverage}</span>
                  </span>
                  <ArrowLeft size={18} aria-hidden="true" />
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="empty-state">לא נמצאו מקורות מתאימים.</div>
      )}
    </section>
  );
}
