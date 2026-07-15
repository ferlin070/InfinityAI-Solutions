# Frontend — Dashboard

Vanilla HTML/CSS/JavaScript dashboard for the AI Command Center.

## Directory Structure

```
frontend/src/
├── index.html           # Main HTML (structure only)
├── css/
│   ├── tokens.css       # Design tokens (colors, fonts)
│   ├── letterhead.css   # Letterhead & title styles
│   ├── forms.css        # Form & textarea styles
│   ├── table.css        # Table & log styles
│   ├── layout.css       # Layout components (grid, roster)
│   └── responsive.css   # Media queries & accessibility
└── js/
    ├── main.js          # Entry point & DOM initialization
    ├── api.js           # API client (fetchExecute, fetchHistory)
    ├── logger.js        # Terminal logging utilities
    ├── history.js       # Activity log management
    └── ui.js            # UI interaction & state management
```

## Design System

### Tokens (`css/tokens.css`)

Color palette ("dokumen pejabat" / office document theme):

```css
--paper:      #EFF2F0    /* Cool beige background */
--card:       #FBFCFB    /* Off-white cards */
--ink:        #1D2A32    /* Dark navy text */
--ink-soft:   #4E6069    /* Softer navy */
--ink-faint:  #7E929B    /* Light gray */
--rule:       #C7D2D2    /* Border lines */
--rule-soft:  #DFE6E5    /* Lighter borders */
--stamp:      #B23A2C    /* Red stamp (emphasis) */
--green:      #2E6B4E    /* Success green */
--green-soft: #E0EAE2    /* Light green background */
```

Fonts (IBM Plex family):
- **IBM Plex Sans Condensed** — Headings, bold labels
- **IBM Plex Sans** — Body text, regular content
- **IBM Plex Mono** — Code, timestamps, data

### CSS Organization

- **tokens.css** — Load first; defines :root variables & resets
- **letterhead.css** — Header, title, date/figures
- **forms.css** — Input fields, buttons, form layout
- **table.css** — Terminal log, activity table, chips
- **layout.css** — Grid layouts, staff roster, footer
- **responsive.css** — Media queries (960px, 440px breakpoints)

### JavaScript Organization

- **api.js** — Fetch wrappers (`fetchExecute`, `fetchHistory`)
- **logger.js** — Terminal utilities (`addLog`, `escapeHtml`)
- **history.js** — Activity log updates (`updateHistory`)
- **ui.js** — Interaction handlers (`executeTask`)
- **main.js** — DOM refs, initialization, event listeners

## Running Locally

No build step required. The frontend is served by the backend.

1. Start backend: `cd backend && python -m src.main`
2. Open browser: `http://localhost:7860`

## Development

### Modifying Styles

Edit files in `css/` — no CSS preprocessor needed. Colors are in `tokens.css`.

Example: To change the primary red stamp color, update `--stamp` in `tokens.css`:

```css
--stamp: #ff6b6b; /* Your new color */
```

All components using `var(--stamp)` will automatically update.

### Adding New JavaScript

1. Create new file in `js/`
2. Add `<script>` tag in `index.html` (before `main.js`)
3. Reference utilities from other js files

### Accessibility

- All interactive elements are keyboard-accessible
- `:focus-visible` outline on all focusable elements
- `aria-live="polite"` on terminal log
- Color contrast meets WCAG AA standards
- Reduced motion support via `@media (prefers-reduced-motion: reduce)`

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires ES6+ JavaScript support
- No external dependencies (vanilla JS only)

## Performance

- Static HTML/CSS/JS — no build or optimization needed
- Inline fonts via Google Fonts CDN
- Responsive images handled at browser level
- CSS grid for efficient layouts

## Future Improvements

- [ ] Dark mode toggle
- [ ] Component library extraction
- [ ] Internationalization (i18n) for non-Malay languages
- [ ] Progressive Web App (PWA) support
- [ ] Offline capability
