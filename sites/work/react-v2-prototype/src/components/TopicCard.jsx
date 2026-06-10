import { ArrowLeft, Bookmark } from 'lucide-react';

export default function TopicCard({ entry, isSelected, onSelect }) {
  return (
    <button
      type="button"
      className={`topic-row${isSelected ? ' is-selected' : ''}`}
      aria-current={isSelected ? 'true' : undefined}
      onClick={() => onSelect(entry.slug)}
    >
      <span className="topic-row__icon" aria-hidden="true">
        <Bookmark size={17} />
      </span>
      <span className="topic-row__copy">
        <span className="topic-row__meta">
          {entry.categoryLabel} · {entry.status}
        </span>
        <strong>{entry.title}</strong>
        <small>{entry.summary}</small>
      </span>
      <ArrowLeft className="topic-row__arrow" size={18} aria-hidden="true" />
    </button>
  );
}
