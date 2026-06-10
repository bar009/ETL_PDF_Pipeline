import { ExternalLink, ListChecks } from 'lucide-react';

export default function InsightPanel({ entry, currentMode }) {
  return (
    <article className={`detail-panel detail-panel--${entry.degree}`} aria-labelledby="detailTitle">
      <div className="detail-panel__header">
        <span>{entry.categoryLabel}</span>
        <strong>{entry.status}</strong>
      </div>

      <h2 id="detailTitle">{entry.title}</h2>
      <p className="detail-summary">{entry.summary}</p>

      <section className="detail-section">
        <h3>{currentMode.detailLabel}</h3>
        <p>{entry.body}</p>
      </section>

      <section className="detail-source">
        <div>
          <span>מקור</span>
          <strong>{entry.source}</strong>
        </div>
        <button type="button" aria-label="פתיחת מקור" title="פתיחת מקור">
          <ExternalLink size={17} />
        </button>
      </section>

      <section className="related-strip">
        <div className="related-strip__title">
          <ListChecks size={17} aria-hidden="true" />
          <span>קשרים</span>
        </div>
        <div className="related-chips">
          {entry.related.map(item => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </section>
    </article>
  );
}
