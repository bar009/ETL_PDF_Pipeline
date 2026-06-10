import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  BookMarked,
  BookOpen,
  ChevronsLeft,
  ChevronsRight,
  ExternalLink,
  FileText,
  GripVertical,
  ListChecks,
  MapPin,
  MapPinned,
  Route
} from 'lucide-react';

const CONTEXT_WIDTH_STORAGE_KEY = 'react-v2-prototype:article-context-width';
const CONTEXT_COLLAPSED_STORAGE_KEY = 'react-v2-prototype:article-context-collapsed';
const CONTEXT_MIN_WIDTH = 200;
const CONTEXT_MAX_RATIO = 0.6;
const BODY_MIN_WIDTH = 320;

const outlineItems = [
  { id: 'overview', label: 'מה הערך הזה', Icon: FileText },
  { id: 'reading', label: 'מה להבין עכשיו', Icon: BookOpen },
  { id: 'source', label: 'מקור', Icon: BookMarked },
  { id: 'links', label: 'קשרים', Icon: ListChecks }
];

export default function ArticlePage({
  currentDegree,
  currentMode,
  entry,
  siblingEntries,
  onBack,
  onSelectEntry
}) {
  const currentIndex = siblingEntries.findIndex(item => item.slug === entry.slug);
  const progressIndex = currentIndex >= 0 ? currentIndex + 1 : 1;
  const previousEntry = currentIndex > 0 ? siblingEntries[currentIndex - 1] : null;
  const nextEntry = currentIndex >= 0 && currentIndex < siblingEntries.length - 1
    ? siblingEntries[currentIndex + 1]
    : null;

  const modeId = currentMode?.id ?? 'learning';
  const isLearning = modeId === 'learning';
  const isEncyclopedia = modeId === 'encyclopedia';
  const containerRef = useRef(null);
  const draggingRef = useRef(false);
  const [contextWidth, setContextWidth] = useState(() => {
    if (typeof window === 'undefined') return null;
    const stored = window.localStorage?.getItem(CONTEXT_WIDTH_STORAGE_KEY);
    const parsed = stored ? Number.parseFloat(stored) : NaN;
    return Number.isFinite(parsed) ? parsed : null;
  });
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage?.getItem(CONTEXT_COLLAPSED_STORAGE_KEY) === '1';
  });
  const [isNarrowViewport, setIsNarrowViewport] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia?.('(max-width: 1180px)').matches
  );

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined;
    const mq = window.matchMedia('(max-width: 1180px)');
    const handler = event => setIsNarrowViewport(event.matches);
    mq.addEventListener?.('change', handler);
    return () => mq.removeEventListener?.('change', handler);
  }, []);

  const persistCollapsed = useCallback(value => {
    setIsCollapsed(value);
    if (typeof window === 'undefined') return;
    if (value) window.localStorage?.setItem(CONTEXT_COLLAPSED_STORAGE_KEY, '1');
    else window.localStorage?.removeItem(CONTEXT_COLLAPSED_STORAGE_KEY);
  }, []);

  const clampWidth = useCallback(width => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return width;
    const max = Math.max(CONTEXT_MIN_WIDTH, rect.width - BODY_MIN_WIDTH);
    const upper = Math.min(max, rect.width * CONTEXT_MAX_RATIO);
    return Math.min(Math.max(width, CONTEXT_MIN_WIDTH), upper);
  }, []);

  const handlePointerDown = useCallback(event => {
    if (isCollapsed) return;
    event.preventDefault();
    draggingRef.current = true;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [isCollapsed]);

  const handlePointerMove = useCallback(event => {
    if (!draggingRef.current) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    // RTL: aside sits on the right edge; dragging the handle leftwards widens it.
    const next = clampWidth(rect.right - event.clientX);
    setContextWidth(next);
  }, [clampWidth]);

  const stopDragging = useCallback(() => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    if (contextWidth != null) {
      window.localStorage?.setItem(CONTEXT_WIDTH_STORAGE_KEY, String(Math.round(contextWidth)));
    }
  }, [contextWidth]);

  const handleResizerKeyDown = useCallback(event => {
    if (isCollapsed) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        persistCollapsed(false);
      }
      return;
    }
    const step = event.shiftKey ? 32 : 12;
    // RTL: ArrowLeft widens the right-hand aside, ArrowRight narrows it.
    let delta = 0;
    if (event.key === 'ArrowLeft') delta = step;
    else if (event.key === 'ArrowRight') delta = -step;
    else if (event.key === 'Home') {
      event.preventDefault();
      setContextWidth(null);
      window.localStorage?.removeItem(CONTEXT_WIDTH_STORAGE_KEY);
      return;
    } else return;
    event.preventDefault();
    setContextWidth(prev => {
      const rect = containerRef.current?.getBoundingClientRect();
      const base = prev ?? (rect ? rect.width * 0.32 : CONTEXT_MIN_WIDTH);
      const next = clampWidth(base + delta);
      window.localStorage?.setItem(CONTEXT_WIDTH_STORAGE_KEY, String(Math.round(next)));
      return next;
    });
  }, [clampWidth, isCollapsed, persistCollapsed]);

  useEffect(() => {
    const handleResize = () => {
      if (contextWidth == null) return;
      setContextWidth(prev => (prev == null ? prev : clampWidth(prev)));
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [contextWidth, clampWidth]);

  const collapsedActive = isCollapsed && !isNarrowViewport;
  const gridStyle = !collapsedActive && contextWidth != null
    ? { '--article-context-width': `${contextWidth}px` }
    : undefined;
  const pageClassName = `article-page article-page--resizable article-page--mode-${modeId}${collapsedActive ? ' article-page--context-collapsed' : ''}`;

  return (
    <section
      className={pageClassName}
      aria-labelledby="articleTitle"
      ref={containerRef}
      style={gridStyle}
    >
      <aside
        className={`article-context${collapsedActive ? ' article-context--rail' : ''}`}
        aria-label="מיקום הערך במסלול"
      >
        <div className="article-context__topbar">
          {collapsedActive ? (
            <button
              type="button"
              className="article-context__collapse article-context__collapse--expand"
              onClick={() => persistCollapsed(false)}
              aria-label="הרחבת הסיידבר"
              title="הרחבת הסיידבר"
            >
              <ChevronsLeft size={16} aria-hidden="true" />
            </button>
          ) : (
            <>
              <button className="article-back" type="button" onClick={onBack}>
                <ArrowRight size={16} aria-hidden="true" />
                <span>חזרה למפת הדרגה</span>
              </button>
              <button
                type="button"
                className="article-context__collapse"
                onClick={() => persistCollapsed(true)}
                aria-label="צמצום הסיידבר"
                title="צמצום הסיידבר"
              >
                <ChevronsRight size={16} aria-hidden="true" />
              </button>
            </>
          )}
        </div>

        {isCollapsed && (
          <nav className="article-context__rail" aria-label="ניווט מהיר">
            <button
              type="button"
              className="rail-button"
              onClick={onBack}
              aria-label="חזרה למפת הדרגה"
              title="חזרה למפת הדרגה"
            >
              <ArrowRight size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="rail-button"
              onClick={() => persistCollapsed(false)}
              aria-label={`איפה אנחנו · ${currentDegree.label}`}
              title={`איפה אנחנו · ${currentDegree.label}`}
            >
              <MapPin size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="rail-button"
              onClick={() => persistCollapsed(false)}
              aria-label={`התקדמות · ${progressIndex} מתוך ${siblingEntries.length}`}
              title={`התקדמות · ${progressIndex} מתוך ${siblingEntries.length}`}
            >
              <Route size={16} aria-hidden="true" />
            </button>
            <span className="rail-separator" aria-hidden="true" />
            {outlineItems.map(item => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className="rail-button"
                aria-label={item.label}
                title={item.label}
              >
                <item.Icon size={16} aria-hidden="true" />
              </a>
            ))}
          </nav>
        )}

        {!collapsedActive && (
          <>
            <div className="path-card">
              <span className="path-card__eyebrow">איפה אנחנו</span>
              <strong>{currentDegree.label} · {currentDegree.title}</strong>
              <p>{entry.categoryLabel} · {entry.status}</p>
            </div>

            {isLearning && (
              <div className="article-progress" aria-label="התקדמות למידה">
                <Route size={18} aria-hidden="true" />
                <div>
                  <strong>{progressIndex} מתוך {siblingEntries.length}</strong>
                  <span>מיקום הערך ברשימת הדרגה</span>
                </div>
              </div>
            )}

            <nav className="article-outline" aria-label="מבנה הערך">
              <span className="article-outline__title">מבנה הערך</span>
              {outlineItems.map(item => (
                <a key={item.id} href={`#${item.id}`}>
                  <item.Icon size={15} aria-hidden="true" />
                  <span>{item.label}</span>
                </a>
              ))}
            </nav>
          </>
        )}
      </aside>

      {!collapsedActive && (
        <div
          className="article-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="גרור לשינוי רוחב הסיידבר"
          aria-valuenow={contextWidth != null ? Math.round(contextWidth) : undefined}
          tabIndex={0}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={stopDragging}
          onPointerCancel={stopDragging}
          onDoubleClick={() => {
            setContextWidth(null);
            window.localStorage?.removeItem(CONTEXT_WIDTH_STORAGE_KEY);
          }}
          onKeyDown={handleResizerKeyDown}
          title="גרור לשינוי רוחב · דאבל־קליק לאיפוס"
        >
          <GripVertical size={14} aria-hidden="true" />
        </div>
      )}

      <article className="article-body">
        <div className={`article-mode-badge article-mode-badge--${modeId}`}>
          <MapPinned size={14} aria-hidden="true" />
          <span>תצוגת {currentMode.label}</span>
          <small>{currentMode.description}</small>
        </div>

        <header id="overview" className="article-hero">
          <h1 id="articleTitle">{entry.title}</h1>
          <p>{entry.summary}</p>
        </header>

        <div className="article-meta-line" aria-label="מיקום הערך">
          <span>{currentDegree.label}</span>
          <span>{entry.categoryLabel}</span>
          <span>{entry.status}</span>
        </div>

        <section id="reading" className="article-main-section">
          <div className="section-heading">
            <BookOpen size={18} aria-hidden="true" />
            <h2>{currentMode.detailLabel}</h2>
          </div>
          <p>{entry.body}</p>
        </section>

        {isEncyclopedia && (
          <section id="links" className="article-related-panel article-related-panel--prominent">
            <div className="section-heading">
              <ListChecks size={18} aria-hidden="true" />
              <h2>מושגים סמוכים</h2>
            </div>
            <div className="related-chips">
              {entry.related.map(item => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </section>
        )}

        <section id="source" className="article-source-panel">
          <div>
            <span>מקור הערך</span>
            <strong>{entry.source}</strong>
          </div>
          <button type="button" aria-label="פתיחת מקור" title="פתיחת מקור">
            <ExternalLink size={17} aria-hidden="true" />
          </button>
        </section>

        {isLearning && (
          <section id="links" className="article-related-panel">
            <div className="section-heading">
              <ListChecks size={18} aria-hidden="true" />
              <h2>מה לפתוח ליד זה</h2>
            </div>
            <div className="related-chips">
              {entry.related.map(item => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </section>
        )}

        {isLearning && (
          <footer className="article-next-step" aria-label="הצעד הבא במסלול">
            <div className="article-next-step__label">
              <Route size={16} aria-hidden="true" />
              <span>הצעד הבא במסלול</span>
            </div>
            <div className="article-next-step__pair">
              <button type="button" className="article-next-step__prev" disabled={!previousEntry} onClick={() => previousEntry && onSelectEntry(previousEntry)}>
                <ArrowRight size={16} aria-hidden="true" />
                <span>{previousEntry ? previousEntry.title : 'אין ערך קודם'}</span>
              </button>
              <button type="button" className="article-next-step__next" disabled={!nextEntry} onClick={() => nextEntry && onSelectEntry(nextEntry)}>
                <span>{nextEntry ? nextEntry.title : 'אין ערך הבא'}</span>
                <ArrowLeft size={16} aria-hidden="true" />
              </button>
            </div>
          </footer>
        )}
      </article>
    </section>
  );
}
