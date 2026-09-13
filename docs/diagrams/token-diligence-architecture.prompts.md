# Token diligence architecture diagrams

## Matching EVM and Solana footers

Both specialist PNGs now use the same user-requested footer as the combined PNG:
**Read-only access · 7 - 8 minute deadline · Missing evidence clearly labeled**.
Built-in image_gen was used separately on each original image. The edit prompt
replaced only the footer body line, preserving its heading, border and all other
diagram content, styling and dimensions. Runtime timing configuration is unchanged.

## Combined research-limits footer

User-requested diagram wording: **Read-only access · 7 - 8 minute deadline · Missing evidence clearly labeled**.
This is a presentation edit; collector/session timing configuration is unchanged.
Built-in image_gen prompt:

```text
undefined
```

## Combined intake label

User-requested wording: **Token address + token name (optional) + additional context (optional)**.
Built-in image_gen edit, preserving the rest of the approved diagram.

```text
undefined
```

## Chain-specific evidence sources

The source panels now retain named EVM and Solana sources while preserving the
approved simplified workflow. EVM names follow the original reference panel.
Solana discovery/source routes were checked against `solana_discovery.py`:
Dexscreener, GeckoTerminal, Solana Explorer, program IDLs and verified-build claims.
Raydium, Orca, Meteora, pump.fun and PumpSwap are protocol/launch context, not a claim
that every run automatically queries each website. Website/docs/GitHub/X are shared
context. The image paths remain unchanged, so README and HTML pick up the edits.

### Solana source-panel edit (built-in image_gen)

```text
Edit this approved SIMPLE Solana architecture diagram. Change ONLY the contents of the upper-left dashed "Evidence sources" panel. Preserve every other panel, main flow, connectors, legend, title, footer, dimensions and style exactly. Maintain the clean 1536x1024 EVM-style diagram, dark navy, thin muted cyan and white handwritten lettering. Do not add technical architecture details elsewhere.

Replace that panel text with these EXACT lines, with the two section headings slightly larger and generous vertical spacing like the original:
"Evidence sources"
"RPC + discovery"
"Authorized dRPC or public RPC"
"Dexscreener · GeckoTerminal"
"Solana Explorer · IDLs · verified builds"

"Context + leads"
"Raydium · Orca · Meteora"
"pump.fun · PumpSwap · launchpads"
"Website · docs · GitHub · X"

These fit inside the existing upper-left dashed panel using the same body font size as the current evidence-source text. Keep the panel size unchanged, and the existing RPC outgoing connector unchanged. No added paragraphs or extra diagrams. No changes outside this panel.
```

### Combined source-panel edit (built-in image_gen)

```text
Edit the approved SIMPLE combined crypto token due diligence diagram. Keep the central router and workflow, right assessment and two lanes, findings box and footer EXACTLY as they are. Change ONLY the left column so Evidence sources explicitly lists the differing EVM and Solana sources. Preserve the professional simple navy/white-handwritten/muted-cyan style, 1536x1024 landscape, readable labels. This is additional source inventory only, NOT extra workflow or implementation detail.

Enlarge the left upper dashed Evidence sources panel downward: keep its top near y106 and left/right near x40/x415, and extend bottom to about y680. Use compact but readable body lettering approximately 17–19px, orderly left alignment. Within it use EXACT following text. "EVM" and "Solana" are modest underlined subheadings, with whitespace clearly separating their source lists. The source category headings can be same size body, but underlined or accented:
"Evidence sources"

"EVM"
"RPC + discovery"
"Authorized dRPC first · public fallback"
"Dexscreener · Sourcify · explorer"
"Context + leads"
"RH Scan · Robinscan · Blockscout"
"Defined · Fomo · RH Trenches"
"Pons · Long · relevant launchpads"

"Solana"
"RPC + discovery"
"Authorized dRPC or public RPC"
"Dexscreener · GeckoTerminal"
"Solana Explorer · IDLs · verified builds"
"Context + leads"
"Raydium · Orca · Meteora"
"pump.fun · PumpSwap · launchpads"

"Shared context"
"Website · docs · GitHub · X"

Fit all this with whitespace within the enlarged panel; do not shrink the whole diagram. The long lines must remain legible and inside the border. The original evidence-sources arrow to Coordinate research remains, and it must not cross any text.

Move the existing left lower "Deterministic backends" panel below the expanded sources to about y700–852. Preserve its exact existing content with slightly tighter vertical spacing:
"Deterministic backends"
"EVM: contracts · pools · block pins"
"Solana: mints · positions · context slots"
"Verified reads · trade receipts"

Do NOT change title, center column, router, the text "Within the selected specialist", right column, legend, main arrows or footer. No new panels elsewhere, no repeated workflows, no implementation details, no paragraphs. Only reorganize the left column to restore chain-specific source detail.
```

Replaced the overly detailed drafts at the user's request. Built-in image_gen used
the original EVM diagram as the style and complexity reference for both images.
The Solana diagram keeps the same five-stage flow; the combined diagram adds an
offline router and draws the common specialist workflow once. Implementation
details remain in the README and runbooks. Existing output paths are overwritten.

## Solana prompt

```text
Create a SIMPLE professional architecture diagram modeled closely on the attached EVM diagram. The attached EVM image is the sole layout, visual-style and level-of-detail reference. Title "Solana token due diligence". Keep the SAME three-column composition, five main boxes, two research lanes, sparse support panels and shallow footer. Match its midnight navy background, thin muted pale cyan lines, soft white neat handwritten lettering, rounded boxes, dashed panels and restrained title underline. Landscape 1536x1024. Readable large labels, generous whitespace. This is an architecture overview a principal engineer would draw, NOT a technical specification. Use ONLY the text below. Do not add explanations, filenames, versions, environment variables, codes, retry counts, adapters, deadlines or implementation details.

LEFT dashed panel:
"Evidence sources"
"RPC + discovery"
"Authorized dRPC or public RPC"
"Dexscreener · GeckoTerminal · explorer"
"Context + leads"
"Website · docs · GitHub · X"
"Project channels · launchpads"

LEFT lower dashed panel:
"Deterministic backend"
"Mint identity · token controls"
"Pools · positions · trade receipts"
"Context slots · consistency checks"

CENTER five stages exactly:
"Token mint + token name (optional)"
→ "Coordinate research" / "Collect + verify evidence"
→ "Shared evidence" / "Facts · automatic findings"
→ "Reconcile assessments" / "Validate + preserve assessment"
→ "Present findings from the preserved report"
In the last box: four colored circled icons and labels, green check "Good", yellow exclamation "Potential Risk", red X "Bad", gray question mark "Unverified".
Below legend ONLY these two small lines:
"Unverified = missing evidence, kept separate"
"Native source link per finding · four conclusions"

RIGHT top:
"Assess evidence"
"Judgment · targeted verification"
RIGHT dashed group:
"Parallel research"
two boxes:
"Liquidity + market" / "Custody · exits · holders"
"Project + creator" / "Delivery · economics · history"
group footer "Web evidence only"
Dashed upward arrow labeled "Leads" to Assess evidence.

CONNECTORS: Center arrows down through all five stages. Evidence sources feeds Coordinate research. Shared evidence branches to assessment and the research group. Assessment and research notes return into Reconcile assessments. Use clear orthogonal lines routed through empty gutters; no lines across text. Backend is a supporting annotation. If context needs a label, keep it inside source panel rather than adding tangled connectors.

BOTTOM shallow dashed strip:
"Research limits"
"Read-only access · Fixed time and request limits · Findings and unknowns kept separate"

Do not reproduce the old verbose Solana diagram. Do not add anything outside this exact text. Keep visual complexity at or BELOW the EVM reference.
```

## Combined prompt

```text
Create a SIMPLE clean professional architecture overview titled "Crypto token due diligence". The attached EVM diagram is the sole style and complexity reference. Match its dark midnight blue background, thin muted pale cyan outlines, soft white neat handwritten typography, rounded stage boxes, dashed support panels and restrained underlines. Landscape 1536x1024 with large readable labels and generous whitespace. One unified architecture, NOT two miniature complete diagrams side by side. Shared workflow drawn ONCE to show the pattern executed inside the selected specialist. This replaces an overly detailed poster. Use ONLY exact labels specified below, about 180 words in total. No implementation detail, filenames, variables, revisions, byte lengths, numeric budgets or paragraphs.

Three columns like the EVM reference: LEFT sources and backend support, CENTER intake/router and shared workflow, RIGHT assessment and two web research lanes. Shallow footer.
CENTER:
Top box "Token address + original request".
Arrow DOWN into a compact dashed router group titled "Route to one specialist". Inside two side-by-side small boxes:
"EVM" / "Contract + chain"
"Solana" / "Mint + network"
Small footer inside router group "Preserve request + deadline".
Input splits to either specialist; both alternatives then merge into ONE main flow below. They are alternative routes, not concurrent investigations.
Below router, four aligned main boxes:
"Coordinate research" / "Collect + verify evidence"
→ "Shared evidence" / "Facts · automatic findings"
→ "Reconcile assessments" / "Validate + preserve assessment"
→ "Present findings from the preserved report"
Final box contains four colored circled symbols/labels: green check "Good", yellow exclamation "Potential Risk", red X "Bad", gray question mark "Unverified".
Below ONLY "Native source link per finding · four conclusions".
A tiny annotation near the main flow: "Within the selected specialist".

LEFT dashed panel:
"Evidence sources"
"RPC + discovery"
"Authorized dRPC or public RPC"
"Dexscreener · explorers"
"Sourcify (EVM) · GeckoTerminal (Solana)"
"Context + leads"
"Website · docs · GitHub · X"
"Project channels · launchpads"

LEFT lower dashed panel:
"Deterministic backends"
"EVM: contracts · pools · block pins"
"Solana: mints · positions · context slots"
"Verified reads · trade receipts"

RIGHT upper box:
"Assess evidence"
"Judgment · targeted verification"
RIGHT dashed group:
"Parallel research"
two boxes:
"Liquidity + market" / "Custody · exits · holders"
"Project + creator" / "Delivery · economics · history"
group footer "Web evidence only".
Dashed upward arrow "Leads" into Assess evidence.

CONNECTORS: input -> router -> Coordinate -> Shared evidence -> Reconcile -> Present. Sources -> Coordinate. Shared evidence branches to Assess evidence and the web research group. Both assessment and research notes return to Reconcile before Present. Use sparse, clean orthogonal routing in gutters, no arrows over labels. Backend panel is supporting annotation, not a workflow stage.

BOTTOM shallow dashed strip:
"Research limits"
"Read-only access · One original deadline · Findings and unknowns kept separate"

Do not create a long poster, duplicate specialist pipelines, small print, nested technical panels or explanatory paragraphs. All text at similar readable size to the EVM reference. This diagram should communicate the architecture at a glance.
```
