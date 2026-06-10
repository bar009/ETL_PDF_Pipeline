# Before/After Heuristics

Use this file when the user says the site feels huge or requires browser zoom-out.

## Global Scale

### Before

- user feels forced to press `Ctrl-minus`
- controls feel tall
- cards look like tiles or bubbles
- support surfaces consume too much height

### After

- 100% zoom feels natural
- controls feel compact but readable
- cards read as entry points, not posters
- support surfaces no longer dominate the page

## Homepage

### Before

- hero is too tall
- category cards consume too much height
- sidebars and panels feel padded for no reason

### After

- hero fits comfortably in the first viewport
- cards and rows scan quickly
- sidebars support, rather than crowd, the main area

## Topic Page

### Before

- title block is too tall
- detail surfaces are over-padded
- reading column is narrow, forcing too much vertical scroll

### After

- title block is compact
- reading starts sooner
- reading width is efficient enough to reduce scrolling

## Watch These Selectors First

- `.topic-card`
- `.cards-grid`
- `.nav-sidebar`
- `.aside-panel`
- `.detail-article`
- `.detail-lead`
- `.detail-section`
- `.detail-source-card`
- `.detail-knowledge-links`

## Failure Condition

If the user still says “it feels like I need to zoom out,” the pass is not done.
