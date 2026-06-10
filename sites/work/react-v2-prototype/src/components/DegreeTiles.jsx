import { useMemo } from 'react';
import { ArrowLeft } from 'lucide-react';

const PREVIEW_COUNT = 3;

const TYPE_LABELS = {
  hub: 'hub',
  topic: 'נושא',
  symbol: 'סמל',
  ceremony: 'טקס',
  connector: 'גשר',
  concept: 'מושג',
  category: 'קטגוריה',
  glossary: 'מילון',
  book: 'ספר',
  chapter: 'פרק'
};

function pickPreviewEntries(entries) {
  const sorted = [...entries].sort((a, b) => {
    const aHub = a.type === 'hub' ? 0 : 1;
    const bHub = b.type === 'hub' ? 0 : 1;
    if (aHub !== bHub) return aHub - bHub;
    const aOrder = a.sourceOrder ?? Number.MAX_SAFE_INTEGER;
    const bOrder = b.sourceOrder ?? Number.MAX_SAFE_INTEGER;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return a.title.localeCompare(b.title, 'he');
  });
  return sorted.slice(0, PREVIEW_COUNT);
}

export default function DegreeTiles({
  degree,
  entries,
  onSelectCategory,
  onSelectEntry
}) {
  const grouped = useMemo(() => {
    const byCategory = new Map();
    entries.forEach(entry => {
      const arr = byCategory.get(entry.category) ?? [];
      arr.push(entry);
      byCategory.set(entry.category, arr);
    });
    return byCategory;
  }, [entries]);

  const realCategories = degree.categories.filter(cat => cat.id !== 'all');

  return (
    <div className="degree-tiles" role="list">
      {realCategories.map(category => {
        const categoryEntries = grouped.get(category.id) ?? [];
        const previews = pickPreviewEntries(categoryEntries);
        const count = categoryEntries.length;

        return (
          <div
            key={category.id}
            role="listitem"
            className="degree-tile"
            style={{ '--tile-tone': degree.tone }}
          >
            <button
              type="button"
              className="degree-tile__body"
              onClick={() => onSelectCategory(category.id)}
              aria-label={`פתיחת רשימת ${category.label}`}
            >
              <div className="degree-tile__head">
                <h3 className="degree-tile__title">{category.label}</h3>
                <span className="degree-tile__count">
                  {count > 0 ? `${count} ערכים` : 'ריק'}
                </span>
              </div>
              {category.description && (
                <p className="degree-tile__description">{category.description}</p>
              )}
              <span className="degree-tile__open">
                <ArrowLeft size={14} aria-hidden="true" />
                <span>פתיחת הרשימה</span>
              </span>
            </button>

            {previews.length > 0 && (
              <div className="degree-tile__previews">
                {previews.map(entry => (
                  <button
                    key={entry.slug}
                    type="button"
                    className="degree-tile__preview"
                    onClick={event => {
                      event.stopPropagation();
                      onSelectEntry(entry);
                    }}
                    title={entry.summary}
                  >
                    <span className="degree-tile__preview-title">{entry.title}</span>
                    <span className="degree-tile__preview-type">
                      {TYPE_LABELS[entry.type] ?? entry.type}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
