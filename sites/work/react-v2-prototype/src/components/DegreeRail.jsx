import { Archive, GraduationCap, LibraryBig, Layers } from 'lucide-react';

const icons = {
  level1: GraduationCap,
  level2: Layers,
  level3: Archive,
  library: LibraryBig
};

export default function DegreeRail({ degrees, currentDegreeId, onSelectDegree }) {
  return (
    <aside className="degree-rail" aria-label="ניווט דרגות">
      {degrees.map(degree => {
        const Icon = icons[degree.id] ?? Layers;
        const isActive = degree.id === currentDegreeId;

        return (
          <button
            key={degree.id}
            type="button"
            className={`degree-nav-item${isActive ? ' is-active' : ''}`}
            style={{ '--degree-tone': degree.tone }}
            aria-current={isActive ? 'page' : undefined}
            onClick={() => onSelectDegree(degree.id)}
          >
            <span className="degree-icon" aria-hidden="true">
              <Icon size={18} />
            </span>
            <span className="degree-copy">
              <strong>{degree.label}</strong>
              <small>{degree.title}</small>
            </span>
          </button>
        );
      })}
    </aside>
  );
}
