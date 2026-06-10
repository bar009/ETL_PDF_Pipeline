import { BookOpen, Languages, LibraryBig, Lock, Search } from 'lucide-react';

export default function ShellHeader({
  accessState,
  locales,
  locale,
  text,
  modes,
  currentModeId,
  legalModeIds,
  navigatesModeIds,
  hideModeTabs = false,
  currentDegree,
  query,
  onQueryChange,
  onLocaleChange,
  onModeChange
}) {
  const legalSet = new Set(legalModeIds ?? modes.map(m => m.id));
  const navigatesSet = new Set(navigatesModeIds ?? []);
  return (
    <header className="shell-header">
      <a className="brand" href="/" aria-label={text.brandName}>
        <span className="brand-mark" aria-hidden="true">
          <BookOpen size={21} />
        </span>
        <span>
          <strong>{text.brandName}</strong>
          <small>{text.degreeDescription(currentDegree)}</small>
        </span>
      </a>

      <div className="global-search">
        <Search size={18} aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={event => onQueryChange(event.target.value)}
          placeholder={text.searchPlaceholder}
          aria-label={text.searchLabel}
        />
      </div>

      {!hideModeTabs && (
      <nav className="mode-tabs" aria-label={text.modeNavLabel}>
        {modes.map(mode => {
          const isLegal = legalSet.has(mode.id);
          const isActive = mode.id === currentModeId;
          const navigates = navigatesSet.has(mode.id);
          const titleSuffix = navigates ? ' · פותח את הספרייה' : '';
          return (
            <button
              key={mode.id}
              type="button"
              className={`${isActive ? 'is-active' : ''}${navigates ? ' mode-tab--navigates' : ''}`.trim()}
              aria-pressed={isActive}
              disabled={!isLegal && !isActive}
              onClick={() => onModeChange(mode.id)}
              title={`${mode.description}${titleSuffix}`}
            >
              {mode.id === 'research' ? <LibraryBig size={16} /> : <BookOpen size={16} />}
              <span>{mode.label}</span>
            </button>
          );
        })}
      </nav>
      )}

      <div className="language-switcher" aria-label={text.languageLabel}>
        <Languages size={16} aria-hidden="true" />
        {locales.map(option => (
          <button
            key={option.id}
            type="button"
            className={option.id === locale.id ? 'is-active' : ''}
            aria-label={option.label}
            aria-pressed={option.id === locale.id}
            onClick={() => onLocaleChange(option.id)}
          >
            {option.shortLabel}
          </button>
        ))}
      </div>

      <button
        className="access-button"
        type="button"
        aria-label={accessState.label}
        title={accessState.label}
      >
        <Lock size={17} />
      </button>
    </header>
  );
}
