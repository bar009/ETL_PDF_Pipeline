import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { LayoutGrid, ListFilter, Rows3 } from 'lucide-react';
import ArticlePage from './components/ArticlePage.jsx';
import DegreeRail from './components/DegreeRail.jsx';
import DegreeTiles from './components/DegreeTiles.jsx';
import HomeSurface from './components/HomeSurface.jsx';
import LibrarySurface from './components/LibrarySurface.jsx';
import ShellHeader from './components/ShellHeader.jsx';
import SourceDetailPage from './components/SourceDetailPage.jsx';
import TopicCard from './components/TopicCard.jsx';
import { modes } from './data/demoContent.js';
import { loadContent } from './lib/contentAdapter.js';
import { getAccessState } from './lib/access.js';
import { getLocale, getPageMeta, locales } from './lib/locales.js';
import { filterEntries } from './lib/search.js';
import { degreePath, entryPath, parseRoute } from './lib/routes.js';
import { legalRefinements, resolveMode } from './lib/modeResolver.js';

function getCurrentPath() {
  return window.location.pathname || '/';
}

function replaceBrowserPath(path, state = null) {
  window.history.replaceState(state, '', path);
}

function pushBrowserPath(path, state = null) {
  window.history.pushState(state, '', path);
}

function upsertMeta(selector, attributes) {
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement('meta');
    document.head.appendChild(element);
  }

  Object.entries(attributes).forEach(([name, value]) => {
    element.setAttribute(name, value);
  });
}

function upsertCanonicalLink(href) {
  let element = document.head.querySelector('link[rel="canonical"]');
  if (!element) {
    element = document.createElement('link');
    element.setAttribute('rel', 'canonical');
    document.head.appendChild(element);
  }

  element.setAttribute('href', href);
}

export default function App() {
  const [pathname, setPathname] = useState(getCurrentPath);
  const [lastNavSource, setLastNavSource] = useState('path-load');
  const [lastFromDegreeId, setLastFromDegreeId] = useState(null);
  const [lastRefinement, setLastRefinement] = useState(null);
  const [prevResolvedMode, setPrevResolvedMode] = useState('encyclopedia');
  const [currentCategoryId, setCurrentCategoryId] = useState('all');
  const [currentLocaleId, setCurrentLocaleId] = useState('he');
  const [query, setQuery] = useState('');
  const [content, setContent] = useState({ degrees: [], entries: [] });
  const [contentStatus, setContentStatus] = useState('loading'); // 'loading' | 'ready' | 'error'
  const [contentError, setContentError] = useState(null);
  const [degreeView, setDegreeView] = useState(() => {
    if (typeof window === 'undefined') return 'tiles';
    return window.localStorage?.getItem('react-v2-prototype:degree-view') ?? 'tiles';
  });

  function selectDegreeView(nextView) {
    setDegreeView(nextView);
    if (typeof window !== 'undefined') {
      window.localStorage?.setItem('react-v2-prototype:degree-view', nextView);
    }
  }
  const deferredQuery = useDeferredValue(query);
  const locale = getLocale(currentLocaleId);
  const text = locale.text;

  useEffect(() => {
    let cancelled = false;
    setContentStatus('loading');
    loadContent()
      .then(data => {
        if (cancelled) return;
        setContent(data);
        setContentStatus('ready');
      })
      .catch(err => {
        if (cancelled) return;
        console.error('contentAdapter load failed', err);
        setContentError(err);
        setContentStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { degrees, entries } = content;
  const hasContent = degrees.length > 0 && entries.length > 0;

  const route = parseRoute(pathname, { degrees, entries });
  const currentDegreeId = route.degreeId;
  const currentDegree = degrees.find(degree => degree.id === currentDegreeId)
    ?? degrees[0]
    ?? { id: '', label: '', title: '', tone: '#666', summary: '', categories: [{ id: 'all', label: 'הכל' }] };
  const currentModeId = useMemo(
    () => resolveMode({
      route,
      source: lastNavSource,
      fromDegreeId: lastFromDegreeId,
      refinement: lastRefinement,
      prevResolved: prevResolvedMode
    }),
    [route.degreeId, route.slug, lastNavSource, lastFromDegreeId, lastRefinement, prevResolvedMode]
  );
  const currentMode = modes.find(mode => mode.id === currentModeId) ?? modes[0];
  const isLibrary = currentDegreeId === 'library';
  const isHomeRoute = pathname === '/';
  const isArticleRoute = Boolean(route.slug);
  const isSourceRoute = isLibrary && isArticleRoute;
  const accessState = getAccessState();

  const degreeEntries = useMemo(
    () => entries.filter(entry => entry.degree === currentDegreeId),
    [currentDegreeId, entries]
  );

  const filteredEntries = useMemo(
    () => filterEntries(degreeEntries, { categoryId: currentCategoryId, query: deferredQuery }),
    [currentCategoryId, deferredQuery, degreeEntries]
  );

  const routeEntry = degreeEntries.find(entry => entry.slug === route.slug) ?? null;
  const selectedEntry = routeEntry
    ?? filteredEntries[0]
    ?? degreeEntries[0]
    ?? entries[0]
    ?? { slug: '', title: '', summary: '', body: '', source: '', related: [], categoryLabel: '', status: '', type: '', degree: '' };
  const pageMeta = useMemo(
    () => getPageMeta({
      currentDegree,
      entry: selectedEntry,
      isArticleRoute,
      isHomeRoute,
      isSourceRoute,
      locale,
      pathname
    }),
    [currentDegree, isArticleRoute, isHomeRoute, isSourceRoute, locale, pathname, selectedEntry]
  );

  useEffect(() => {
    function handlePopState(event) {
      const restored = event.state;
      setLastNavSource(restored?.source ?? 'path-load');
      setLastFromDegreeId(restored?.fromDegreeId ?? null);
      setLastRefinement(restored?.refinement ?? null);
      setPathname(getCurrentPath());
    }

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (!route.canonicalPath || route.canonicalPath === pathname) return;
    replaceBrowserPath(route.canonicalPath);
    setPathname(route.canonicalPath);
  }, [pathname, route.canonicalPath]);

  useEffect(() => {
    document.documentElement.lang = locale.code;
    document.documentElement.dir = locale.dir;
  }, [locale]);

  useEffect(() => {
    document.title = pageMeta.title;
    const canonicalUrl = new URL(pageMeta.canonicalPath, window.location.origin).href;

    upsertMeta('meta[name="description"]', { name: 'description', content: pageMeta.description });
    upsertCanonicalLink(canonicalUrl);
    upsertMeta('meta[property="og:title"]', { property: 'og:title', content: pageMeta.title });
    upsertMeta('meta[property="og:description"]', { property: 'og:description', content: pageMeta.description });
    upsertMeta('meta[property="og:type"]', { property: 'og:type', content: pageMeta.ogType });
    upsertMeta('meta[property="og:url"]', { property: 'og:url', content: canonicalUrl });
    upsertMeta('meta[property="og:locale"]', { property: 'og:locale', content: locale.code });
  }, [pageMeta]);

  useEffect(() => {
    setPrevResolvedMode(currentModeId);
  }, [currentModeId]);

  function navigate(path, { replace = false, navState = null } = {}) {
    if (path === pathname) return;
    if (replace) replaceBrowserPath(path, navState);
    else pushBrowserPath(path, navState);
    setPathname(path);
  }

  function selectDegree(nextDegreeId, source = 'degree-tab') {
    startTransition(() => {
      setCurrentCategoryId('all');
      const navState = { source, fromDegreeId: currentDegreeId, refinement: null };
      setLastNavSource(source);
      setLastFromDegreeId(currentDegreeId);
      setLastRefinement(null);
      navigate(degreePath(nextDegreeId), { navState });
    });
  }

  function selectEntry(entry, source = 'internal-link') {
    startTransition(() => {
      const navState = { source, fromDegreeId: currentDegreeId, refinement: null };
      setLastNavSource(source);
      setLastFromDegreeId(currentDegreeId);
      setLastRefinement(null);
      navigate(entryPath(entry), { navState });
    });
  }

  function applyRefinement(nextModeId) {
    const legal = legalRefinements(currentDegreeId);
    if (!legal.includes(nextModeId)) return;
    startTransition(() => {
      setLastNavSource('mode-tab-refinement');
      setLastRefinement(nextModeId);
      window.history.replaceState(
        { source: 'mode-tab-refinement', fromDegreeId: lastFromDegreeId, refinement: nextModeId },
        '',
        pathname
      );
    });
  }

  function handleModeTabClick(nextModeId) {
    if (nextModeId === currentModeId) return;
    // Research belongs to the library; clicking it from a degree-of-study route
    // jumps there rather than no-opping.
    if (nextModeId === 'research' && currentDegreeId !== 'library') {
      selectHomeMode('research');
      return;
    }
    applyRefinement(nextModeId);
  }

  function selectHomeMode(nextModeId) {
    startTransition(() => {
      const targetPath = nextModeId === 'research'
        ? degreePath('library')
        : degreePath(currentDegreeId);
      const navState = { source: 'home-mode-pick', fromDegreeId: currentDegreeId, refinement: nextModeId };
      setLastNavSource('home-mode-pick');
      setLastFromDegreeId(currentDegreeId);
      setLastRefinement(nextModeId);
      navigate(targetPath, { navState });
    });
  }

  function selectCategory(nextCategoryId) {
    startTransition(() => {
      setCurrentCategoryId(nextCategoryId);
    });
  }

  function selectLocale(nextLocaleId) {
    startTransition(() => {
      setCurrentLocaleId(nextLocaleId);
    });
  }

  if (contentStatus === 'loading' && !hasContent) {
    return (
      <main className="app-shell app-shell--loading" aria-busy="true">
        <div className="content-loading" role="status">
          <span>טוען נתונים…</span>
        </div>
      </main>
    );
  }

  if (contentStatus === 'error' && !hasContent) {
    return (
      <main className="app-shell app-shell--error">
        <div className="content-loading" role="alert">
          <strong>טעינת הנתונים נכשלה</strong>
          <p>{contentError?.message ?? 'שגיאה לא ידועה'}</p>
        </div>
      </main>
    );
  }

  return (
    <>
      <a className="skip-link" href="#mainContent">{text.skipLink}</a>
      <main className={`app-shell${isLibrary ? ' app-shell--library' : ''}`}>
        <ShellHeader
          accessState={accessState}
          locales={locales}
          locale={locale}
          text={text}
          modes={modes}
          currentModeId={currentModeId}
          legalModeIds={isLibrary ? ['research'] : ['learning', 'encyclopedia', 'research']}
          navigatesModeIds={isLibrary ? [] : ['research']}
          hideModeTabs={isHomeRoute}
          currentDegree={currentDegree}
          query={query}
          onQueryChange={setQuery}
          onLocaleChange={selectLocale}
          onModeChange={handleModeTabClick}
        />

        {!isArticleRoute && !isHomeRoute && (
          <section className="home-band">
            <div className="home-band__copy">
              <span>{currentDegree.label}</span>
              <h1>{currentDegree.title}</h1>
              <p>{currentDegree.summary}</p>
            </div>
            <div className="home-band__metric">
              <strong>{filteredEntries.length}</strong>
              <span aria-live="polite">{text.entriesShown}</span>
            </div>
          </section>
        )}

        {isHomeRoute ? (
          <HomeSurface
            degrees={degrees}
            modes={modes}
            entries={entries}
            text={text}
            onSelectDegree={degreeId => selectDegree(degreeId, 'degree-tile')}
            onSelectEntry={entry => selectEntry(entry, 'search-result')}
            onSelectMode={selectHomeMode}
          />
        ) : isSourceRoute ? (
          <div id="mainContent" tabIndex="-1">
            <SourceDetailPage
              currentDegree={currentDegree}
              entry={selectedEntry}
              siblingEntries={degreeEntries}
              onBack={() => navigate(degreePath(currentDegreeId))}
              onSelectEntry={selectEntry}
            />
          </div>
        ) : isArticleRoute ? (
          <div id="mainContent" tabIndex="-1">
            <ArticlePage
              currentDegree={currentDegree}
              currentMode={currentMode}
              entry={selectedEntry}
              siblingEntries={degreeEntries}
              onBack={() => navigate(degreePath(currentDegreeId))}
              onSelectEntry={selectEntry}
            />
          </div>
        ) : (
          <section className="workspace">
            <DegreeRail degrees={degrees} currentDegreeId={currentDegreeId} onSelectDegree={selectDegree} />

            <section id="mainContent" className="content-pane" tabIndex="-1">
              <div className="content-toolbar">
                <div className="toolbar-title">
                  <ListFilter size={18} aria-hidden="true" />
                  <span>{currentMode.label}</span>
                </div>

                <div className="category-tabs" aria-label={text.categoryFilterLabel}>
                  {currentDegree.categories.map(category => {
                    const isActive = category.id === currentCategoryId;
                    const isToggleable = isActive && category.id !== 'all';
                    return (
                      <button
                        key={category.id}
                        type="button"
                        data-cat={category.id}
                        className={isActive ? 'is-active' : ''}
                        aria-pressed={isActive}
                        title={isToggleable ? 'לחץ שוב לחזרה לכל הקטגוריות' : undefined}
                        onClick={() => selectCategory(isToggleable ? 'all' : category.id)}
                      >
                        {category.label}
                      </button>
                    );
                  })}
                </div>

                {!isLibrary && (
                  <div className="degree-view-switch" role="tablist" aria-label="צורת תצוגה">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={degreeView === 'tiles'}
                      className={degreeView === 'tiles' ? 'is-active' : ''}
                      onClick={() => selectDegreeView('tiles')}
                      title="תצוגת קוביות לפי קטגוריה"
                    >
                      <LayoutGrid size={15} aria-hidden="true" />
                      <span>קוביות</span>
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={degreeView === 'list'}
                      className={degreeView === 'list' ? 'is-active' : ''}
                      onClick={() => selectDegreeView('list')}
                      title="תצוגת רשימה"
                    >
                      <Rows3 size={15} aria-hidden="true" />
                      <span>רשימה</span>
                    </button>
                  </div>
                )}
              </div>

              {filteredEntries.length === 0 ? (
                <div className="empty-state" role="status">{text.noEntries}</div>
              ) : isLibrary ? (
                <LibrarySurface entries={filteredEntries} selectedSlug={route.slug} onSelect={selectEntry} />
              ) : degreeView === 'tiles' && currentCategoryId === 'all' ? (
                <DegreeTiles
                  degree={currentDegree}
                  entries={degreeEntries}
                  onSelectCategory={selectCategory}
                  onSelectEntry={selectEntry}
                />
              ) : (
                <div className="topic-list">
                  {filteredEntries.map(entry => (
                    <TopicCard
                      key={entry.slug}
                      entry={entry}
                      isSelected={entry.slug === route.slug}
                      onSelect={() => selectEntry(entry)}
                    />
                  ))}
                </div>
              )}
            </section>
          </section>
        )}
      </main>
    </>
  );
}
