# Token diligence architecture diagrams

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
