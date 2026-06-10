export const modes = [
  {
    id: 'learning',
    label: 'למידה',
    description: 'מסלול קריאה קצר וברור',
    detailLabel: 'מה לקחת הלאה'
  },
  {
    id: 'encyclopedia',
    label: 'אנציקלופדיה',
    description: 'הגדרה, מיקום וקשרים',
    detailLabel: 'מיקום במערכת'
  },
  {
    id: 'research',
    label: 'מחקר',
    description: 'מקור, עדות והשוואה',
    detailLabel: 'עוגן מקור'
  }
];

export const degrees = [
  {
    id: 'level1',
    label: 'דרגה 1',
    title: 'תלמיד בונה',
    tone: '#8c6a24',
    summary: 'סף הכניסה, הכלים הראשונים, ומפת הסמלים הבסיסית.',
    categories: [
      { id: 'all', label: 'הכל' },
      { id: 'tools_and_signs', label: 'כלים וסימנים' },
      { id: 'degree_board', label: 'לשכה וסמל' }
    ]
  },
  {
    id: 'level2',
    label: 'דרגה 2',
    title: 'שותף בונה',
    tone: '#44705a',
    summary: 'מעבר לעיון, מדעים, מבנים רעיוניים וקשרים רחבים יותר.',
    categories: [
      { id: 'all', label: 'הכל' },
      { id: 'philosophy', label: 'פילוסופיה' }
    ]
  },
  {
    id: 'level3',
    label: 'דרגה 3',
    title: 'מורה הדרך',
    tone: '#9b5644',
    summary: 'סמלי עומק, זיכרון, אחריות, זמן ומוות.',
    categories: [
      { id: 'all', label: 'הכל' },
      { id: 'lesson', label: 'שיעורי ליבה' }
    ]
  },
  {
    id: 'library',
    label: 'ספריה',
    title: 'מקורות וארכיון',
    tone: '#496f82',
    summary: 'ספרים, פרקים, עוגני מקור, והשוואת עדויות.',
    categories: [
      { id: 'all', label: 'הכל' },
      { id: 'etl_imports', label: 'ייבואי PDF' },
      { id: 'source_book', label: 'ספרים' }
    ]
  }
];

export const entries = [
  {
    degree: 'level1',
    title: 'The Lambskin Apron',
    slug: 'the-lambskin-apron',
    category: 'tools_and_signs',
    categoryLabel: 'כלים וסימנים',
    type: 'topic',
    status: 'פתיחה',
    summary: 'סמל יסוד של הכנה, מוסר ומשמעת עצמית בדרגה הראשונה.',
    body: 'הסינר הוא שער קריאה נוח מפני שהוא מחבר אובייקט מוחשי, משמעות מוסרית, ושאלת המשך פשוטה: מה האדם נושא עליו כשהוא נכנס לעבודה?',
    source: 'Duncan’s Ritual · Degree 1',
    related: ['The Working Tools of an Entered Apprentice', 'The Furniture of a Lodge']
  },
  {
    degree: 'level1',
    title: 'The Working Tools of an Entered Apprentice',
    slug: 'the-working-tools-of-an-entered-apprentice',
    category: 'tools_and_signs',
    categoryLabel: 'כלים וסימנים',
    type: 'topic',
    status: 'המשך',
    summary: 'כלי העבודה הראשונים כמסגרת לזמן, עבודה פנימית וריסון.',
    body: 'זהו נושא שמתאים במיוחד למסלול לימודי: תחילה מזהים את הכלים, אחר כך קוראים את ההוראה המוסרית, ובסוף עוברים להשוואה מול סמלים סמוכים.',
    source: 'Duncan’s Ritual · Degree 1',
    related: ['The Lambskin Apron', 'The Form and Support of a Lodge']
  },
  {
    degree: 'level1',
    title: 'The Furniture of a Lodge',
    slug: 'the-furniture-of-a-lodge',
    category: 'degree_board',
    categoryLabel: 'לשכה וסמל',
    type: 'topic',
    status: 'מפה',
    summary: 'מערכת הרכיבים שממקמת את הלשכה כמרחב סמלי אחד.',
    body: 'כאן המסך צריך לעבוד כמו מפה: לא עוד פסקה רצופה בלבד, אלא חלוקה לרכיבים, תפקידים וקשרים בתוך אותו מרחב.',
    source: 'Duncan’s Ritual · Degree 1',
    related: ['The Covering of a Lodge', 'The Ornaments and Lights of a Lodge']
  },
  {
    degree: 'level2',
    title: 'The Globes',
    slug: 'the-globes',
    category: 'philosophy',
    categoryLabel: 'פילוסופיה',
    type: 'topic',
    status: 'עיון',
    summary: 'גיאוגרפיה, שמים, ותנועה אינטלקטואלית רחבה יותר.',
    body: 'הגלובוסים שייכים למסך שמעדיף הגדרה קצרה, הקשר רעיוני, וקישור ישיר למדעים הסמוכים.',
    source: 'Degree 2 Review Set',
    related: ['Astronomy', 'Geometry']
  },
  {
    degree: 'level2',
    title: 'Geometry',
    slug: 'geometry',
    category: 'philosophy',
    categoryLabel: 'פילוסופיה',
    type: 'topic',
    status: 'צומת',
    summary: 'המדע המרכזי שמחזיק סדר, מידה ותוכנית.',
    body: 'גיאומטריה היא צומת שמרוויח ממסך מפורק: הגדרה, מקום בדרגה, קשר לאומנויות החופשיות, וקישורי המשך.',
    source: 'Degree 2 Review Set',
    related: ['The Five Senses and Seven Liberal Arts', 'Astronomy']
  },
  {
    degree: 'level3',
    title: 'The All-Seeing Eye',
    slug: 'the-all-seeing-eye',
    category: 'lesson',
    categoryLabel: 'שיעורי ליבה',
    type: 'topic',
    status: 'קריאה',
    summary: 'סמל של השגחה, חיים פנימיים ואחריות מוסרית.',
    body: 'זהו ערך שצריך נשימה טיפוגרפית: סיכום קצר, פרשנות, מקור, וקשר לשאלת האחריות האישית.',
    source: 'Degree 3 Review Set',
    related: ['The Scythe', 'Youth, Manhood, and Age']
  },
  {
    degree: 'level3',
    title: 'The Scythe',
    slug: 'the-scythe',
    category: 'lesson',
    categoryLabel: 'שיעורי ליבה',
    type: 'topic',
    status: 'סמל עומק',
    summary: 'סמל מוות וזמן שמכוון לקריאה איטית וממוקדת.',
    body: 'החרמש צריך להרגיש כמו דף קריאה ולא כמו כרטיס קטלוג: פחות צפיפות, יותר סדר בין סיכום, מקור וקשרים.',
    source: 'Degree 3 Review Set',
    related: ['The All-Seeing Eye', 'Youth, Manhood, and Age']
  },
  {
    degree: 'library',
    title: 'Duncan’s Masonic Ritual and Monitor of Freemasonry',
    slug: 'duncans-ritual-monitor-1866-book',
    category: 'source_book',
    categoryLabel: 'ספרים',
    type: 'book',
    status: 'מקור עוגן',
    summary: 'ספר מקור מרכזי שממנו נגזרים פרקים, עוגנים ונושאי דרגות.',
    body: 'הספריה צריכה להדגיש מקור, פרק, סטטוס, וקשר לערכים שנבנו ממנו.',
    source: 'Library Root',
    sourceYear: '1866',
    sourceKind: 'Book',
    coverage: '1305 library entries',
    related: ['The Lambskin Apron', 'Geometry']
  },
  {
    degree: 'library',
    title: 'Page 2',
    slug: 'duncans-ritual-monitor-1866-section-0001-page-2',
    category: 'etl_imports',
    categoryLabel: 'ייבואי PDF',
    type: 'chapter',
    status: 'סריקה',
    summary: 'עמוד מקור מתוך ייבוא PDF.',
    body: 'דפי מקור צריכים להיות נגישים דרך טבלת מחקר צפופה, עם סימון מקור וקשר לערכים שנשענים עליהם.',
    source: 'Duncan’s Ritual · Page 2',
    sourceYear: '1866',
    sourceKind: 'Chapter',
    coverage: 'source page',
    related: ['Duncan’s Masonic Ritual and Monitor of Freemasonry']
  }
];
