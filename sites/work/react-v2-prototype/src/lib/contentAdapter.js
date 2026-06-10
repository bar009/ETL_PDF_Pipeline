// Loads the v1.1 JSON data and normalizes it to the shape the prototype UI expects.

const DEGREE_FILES = {
  level1: 'level1',
  level2: 'level2',
  level3: 'level3',
  library: 'library'
};

const DEGREE_LABEL_OVERRIDES = {
  level1: 'דרגה 1',
  level2: 'דרגה 2',
  level3: 'דרגה 3',
  library: 'ספרייה'
};

const DEGREE_TITLE_OVERRIDES = {
  level1: 'תלמיד בונה',
  level2: 'שותף בונה',
  level3: 'מורה הדרך',
  library: 'מקורות וארכיון'
};

const DEGREE_SUMMARY_FALLBACK = {
  level1: 'סף הכניסה, הכלים הראשונים, ומפת הסמלים הבסיסית.',
  level2: 'מעבר לעיון, מדעים, מבנים רעיוניים וקשרים רחבים יותר.',
  level3: 'סמלי עומק, זיכרון, אחריות, זמן ומוות.',
  library: 'ספרים, פרקים, עוגני מקור, והשוואת עדויות.'
};

const STATUS_LABELS = {
  draft: 'טיוטה',
  candidate: 'מועמד',
  approved: 'אושר',
  published: 'פתיחה',
  needs_review: 'בבדיקה'
};

async function fetchJson(path) {
  const response = await fetch(path, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Failed to load ${path}: ${response.status}`);
  return response.json();
}

function buildDegree(id, degreesMeta, degreeFile) {
  const meta = degreesMeta?.[id] ?? {};
  const categories = degreeFile?.categories ?? {};
  const categoryList = [
    { id: 'all', label: 'הכל', description: '' },
    ...Object.values(categories).map(cat => ({
      id: cat.id,
      label: cat.title || cat.id,
      description: cat.description || ''
    }))
  ];

  return {
    id,
    label: DEGREE_LABEL_OVERRIDES[id] ?? id,
    title: DEGREE_TITLE_OVERRIDES[id] ?? (meta.title || id),
    tone: meta.color ?? '#666',
    summary: DEGREE_SUMMARY_FALLBACK[id] ?? '',
    categories: categoryList
  };
}

function buildEntry(raw, categoryLookup, degreeId) {
  const categoryId = raw.category ?? 'all';
  const categoryLabel = categoryLookup[categoryId] ?? raw.category ?? '';
  const summary = raw.short_summary || raw.full_summary?.slice(0, 180) || '';
  const bodyParts = [
    raw.full_summary,
    raw.symbolic_meaning,
    raw.practical_elements,
    raw.candidate_lesson
  ].filter(Boolean);
  const body = bodyParts.join('\n\n');
  const sourceRaw = raw.work_title
    || raw.source_path
    || raw.source_heading
    || raw.source_notes
    || '';
  // source_notes is an array in the runtime contract; flatten to display text.
  const source = Array.isArray(sourceRaw)
    ? sourceRaw.filter(Boolean).join(' · ')
    : sourceRaw;
  const relatedRaw = Array.isArray(raw.related_topics) && raw.related_topics.length > 0
    ? raw.related_topics
    : Array.isArray(raw.knowledge_links)
      ? raw.knowledge_links.map(link => link.title || link.slug || link.target_slug).filter(Boolean)
      : [];
  // status is display-fallback-only per MISSING_FIELD_POLICY: missing status
  // renders as the pipeline default (draft), never as an empty badge.
  const status = STATUS_LABELS[raw.status] ?? raw.status ?? STATUS_LABELS.draft;

  return {
    slug: raw.slug,
    title: raw.title,
    type: raw.type,
    degree: degreeId,
    category: categoryId,
    categoryLabel,
    summary,
    body,
    source,
    related: relatedRaw,
    status,
    sourceKind: raw.source_kind ?? raw.type,
    sourceYear: raw.source_year ?? raw.source_anchor ?? '',
    coverage: raw.content_scope ?? raw.knowledge_type ?? '',
    sourceOrder: Number.isFinite(raw.source_order) ? raw.source_order : null,
    parentTopic: raw.parent_topic ?? null
  };
}

export async function loadContent() {
  const [degreesMeta, ...degreeFiles] = await Promise.all([
    fetchJson('/data/degrees.json'),
    ...Object.values(DEGREE_FILES).map(name => fetchJson(`/data/${name}.json`))
  ]);

  const degrees = [];
  const entries = [];

  Object.keys(DEGREE_FILES).forEach((id, index) => {
    const degreeFile = degreeFiles[index];
    const degree = buildDegree(id, degreesMeta, degreeFile);
    degrees.push(degree);

    const categoryLookup = Object.fromEntries(
      degree.categories.map(cat => [cat.id, cat.label])
    );

    (degreeFile?.entries ?? []).forEach(raw => {
      if (!raw?.slug || !raw?.title) return;
      const entry = buildEntry(raw, categoryLookup, id);
      // slug/title/degree/source are hard-fail fields (MISSING_FIELD_POLICY):
      // an entry with no source provenance is dropped, not rendered blank.
      if (!entry.source) return;
      entries.push(entry);
    });
  });

  return { degrees, entries };
}
