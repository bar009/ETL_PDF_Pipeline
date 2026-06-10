import {
  ArrowLeft,
  ArrowRight,
  BookMarked,
  ExternalLink,
  FileText,
  Link2,
  Route
} from 'lucide-react';

const researchOutline = [
  { id: 'sourceIdentity', label: 'זהות המקור' },
  { id: 'sourceRecord', label: 'רשומה ביבליוגרפית' },
  { id: 'sourceUse', label: 'איך להשתמש במקור' },
  { id: 'sourceRelations', label: 'קשרים לערכים' }
];

export default function SourceDetailPage({
  currentDegree,
  entry,
  siblingEntries,
  onBack,
  onSelectEntry
}) {
  const currentIndex = siblingEntries.findIndex(item => item.slug === entry.slug);
  const recordIndex = currentIndex >= 0 ? currentIndex + 1 : 1;
  const previousEntry = currentIndex > 0 ? siblingEntries[currentIndex - 1] : null;
  const nextEntry = currentIndex >= 0 && currentIndex < siblingEntries.length - 1
    ? siblingEntries[currentIndex + 1]
    : null;

  const metadataRows = [
    ['סוג מקור', entry.sourceKind ?? entry.type],
    ['שנה', entry.sourceYear ?? 'לא צוין'],
    ['כיסוי', entry.coverage ?? currentDegree.summary],
    ['קטגוריה', entry.categoryLabel],
    ['סטטוס', entry.status],
    ['שורש נתונים', entry.source]
  ];

  return (
    <section className="source-detail-page" aria-labelledby="sourceTitle">
      <aside className="source-detail-context" aria-label="מיקום המקור בספרייה">
        <button className="source-back" type="button" onClick={onBack}>
          <ArrowRight size={16} aria-hidden="true" />
          <span>חזרה לספרייה</span>
        </button>

        <div className="source-context-card">
          <span>איפה אנחנו</span>
          <strong>{currentDegree.title}</strong>
          <p>{entry.categoryLabel} · {entry.status}</p>
        </div>

        <div className="source-record-count" aria-label="מיקום ברשימת המקורות">
          <Route size={18} aria-hidden="true" />
          <div>
            <strong>{recordIndex} מתוך {siblingEntries.length}</strong>
            <span>רשומה בתוך משטח המחקר</span>
          </div>
        </div>

        <nav className="source-outline" aria-label="מבנה רשומת המקור">
          <span>מבנה הרשומה</span>
          {researchOutline.map(item => (
            <a key={item.id} href={`#${item.id}`}>
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      <article className="source-detail-body">
        <div className="source-kicker">
          <BookMarked size={17} aria-hidden="true" />
          <span>מחקר · מקור, עדות והשוואה</span>
        </div>

        <header id="sourceIdentity" className="source-detail-hero">
          <h1 id="sourceTitle">{entry.title}</h1>
          <p>{entry.summary}</p>
        </header>

        <section id="sourceRecord" className="source-record-section" aria-labelledby="sourceRecordTitle">
          <div className="source-section-heading">
            <FileText size={18} aria-hidden="true" />
            <h2 id="sourceRecordTitle">רשומת מקור</h2>
          </div>

          <dl className="source-facts">
            {metadataRows.map(([label, value]) => (
              <div key={label} className="source-fact-row">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section id="sourceUse" className="source-note-section" aria-labelledby="sourceUseTitle">
          <div className="source-section-heading">
            <ExternalLink size={18} aria-hidden="true" />
            <h2 id="sourceUseTitle">איך להשתמש במקור</h2>
          </div>
          <p>{entry.body}</p>
        </section>

        <section id="sourceRelations" className="source-related-section" aria-labelledby="sourceRelationsTitle">
          <div className="source-section-heading">
            <Link2 size={18} aria-hidden="true" />
            <h2 id="sourceRelationsTitle">קשרים לערכים ולמקורות</h2>
          </div>
          <div className="related-chips">
            {entry.related.map(item => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </section>

        <footer className="source-neighbors" aria-label="ניווט בין מקורות">
          <button type="button" disabled={!previousEntry} onClick={() => previousEntry && onSelectEntry(previousEntry)}>
            <ArrowRight size={16} aria-hidden="true" />
            <span>{previousEntry ? previousEntry.title : 'אין מקור קודם'}</span>
          </button>
          <button type="button" disabled={!nextEntry} onClick={() => nextEntry && onSelectEntry(nextEntry)}>
            <span>{nextEntry ? nextEntry.title : 'אין מקור הבא'}</span>
            <ArrowLeft size={16} aria-hidden="true" />
          </button>
        </footer>
      </article>
    </section>
  );
}
