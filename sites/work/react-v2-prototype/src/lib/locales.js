export const locales = [
  {
    id: 'he',
    code: 'he',
    dir: 'rtl',
    label: 'עברית',
    shortLabel: 'HE',
    text: {
      brandName: 'כספת הידע',
      skipLink: 'דלג לתוכן',
      searchLabel: 'חיפוש',
      searchPlaceholder: 'חיפוש נושא, מקור או קשר...',
      categoryFilterLabel: 'סינון קטגוריות',
      entriesShown: 'ערכים מוצגים',
      noEntries: 'לא נמצאו ערכים מתאימים.',
      modeNavLabel: 'מצבי קריאה',
      languageLabel: 'שפה',
      pageTitleSuffix: 'כספת הידע',
      homeEyebrow: 'מפת לימוד ומחקר',
      homeTitle: 'להבין את הדרך, לקרוא את הערך, לפתוח את המקור',
      homeSummary: 'התחל במסלול מודרך, עבור לערך מפורק, או פתח את הספרייה כמשטח מחקרי.',
      homeStartAction: 'התחל בדרגה 1',
      homeResearchAction: 'פתח ספרייה',
      homePathTitle: 'בחירת מסלול',
      homeModeTitle: 'איך לקרוא',
      homeFeaturedTitle: 'המלצה להתחלה',
      homeResearchTitle: 'משטח מחקר',
      homeTopicCount: 'נושאים בדרגות',
      homeSourceCount: 'מקורות בדמו',
      homeOpenLibrary: 'למקורות וארכיון',
      degreeDescription: degree => `${degree.label} · ${degree.title}`,
      articleDescription: (entry, degree) => `${entry.title} בתוך ${degree.label}: ${entry.summary}`,
      listDescription: degree => `${degree.title}: ${degree.summary}`,
      homeDescription: 'מפת כניסה ללימוד דרגות, קריאת ערכים וספריית מקורות.'
    }
  },
  {
    id: 'en',
    code: 'en',
    dir: 'ltr',
    label: 'English',
    shortLabel: 'EN',
    text: {
      brandName: 'Knowledge Vault',
      skipLink: 'Skip to content',
      searchLabel: 'Search',
      searchPlaceholder: 'Search topic, source, or relation...',
      categoryFilterLabel: 'Filter categories',
      entriesShown: 'entries shown',
      noEntries: 'No matching entries found.',
      modeNavLabel: 'Reading modes',
      languageLabel: 'Language',
      pageTitleSuffix: 'Knowledge Vault',
      homeEyebrow: 'Learning and research map',
      homeTitle: 'Find the path, read the article, open the source',
      homeSummary: 'Start with a guided degree path, move into a focused article, or open the library as a research surface.',
      homeStartAction: 'Start Degree 1',
      homeResearchAction: 'Open library',
      homePathTitle: 'Choose a path',
      homeModeTitle: 'How to read',
      homeFeaturedTitle: 'Recommended start',
      homeResearchTitle: 'Research surface',
      homeTopicCount: 'degree topics',
      homeSourceCount: 'demo sources',
      homeOpenLibrary: 'Sources and archive',
      degreeDescription: degree => `${degree.label} · ${degree.title}`,
      articleDescription: (entry, degree) => `${entry.title} in ${degree.label}: ${entry.summary}`,
      listDescription: degree => `${degree.title}: ${degree.summary}`,
      homeDescription: 'Entry map for degree learning, article reading, and source research.'
    }
  }
];

export function getLocale(localeId) {
  return locales.find(locale => locale.id === localeId) ?? locales[0];
}

function getSourceDescription(entry) {
  return [
    `${entry.title}: ${entry.summary}`,
    entry.sourceKind,
    entry.sourceYear,
    entry.coverage
  ].filter(Boolean).join(' · ');
}

export function getPageMeta({
  currentDegree,
  entry,
  isArticleRoute,
  isHomeRoute,
  isSourceRoute = false,
  locale,
  pathname = '/'
}) {
  if (isHomeRoute) {
    return {
      title: `${locale.text.homeTitle} | ${locale.text.pageTitleSuffix}`,
      description: locale.text.homeDescription,
      canonicalPath: '/',
      ogType: 'website'
    };
  }

  const titleBase = isArticleRoute ? entry.title : currentDegree.title;
  const description = isSourceRoute
    ? getSourceDescription(entry)
    : isArticleRoute
      ? locale.text.articleDescription(entry, currentDegree)
      : locale.text.listDescription(currentDegree);

  return {
    title: `${titleBase} | ${locale.text.pageTitleSuffix}`,
    description,
    canonicalPath: pathname,
    ogType: isArticleRoute ? 'article' : 'website'
  };
}
