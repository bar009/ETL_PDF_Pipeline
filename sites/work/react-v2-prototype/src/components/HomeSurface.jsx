import { ArrowLeft, BookOpen, LibraryBig, Map, Route } from 'lucide-react';

export default function HomeSurface({
  degrees,
  modes,
  entries,
  text,
  onSelectDegree,
  onSelectEntry,
  onSelectMode
}) {
  const learningDegrees = degrees.filter(degree => degree.id !== 'library');
  const libraryDegree = degrees.find(degree => degree.id === 'library');
  const recommendedEntry = entries.find(entry => entry.degree === 'level1') ?? entries[0];
  const topicCount = entries.filter(entry => entry.degree !== 'library').length;
  const sourceCount = entries.filter(entry => entry.degree === 'library').length;

  return (
    <section id="mainContent" className="home-surface" tabIndex="-1" aria-labelledby="homeTitle">
      <div className="home-hero">
        <div className="home-hero__copy">
          <span>{text.homeEyebrow}</span>
          <h1 id="homeTitle">{text.homeTitle}</h1>
          <p>{text.homeSummary}</p>
        </div>
        <div className="home-hero__actions">
          <button type="button" className="primary-action" onClick={() => onSelectDegree('level1')}>
            <BookOpen size={18} aria-hidden="true" />
            <span>{text.homeStartAction}</span>
          </button>
          <button type="button" onClick={() => libraryDegree && onSelectDegree(libraryDegree.id)}>
            <LibraryBig size={18} aria-hidden="true" />
            <span>{text.homeResearchAction}</span>
          </button>
        </div>
      </div>

      <div className="home-grid">
        <section className="home-panel home-panel--path" aria-labelledby="homePathTitle">
          <div className="home-panel__title">
            <Route size={18} aria-hidden="true" />
            <h2 id="homePathTitle">{text.homePathTitle}</h2>
          </div>
          <div className="home-degree-list">
            {learningDegrees.map(degree => (
              <button
                key={degree.id}
                type="button"
                className="home-degree-row"
                style={{ '--degree-tone': degree.tone }}
                onClick={() => onSelectDegree(degree.id)}
              >
                <span className="home-degree-row__mark" aria-hidden="true" />
                <span>
                  <strong>{degree.label}</strong>
                  <small>{degree.title}</small>
                </span>
                <ArrowLeft size={17} aria-hidden="true" />
              </button>
            ))}
          </div>
        </section>

        <section className="home-panel" aria-labelledby="homeModeTitle">
          <div className="home-panel__title">
            <Map size={18} aria-hidden="true" />
            <h2 id="homeModeTitle">{text.homeModeTitle}</h2>
          </div>
          <div className="home-mode-list">
            {modes.map(mode => (
              <button key={mode.id} type="button" onClick={() => onSelectMode(mode.id)}>
                <strong>{mode.label}</strong>
                <span>{mode.description}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="home-panel home-panel--featured" aria-labelledby="homeFeaturedTitle">
          <div className="home-panel__title">
            <BookOpen size={18} aria-hidden="true" />
            <h2 id="homeFeaturedTitle">{text.homeFeaturedTitle}</h2>
          </div>
          <button type="button" className="home-featured-entry" onClick={() => onSelectEntry(recommendedEntry)}>
            <span>{recommendedEntry.categoryLabel}</span>
            <strong>{recommendedEntry.title}</strong>
            <small>{recommendedEntry.summary}</small>
          </button>
        </section>

        <section className="home-panel home-panel--research" aria-labelledby="homeResearchTitle">
          <div className="home-panel__title">
            <LibraryBig size={18} aria-hidden="true" />
            <h2 id="homeResearchTitle">{text.homeResearchTitle}</h2>
          </div>
          <div className="home-stats">
            <span>
              <strong>{topicCount}</strong>
              {text.homeTopicCount}
            </span>
            <span>
              <strong>{sourceCount}</strong>
              {text.homeSourceCount}
            </span>
          </div>
          <button type="button" onClick={() => libraryDegree && onSelectDegree(libraryDegree.id)}>
            {text.homeOpenLibrary}
          </button>
        </section>
      </div>
    </section>
  );
}
