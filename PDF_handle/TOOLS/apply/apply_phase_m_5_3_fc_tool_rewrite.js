const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const TODAY = new Date().toISOString().slice(0, 10);

const PHASE_ID = "phase_m5_3_fc_tool_rewrite";
const FROZEN_SLUG = "level2-tool-system-measure-force-direction";
const NEW_SLUG = "level2-tool-system-plumb-square-level";

const REQUIRED_FIELDS = [
  "title",
  "slug",
  "type",
  "level2_content_type",
  "level2_type",
  "depth_scope",
  "boundary_guard_passed",
  "knowledge_type",
  "degree",
  "applies_to_degrees",
  "content_scope",
  "partition_role",
  "degree_owner",
  "product_state",
  "category",
  "parent_topic",
  "aliases",
  "keywords",
  "related_topics",
  "short_summary",
  "reading_layers",
  "full_summary",
  "practical_elements",
  "symbolic_meaning",
  "candidate_lesson",
  "tradition_notes",
  "caution_notes",
  "source_notes",
  "language",
  "knowledge_links",
  "chapter_toc",
  "visibility_level",
  "sensitivity_level",
  "tradition_scope",
  "status",
  "observability",
  "relies_on_level1_topics",
];

const RELATION_MARKERS = [
  "יחס",
  "ביניהם",
  "משלימים",
  "מגדיר",
  "מגדירים",
  "קשר",
  "מפגש",
  "ציר",
  "מישור",
  "התאמה",
];

const PROCESS_MARKERS = [
  "תהליך",
  "רצף",
  "שלב",
  "שלבים",
];

const FORBIDDEN_PATTERNS = [
  { label: "gauge", pattern: /amah-24-etzbaot|gauge|אמת המידה/iu },
  { label: "gavel", pattern: /makevet-ve-izmel|gavel|מקבת/iu },
  { label: "chisel", pattern: /makevet-ve-izmel|chisel|איזמל/iu },
  { label: "mark_master_or_later", pattern: /mark[\s-]?master|later-degree|later degree|royal arch|master mason|דרגה שלישית|רב.?בונה/iu },
];

const REQUIRED_READING_LAYERS = ["basic", "symbolic", "advanced"];
const ALLOW_EMPTY_REQUIRED_FIELDS = new Set([
  "parent_topic",
  "relies_on_level1_topics",
]);

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const rewriteEntry = buildRewriteEntry();

  const validation = {
    phase: PHASE_ID,
    executed_at: new Date().toISOString(),
    frozen_slug: FROZEN_SLUG,
    target_slug: NEW_SLUG,
    stage_1_source_alignment: null,
    stage_2_schema_fit: null,
    stage_3_identity_check: null,
    stage_4_boundary_check: null,
    stage_5_apply_gate: null,
    overall_status: "pending",
  };

  const report = {
    phase: PHASE_ID,
    goal: "Rewrite the frozen Level 2 tool-system entry using only Fellow Craft-supported tools and restore it as a valid canonical Level 2 entry.",
    mode: "controlled_rewrite_single_entry",
    executed_at: validation.executed_at,
    inputs: {
      level2_path: config.level2Path,
      frozen_slug: FROZEN_SLUG,
      notebooklm_report: config.notebooklmReportPath,
      alignment_report: config.alignmentReportPath,
    },
    target_contract: {
      target_slug: NEW_SLUG,
      target_title: rewriteEntry.title,
      degree: rewriteEntry.degree,
      applies_to_degrees: rewriteEntry.applies_to_degrees,
      degree_owner: rewriteEntry.degree_owner,
      level2_type: rewriteEntry.level2_type,
      level2_content_type: rewriteEntry.level2_content_type,
      category: rewriteEntry.category,
      knowledge_type: rewriteEntry.knowledge_type,
      content_scope: rewriteEntry.content_scope,
      partition_role: rewriteEntry.partition_role,
      depth_scope: rewriteEntry.depth_scope,
      language: rewriteEntry.language,
      visibility_level: rewriteEntry.visibility_level,
      sensitivity_level: rewriteEntry.sensitivity_level,
      tradition_scope: rewriteEntry.tradition_scope,
    },
    apply_policy: {
      atomic_write: true,
      backup_required: true,
      backup_name: path.basename(config.backupLevel2Path),
    },
    grounding_strategy: {
      mode: "native_level2_fc_basis",
      relies_on_level1_topics: rewriteEntry.relies_on_level1_topics,
      note: "This rewrite is treated as native Fellow Craft ownership in Level 2. Dedicated local Level 1 FC tool topics are not used as the support basis; grounding is carried through existing library entries only.",
    },
    outputs: {
      updated_level2: config.level2Path,
      backup_level2: config.backupLevel2Path,
      rewrite_entry: config.rewriteEntryPath,
      rewrite_report: config.rewriteReportPath,
      rewrite_validation: config.rewriteValidationPath,
    },
    success_criteria: null,
    overall_status: "pending",
  };

  try {
    assertFileExists(config.level2Path, "Level 2 input");
    assertFileExists(config.notebooklmReportPath, "NotebookLM report");
    assertFileExists(config.alignmentReportPath, "Alignment report");

    const level2Raw = fs.readFileSync(config.level2Path, "utf8");
    const level2Eol = detectEol(level2Raw);
    const level2Data = JSON.parse(level2Raw);
    const level2Next = clone(level2Data);

    const frozenIndex = level2Next.entries.findIndex((entry) => entry.slug === FROZEN_SLUG);
    if (frozenIndex < 0) {
      throw new Error(`Frozen source entry not found: ${FROZEN_SLUG}`);
    }
    if (level2Next.entries.some((entry) => entry.slug === NEW_SLUG)) {
      throw new Error(`Target slug already exists in level2.json: ${NEW_SLUG}`);
    }

    validation.stage_1_source_alignment = runSourceAlignmentValidation(rewriteEntry);
    validation.stage_2_schema_fit = runSchemaFitValidation(rewriteEntry, level2Next);
    validation.stage_3_identity_check = runIdentityValidation(rewriteEntry);
    validation.stage_4_boundary_check = runBoundaryValidation(rewriteEntry);

    const frozenEntry = level2Next.entries[frozenIndex];
    if (frozenEntry.visibility_level !== "editorial" || frozenEntry.review_controls?.decision_status !== "rejected_pending_rewrite") {
      throw new Error(`Frozen source entry is not in the expected M.5.2 editorial state: ${FROZEN_SLUG}`);
    }

    frozenEntry.review_controls = {
      ...(frozenEntry.review_controls || {}),
      superseded_by: NEW_SLUG,
      superseded_in_phase: PHASE_ID,
    };

    level2Next.entries.splice(frozenIndex + 1, 0, rewriteEntry);
    level2Next.meta = {
      ...level2Next.meta,
      updated_at: TODAY,
    };

    validation.stage_5_apply_gate = runApplyGateValidation(level2Next, frozenEntry);

    const stageResults = [
      validation.stage_1_source_alignment,
      validation.stage_2_schema_fit,
      validation.stage_3_identity_check,
      validation.stage_4_boundary_check,
      validation.stage_5_apply_gate,
    ];
    validation.overall_status = stageResults.every((stage) => stage.pass) ? "pass" : "fail";

    if (validation.overall_status !== "pass") {
      throw new Error("Phase M.5.3 validation failed. See rewrite validation output for details.");
    }

    report.success_criteria = {
      new_entry_created: true,
      new_entry_valid: true,
      new_entry_source_aligned: true,
      new_entry_type_integrity: "pass",
      new_entry_category_fit: "pass",
      no_broken_links: true,
      overall_status: "pass",
    };
    report.validation_overview = {
      stage_1_source_alignment: validation.stage_1_source_alignment.pass,
      stage_2_schema_fit: validation.stage_2_schema_fit.pass,
      stage_3_identity_check: validation.stage_3_identity_check.pass,
      stage_4_boundary_check: validation.stage_4_boundary_check.pass,
      stage_5_apply_gate: validation.stage_5_apply_gate.pass,
    };
    report.overall_status = "pass";

    const level2Text = stringifyJson(level2Next, level2Eol);
    const rewriteEntryText = stringifyJson(rewriteEntry, level2Eol);
    const validationText = stringifyJson(validation, level2Eol);
    const reportText = stringifyJson(report, level2Eol);

    ensureParentDir(config.backupLevel2Path);
    ensureParentDir(config.rewriteEntryPath);
    ensureParentDir(config.rewriteReportPath);
    ensureParentDir(config.rewriteValidationPath);

    fs.writeFileSync(config.backupLevel2Path, level2Raw, "utf8");

    const snapshots = buildSnapshots([
      { path: config.level2Path, content: level2Text },
      { path: config.rewriteEntryPath, content: rewriteEntryText },
      { path: config.rewriteReportPath, content: reportText },
      { path: config.rewriteValidationPath, content: validationText },
    ]);

    commitWritesWithRollback(snapshots);

    console.log("Phase M.5.3 rewrite complete");
    console.log(`Level 2 updated: ${config.level2Path}`);
    console.log(`Backup: ${config.backupLevel2Path}`);
    console.log(`Rewrite entry: ${config.rewriteEntryPath}`);
    console.log(`Rewrite report: ${config.rewriteReportPath}`);
    console.log(`Rewrite validation: ${config.rewriteValidationPath}`);
  } catch (error) {
    validation.overall_status = "fail";
    report.overall_status = "fail";
    report.error = error.message;
    console.error(error.message);
    process.exitCode = 1;
  }
}

function buildRewriteEntry() {
  return {
    title: "מערכת כלי חבר־בונה: אנך, זוויתן ופלס",
    slug: NEW_SLUG,
    type: "topic",
    level2_content_type: "symbol_relationship_analysis",
    level2_type: "relationship",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "symbol",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "relationships_between_symbols",
    parent_topic: null,
    aliases: [
      "אנך זוויתן ופלס",
      "Plumb Square Level",
      "כלי חבר־בונה",
    ],
    keywords: [
      "אנך",
      "זוויתן",
      "פלס",
      "חבר בונה",
      "דרגה 2",
      "קשר בין סמלים",
      "Plumb",
      "Square",
      "Level",
    ],
    related_topics: {
      prior: [],
      companion: [
        "level2-lodge-as-learning-structure",
        "level2-light-placement-and-orientation",
      ],
      deeper: [
        "level2-layers-of-the-tracing-board",
      ],
    },
    short_summary: "בדרגה השנייה אנך, זוויתן ופלס נקראים כמערכת יחסים אחת: האנך קובע ציר של יושר, הזוויתן בוחן את היחס, והפלס מחזיק מישור משותף. העומק כאן נולד מן התלות ההדדית בין שלושת הכלים, לא מן הכלי הבודד.",
    reading_layers: {
      basic: "בקריאה הבסיסית, שלושת הכלים אינם שלוש סיסמאות נפרדות. האנך מייצב קו עולה, הזוויתן בודק אם העבודה נשמרת נכונה, והפלס מזכיר שהכול מונח על מישור משותף. לכן הקריאה איננה רק מה אומר כל כלי, אלא איך כל כלי מתקן את האחרים.",
      symbolic: "בקריאה הסמלית, האנך בלי פלס עלול להישאר דרישה נוקשה ללא מישור משותף, הפלס בלי אנך עלול להיהפך לשוויון חסר כיוון, והזוויתן בוחן את המפגש ביניהם כדי שהיושר והאיזון לא יתעוותו. שלושתם יחד יוצרים דקדוק של יושר, מידה ושוויון.",
      advanced: "בקריאה המבנית של דרגה 2, מערכת הכלים מגדירה מרחב עבודה: אנך נותן ציר, פלס נותן מישור, וזוויתן בודק את אמינות המפגש ביניהם. זהו ערך של קשר בין סמלים, משום שהמשמעות נמצאת בהתאמה, בניגוד ובהשלמה שבין שלושת הכלים, לא בהגדרה מבודדת של כל אחד.",
    },
    full_summary: "הערך נשען על כלי חבר־בונה הנתמכים במקורות: אנך, זוויתן ופלס. האנך קובע את הקו העולה ואת יושר העמידה; הפלס יוצר מישור משותף שבו העבודה איננה פרטית ומנותקת; והזוויתן בוחן אם הקשר בין הקו העולה ובין המישור הזה נשמר נכון. לכן הזוויתן איננו תוספת חיצונית לשני האחרים, והפלס איננו רק לקח נפרד על שוויון. כל אחד מן הכלים מגדיר את גבולו של חברו.\n\nבמקום לקרוא את הכלים כרשימת מידות, הקריאה של דרגה 2 רואה בהם מערכת יחסית. האנך מזכיר שהעבודה זקוקה לציר ישר; הפלס מזכיר שהציר הזה חייב להיבחן בתוך שדה משותף; והזוויתן מוודא שהמפגש בין השאיפה האנכית ובין המישור האופקי איננו מעוות. כך נוצרת שפה של בניין: לא רק להיות ישר, ולא רק לעמוד על אותו מישור עם אחרים, אלא לדעת כיצד יושר, מידה ושוויון מחזיקים מבנה אחד.\n\nהעומק של הערך איננו בסדרה עוקבת אלא בתלות ההדדית של הצירים. אנך בלי זוויתן עשוי להישאר קו שאינו נבחן; זוויתן בלי פלס בוחן צורה ללא שדה משותף; פלס בלי אנך עלול להסתפק באחידות שטוחה. הקריאה המשותפת מראה שחבר־בונה לומד לאחוז בו־זמנית בכיוון, ביחס ובמישור.\n\nלכן זהו ערך דרגה שנייה מובהק: לא חזרה על שם הכלים, אלא קריאה מבנית של היחסים ביניהם. המערכת מלמדת כיצד עבודה סימבולית נעשית מדויקת כאשר ציר, מידה ומישור נשמרים יחד.",
    practical_elements: [
      "לבחון מצב של עבודה משותפת דרך שלושה צירים: מהו הקו הישר שמנסים להחזיק (אנך), מהו היחס שנבדק בפועל (זוויתן), ומהו המישור המשותף שעליו כולם עומדים (פלס).",
      "בקריאת סמל או מצב בלשכה, לשאול איזה כלי מבין השלושה חסר כדי שהמבנה יחזיק: ציר, יחס או מישור.",
    ],
    symbolic_meaning: "המשמעות הסמלית של שלושת הכלים נוצרת מן הזיקה ביניהם. האנך מייצר ציר של יושר, הפלס פורש שדה של שוויון ומישור משותף, והזוויתן בודק שהמפגש ביניהם נאמן למידה. כאשר שלושתם נקראים יחד, הם הופכים ממסר בודד לדקדוק של בניין ושל יחס.",
    candidate_lesson: "הלקח של דרגה 2 הוא שלא די להחזיק ערך אחד נכון. יושר ללא יחס בודק עלול להתקשות, ושוויון ללא כיוון עלול להשתטח. חבר־בונה נדרש לקרוא כל מצב דרך השאלה האם הציר ישר, האם היחס נכון, והאם המישור המשותף נשמר.",
    tradition_notes: [
      "הערך נשען רק על כלי חבר־בונה הנתמכים במקורות: אנך, זוויתן ופלס.",
      "הקריאה כאן שומרת על דרגה 2 כקריאה של יחס בין סמלים, ולא כחזרה על הגדרות בודדות של כל כלי.",
    ],
    caution_notes: [
      "אין לערב כאן את כלי התלמיד מן הדרגה הראשונה או כלים מדרגות מאוחרות יותר.",
      "הערך עוסק ביחסים בין שלושת כלי FC ואינו מתרחב לדרשה מוסרית כללית שאינה נובעת מן המערכת עצמה.",
    ],
    source_notes: [
      "Phase M.5.3 controlled rewrite created after the M.5.2 freeze, using FC-supported tools only: Plumb, Square, Level.",
      "Blue Lodge Ritual Reference Guide | THE WORKING TOOLS | C:\\Users\\bar16\\OneDrive\\Documents\\code\\PDF_handle\\consolidated_books\\1st_Edition_Blue_Lodge_Ritual_Reference_Guide_Digital_Edition.md#the-working-tools | section 45",
      "The Deeper Meaning of the FC Degree | Opening the Lodge in the Second Degree | C:\\Users\\bar16\\OneDrive\\Documents\\code\\PDF_handle\\consolidated_books\\Deeper meaning of FC Degree.md#opening-the-lodge-in-the-second-degree | section 4",
      "Commentary on the Second Degree | 2nd Pause | C:\\Users\\bar16\\OneDrive\\Documents\\code\\PDF_handle\\consolidated_books\\commentary_on_the_second_Degree.md#2nd-pause | section 3",
    ],
    language: "he",
    work_id: null,
    work_title: "",
    source_kind: null,
    source_path: null,
    source_anchor: null,
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      {
        slug: "blue-lodge-ritual-reference-guide-2021-section-0045-the-working-tools",
        degree: "library",
      },
      {
        slug: "deeper-meaning-of-fc-degree-section-0004-opening-the-lodge-in-the-second-degree",
        degree: "library",
      },
      {
        slug: "commentary-on-the-second-degree-section-0003-2nd-pause",
        degree: "library",
      },
    ],
    chapter_toc: [
      "פתיחה קצרה",
      "פירוש מבני",
      "קשרים",
      "מסקנה לימודית",
    ],
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "interpretive",
    status: "draft",
    observability: {
      is_distinct_from_level1: true,
      depth_level: "level2",
      relies_on_level1_topics: false,
      relies_on_level1_topic: false,
      introduces_new_structure: true,
    },
    relies_on_level1_topics: [],
  };
}

function runSourceAlignmentValidation(entry) {
  const checks = [];
  const serialized = JSON.stringify(entry);

  checks.push({
    name: "uses_allowed_fc_basis_terms",
    pass: /אנך/u.test(serialized) && /זוויתן/u.test(serialized) && /פלס/u.test(serialized),
    detail: "Entry must explicitly include Plumb, Square, and Level in Hebrew content.",
  });

  checks.push({
    name: "knowledge_links_use_supported_sources_only",
    pass: entry.knowledge_links.every((link) => link.degree === "library" && link.slug !== FROZEN_SLUG),
    detail: "Knowledge links must stay on FC-supporting library sources and never reference the frozen tool entry.",
  });

  for (const rule of FORBIDDEN_PATTERNS) {
    checks.push({
      name: `forbidden_basis_absent:${rule.label}`,
      pass: !rule.pattern.test(serialized),
      detail: `Forbidden source basis ${rule.label} must not appear in the new entry.`,
    });
  }

  return {
    pass: checks.every((check) => check.pass),
    checks,
  };
}

function runSchemaFitValidation(entry, dataset) {
  const checks = [];

  for (const field of REQUIRED_FIELDS) {
    const hasField = Object.prototype.hasOwnProperty.call(entry, field);
    const notEmpty = hasField && (ALLOW_EMPTY_REQUIRED_FIELDS.has(field) || !isEmptyValue(entry[field]));
    checks.push({
      name: `required_field:${field}`,
      pass: hasField && notEmpty,
      detail: "Required field must exist and be non-empty where applicable.",
    });
  }

  for (const layer of REQUIRED_READING_LAYERS) {
    checks.push({
      name: `reading_layer:${layer}`,
      pass: Boolean(entry.reading_layers && typeof entry.reading_layers[layer] === "string" && entry.reading_layers[layer].trim()),
      detail: "All required reading layers must be present.",
    });
  }

  checks.push({
    name: "slug_is_unique",
    pass: !dataset.entries.some((item) => item.slug === entry.slug),
    detail: "Target slug must not already exist in level2.json before apply.",
  });

  checks.push({
    name: "type_matches_target_contract",
    pass: entry.level2_type === "relationship" && entry.level2_content_type === "symbol_relationship_analysis" && entry.type === "topic",
    detail: "Type and Level 2 content type must match the target contract.",
  });

  checks.push({
    name: "category_matches_target_contract",
    pass: entry.category === "relationships_between_symbols",
    detail: "Category must stay in relationships_between_symbols.",
  });

  checks.push({
    name: "visibility_and_scope_match_target_contract",
    pass: entry.visibility_level === "internal"
      && entry.sensitivity_level === "standard"
      && entry.tradition_scope === "interpretive"
      && entry.depth_scope === "structural_only"
      && entry.content_scope === "degree_specific",
    detail: "Scope and visibility fields must match the target contract.",
  });

  return {
    pass: checks.every((check) => check.pass),
    checks,
  };
}

function runIdentityValidation(entry) {
  const text = [
    entry.short_summary,
    entry.reading_layers.basic,
    entry.reading_layers.symbolic,
    entry.reading_layers.advanced,
    entry.full_summary,
    entry.symbolic_meaning,
    entry.candidate_lesson,
  ].join(" ");

  const relationHits = RELATION_MARKERS.reduce((count, marker) => (
    count + (text.includes(marker) ? 1 : 0)
  ), 0);

  const processHits = PROCESS_MARKERS.reduce((count, marker) => (
    count + (text.includes(marker) ? 1 : 0)
  ), 0);

  const checks = [
    {
      name: "declared_type_is_relationship",
      pass: entry.level2_type === "relationship",
      detail: "Entry must remain declared as relationship.",
    },
    {
      name: "interdependence_is_explicit",
      pass: relationHits >= 6,
      detail: "The text must explicitly read through relation, complementarity, or contrast between the tools.",
    },
    {
      name: "does_not_read_mainly_as_process",
      pass: processHits === 0,
      detail: "The rewrite must avoid stage-by-stage or process-centered framing.",
    },
    {
      name: "not_three_isolated_tool_definitions",
      pass: /שלושתם/u.test(text) && /ביניהם/u.test(text) && /מגדיר/u.test(text),
      detail: "The text must tie the tools into one relationship field, not separate mini-definitions.",
    },
  ];

  return {
    pass: checks.every((check) => check.pass),
    checks,
  };
}

function runBoundaryValidation(entry) {
  const text = JSON.stringify(entry);
  const checks = [
    {
      name: "no_higher_degree_contamination",
      pass: !/royal arch|master mason|mark[\s-]?master|דרגה שלישית|רב.?בונה/iu.test(text),
      detail: "Entry must stay clear of higher-degree ownership or later-degree contamination.",
    },
    {
      name: "no_first_degree_tool_recap",
      pass: !/אמת המידה|amah-24-etzbaot|מקבת|makevet|איזמל|chisel|gavel|gauge/iu.test(text),
      detail: "Entry must not reuse the rejected First Degree tool system as a basis.",
    },
    {
      name: "native_fc_degree_ownership_is_clear",
      pass: entry.degree === "level2"
        && JSON.stringify(entry.applies_to_degrees) === JSON.stringify(["level2"])
        && entry.degree_owner === "level2"
        && entry.observability.is_distinct_from_level1 === true
        && entry.observability.introduces_new_structure === true,
      detail: "The entry must clearly own its Level 2 lane.",
    },
  ];

  return {
    pass: checks.every((check) => check.pass),
    checks,
  };
}

function runApplyGateValidation(dataset, frozenEntry) {
  const issues = collectBrokenLocalReferences(dataset);
  const newEntry = dataset.entries.find((entry) => entry.slug === NEW_SLUG);

  const checks = [
    {
      name: "new_entry_created",
      pass: Boolean(newEntry),
      detail: "The new canonical FC tool entry must exist in level2.json.",
    },
    {
      name: "frozen_entry_remains_editorial",
      pass: frozenEntry.visibility_level === "editorial"
        && frozenEntry.review_controls?.decision_status === "rejected_pending_rewrite"
        && frozenEntry.review_controls?.superseded_by === NEW_SLUG,
      detail: "The frozen source entry must remain frozen and may be marked superseded.",
    },
    {
      name: "no_broken_related_topics_or_local_knowledge_links",
      pass: issues.length === 0,
      detail: issues.length ? JSON.stringify(issues) : "No broken local references detected.",
    },
  ];

  return {
    pass: checks.every((check) => check.pass),
    checks,
    broken_references: issues,
  };
}

function collectBrokenLocalReferences(dataset) {
  const entryBySlug = new Map(dataset.entries.map((entry) => [entry.slug, entry]));
  const issues = [];

  for (const entry of dataset.entries) {
    for (const slug of flattenRelatedTopics(entry.related_topics)) {
      if (!entryBySlug.has(slug)) {
        issues.push({ entry_slug: entry.slug, kind: "related_topics", target: slug });
      }
    }

    if (entry.parent_topic && !entryBySlug.has(entry.parent_topic)) {
      issues.push({ entry_slug: entry.slug, kind: "parent_topic", target: entry.parent_topic });
    }

    if (entry.parallel_entry && !entryBySlug.has(entry.parallel_entry)) {
      issues.push({ entry_slug: entry.slug, kind: "parallel_entry", target: entry.parallel_entry });
    }

    for (const link of entry.knowledge_links || []) {
      if (link.degree === dataset.meta.degree && !entryBySlug.has(link.slug)) {
        issues.push({ entry_slug: entry.slug, kind: "knowledge_links", target: link.slug });
      }
    }
  }

  return issues;
}

function resolveConfig(options) {
  return {
    level2Path: resolvePathOption(
      options.level2,
      path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00", "data", "level2.json")
    ),
    notebooklmReportPath: resolvePathOption(
      options["notebooklm-report"],
      path.join(ROOT, "experiments", "notebooklm_validation", "runs", "2026-03-20", "notebooklm_level2_queue_report_19-37-35Z.md")
    ),
    alignmentReportPath: resolvePathOption(
      options["alignment-report"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_2_alignment_report.json")
    ),
    backupLevel2Path: resolvePathOption(
      options["level2-backup"],
      path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00", "data", "level2.pre_m5_3_backup.json")
    ),
    rewriteEntryPath: resolvePathOption(
      options["rewrite-entry"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_3_rewrite_entry.json")
    ),
    rewriteReportPath: resolvePathOption(
      options["rewrite-report"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_3_rewrite_report.json")
    ),
    rewriteValidationPath: resolvePathOption(
      options["rewrite-validation"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_3_rewrite_validation.json")
    ),
  };
}

function parseArgs(args) {
  const parsed = {};
  for (let i = 0; i < args.length; i += 1) {
    const token = args[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = args[i + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
      continue;
    }
    parsed[key] = next;
    i += 1;
  }
  return parsed;
}

function resolvePathOption(value, fallback) {
  const target = value || fallback;
  if (!target) {
    throw new Error("Missing required path configuration");
  }
  return path.isAbsolute(target) ? target : path.resolve(ROOT, target);
}

function buildSnapshots(writes) {
  return writes.map((write) => {
    const exists = fs.existsSync(write.path);
    return {
      ...write,
      previousExists: exists,
      previousContent: exists ? fs.readFileSync(write.path, "utf8") : null,
    };
  });
}

function commitWritesWithRollback(snapshots) {
  const applied = [];
  try {
    for (const snapshot of snapshots) {
      ensureParentDir(snapshot.path);
      fs.writeFileSync(snapshot.path, snapshot.content, "utf8");
      applied.push(snapshot);
    }
  } catch (error) {
    for (let index = applied.length - 1; index >= 0; index -= 1) {
      const snapshot = applied[index];
      if (snapshot.previousExists) {
        fs.writeFileSync(snapshot.path, snapshot.previousContent, "utf8");
      } else if (fs.existsSync(snapshot.path)) {
        fs.unlinkSync(snapshot.path);
      }
    }
    throw error;
  }
}

function flattenRelatedTopics(relatedTopics) {
  if (Array.isArray(relatedTopics)) return relatedTopics.filter(Boolean);
  if (!relatedTopics || typeof relatedTopics !== "object") return [];
  return [
    ...(Array.isArray(relatedTopics.prior) ? relatedTopics.prior : []),
    ...(Array.isArray(relatedTopics.companion) ? relatedTopics.companion : []),
    ...(Array.isArray(relatedTopics.deeper) ? relatedTopics.deeper : []),
  ].filter(Boolean);
}

function isEmptyValue(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value).length === 0;
  return false;
}

function detectEol(text) {
  return text.includes("\r\n") ? "\r\n" : "\n";
}

function stringifyJson(value, eol = "\n") {
  return `${JSON.stringify(value, null, 2)}\n`.replace(/\n/g, eol);
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function assertFileExists(filePath, label) {
  if (!filePath || !fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath || "<missing>"}`);
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

main();
