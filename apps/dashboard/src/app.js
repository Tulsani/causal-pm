const DATA_PATHS = {
  effects: [
    "/experiments/runs/synerise_overlap_100000_20260708_055716.json",
    "../../../experiments/runs/synerise_overlap_100000_20260708_055716.json",
  ],
  windows: [
    "/experiments/runs/event_windows_100000_20260708.json",
    "../../../experiments/runs/event_windows_100000_20260708.json",
  ],
  graph: [
    "/experiments/graphs/synerise_product_journey_v0.json",
    "../../../experiments/graphs/synerise_product_journey_v0.json",
  ],
};

const CONFOUNDERS = [
  "Prior purchase behavior",
  "Prior search, page, cart, and remove activity",
  "Recency of the last pre-period event",
  "Active-client lifecycle status",
  "SKU interaction count and unique SKU count",
  "Mean interacted product price and category size",
];

const NEXT_TESTS = [
  {
    title: "Use event-relative causal windows",
    body: "Estimate add_to_cart -> product_buy within 1 hour, 24 hours, and 7 days with controls measured before each event.",
    why: "This matches the actual product journey better than a broad pre/post split.",
  },
  {
    title: "Segment first-time vs repeat buyers",
    body: "Run the add-to-cart analysis separately for clients with and without prior purchases.",
    why: "Prior buyers can have satisfied demand, which distorts later purchase probability.",
  },
  {
    title: "Disambiguate remove-from-cart",
    body: "Measure remove_from_cart followed by add_to_cart of another SKU and later purchase.",
    why: "Remove may mean cart editing rather than abandonment.",
  },
  {
    title: "Replace synthetic DOM priors",
    body: "Instrument a demo store so add-to-cart events are tied to real DOM nodes and page context.",
    why: "The graph should distinguish product-card CTA, cart-page CTA, and checkout controls.",
  },
];

let state = {
  effects: null,
  windows: null,
  graph: null,
};

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  const sign = Number(value) > 0 ? "+" : "";
  return `${sign}${(Number(value) * 100).toFixed(2)}%`;
}

function formatRate(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return `${(Number(value) * 100).toFixed(2)}%`;
}

async function fetchFirst(paths) {
  let lastError;
  for (const path of paths) {
    try {
      const response = await fetch(path);
      if (response.ok) {
        return response.json();
      }
      lastError = new Error(`${path}: ${response.status}`);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

function getEffect(treatment) {
  return state.effects.effects.find((effect) => effect.treatment === treatment);
}

function getWindow(scope, hours) {
  return state.windows[scope].find((row) => Number(row.window_hours) === Number(hours));
}

function setStatus(text, className) {
  const status = document.getElementById("load-status");
  status.textContent = text;
  status.className = `status-pill ${className || ""}`.trim();
}

function inferAnswer(question) {
  const normalized = question.toLowerCase();
  const addToCart = getEffect("add_to_cart");
  const remove = getEffect("remove_from_cart");
  const search = getEffect("search_query");
  const sameSku24 = getWindow("same_sku", 24);
  const anySku24 = getWindow("any_sku", 24);

  if (normalized.includes("remove")) {
    return {
      title: "Remove-from-cart may be cart editing, not pure abandonment",
      body: `Raw analytics shows remove-from-cart users buy less later (${formatPercent(
        remove.naive_risk_difference
      )}), but the regression-adjusted estimate is ${formatPercent(
        remove.regression_adjusted_risk_difference
      )}. A plausible product interpretation is that remove-from-cart marks highly engaged shoppers who are editing choices, not simply abandoning.`,
      primary: remove,
      window: null,
    };
  }

  if (normalized.includes("search")) {
    return {
      title: "Search behaves like an intent-formation signal",
      body: `Search looks negative in the raw later-window comparison (${formatPercent(
        search.naive_risk_difference
      )}), but adjusted estimates turn positive. The graph treats search as an upstream product action that can precede carting and purchase.`,
      primary: search,
      window: null,
    };
  }

  return {
    title: "Raw add-to-cart analysis is misleading",
    body: `The raw comparison says add-to-cart users buy less later (${formatPercent(
      addToCart.naive_risk_difference
    )}). After controlling for observed confounders, the regression-adjusted estimate is ${formatPercent(
      addToCart.regression_adjusted_risk_difference
    )}. Event-relative timing tells the missing story: ${formatRate(
      sameSku24.conversion_rate
    )} of add-to-cart events have a same-SKU purchase within 24 hours, and ${formatRate(
      anySku24.conversion_rate
    )} have any-SKU purchase within 24 hours.`,
    primary: addToCart,
    window: sameSku24,
  };
}

function renderAnswer(question) {
  const answer = inferAnswer(question);
  document.getElementById("answer-title").textContent = answer.title;
  document.getElementById("answer-body").textContent = answer.body;

  const naive = document.getElementById("metric-naive");
  const regression = document.getElementById("metric-regression");
  const windowMetric = document.getElementById("metric-window");

  naive.textContent = formatPercent(answer.primary.naive_risk_difference);
  naive.className = answer.primary.naive_risk_difference < 0 ? "negative" : "positive";

  regression.textContent = formatPercent(answer.primary.regression_adjusted_risk_difference);
  regression.className = answer.primary.regression_adjusted_risk_difference < 0 ? "negative" : "positive";

  windowMetric.textContent = answer.window ? formatRate(answer.window.conversion_rate) : "n/a";
  windowMetric.className = "positive";
}

function renderConfounders() {
  const list = document.getElementById("confounder-list");
  list.innerHTML = CONFOUNDERS.map((item) => `<li>${item}</li>`).join("");
}

function renderInsightCards() {
  const cards = [
    {
      title: "The raw comparison is unfair",
      body: "Users who already added to cart are often later in their lifecycle than users who did not. They may have already completed demand before the later outcome window.",
    },
    {
      title: "Product role changes interpretation",
      body: "Add-to-cart is a commitment action, not a generic click. It should be evaluated near the event and within the product journey.",
    },
    {
      title: "Evidence is useful but not final",
      body: "Current evidence is adjusted association plus event-relative timing. A real experiment or stronger event-level SCM is still needed.",
    },
  ];

  document.getElementById("insight-grid").innerHTML = cards
    .map(
      (card) => `
        <article class="insight-card">
          <h3>${card.title}</h3>
          <p>${card.body}</p>
        </article>
      `
    )
    .join("");
}

function renderEvidenceTable() {
  const rows = state.effects.effects
    .map(
      (effect) => `
      <tr>
        <td><strong>${effect.treatment}</strong></td>
        <td class="${effect.naive_risk_difference < 0 ? "negative" : "positive"}">${formatPercent(
          effect.naive_risk_difference
        )}</td>
        <td class="${effect.activity_adjusted_risk_difference < 0 ? "negative" : "positive"}">${formatPercent(
          effect.activity_adjusted_risk_difference
        )}</td>
        <td class="${effect.propensity_proxy_adjusted_risk_difference < 0 ? "negative" : "positive"}">${formatPercent(
          effect.propensity_proxy_adjusted_risk_difference
        )}</td>
        <td class="${effect.regression_adjusted_risk_difference < 0 ? "negative" : "positive"}">${formatPercent(
          effect.regression_adjusted_risk_difference
        )}</td>
        <td>${effect.evidence_level}</td>
      </tr>
    `
    )
    .join("");
  document.getElementById("evidence-table").innerHTML = rows;
}

function renderWindows() {
  const scopes = [
    ["same_sku", "Same SKU"],
    ["any_sku", "Any SKU"],
  ];
  const html = scopes
    .flatMap(([key, label]) =>
      state.windows[key].map(
        (row) => `
          <article class="window-card">
            <h3>${label}: ${row.window_hours}h</h3>
            <p><strong>${formatRate(row.conversion_rate)}</strong> conversion rate</p>
            <p>${row.matched_purchases.toLocaleString()} matched events from ${row.add_to_cart_events.toLocaleString()} add-to-cart events</p>
          </article>
        `
      )
    )
    .join("");
  document.getElementById("window-grid").innerHTML = html;
}

function edgeClass(edge) {
  if (edge.kind === "causes_candidate") return "candidate";
  if (edge.kind === "influences" || edge.kind === "precedes") return "evidence";
  return "";
}

function renderGraph() {
  const positions = {
    "page.product_detail": [180, 70],
    "element.search_input": [80, 190],
    "element.product_card": [290, 190],
    "element.add_to_cart_button": [230, 320],
    "element.remove_from_cart_button": [430, 320],
    "action.search_query": [80, 440],
    "action.add_to_cart": [270, 440],
    "action.remove_from_cart": [470, 440],
    "outcome.product_buy": [610, 250],
  };

  const nodeById = Object.fromEntries(state.graph.nodes.map((node) => [node.id, node]));
  const edges = state.graph.edges.filter((edge) => positions[edge.source] && positions[edge.target]);
  const edgeMarkup = edges
    .map((edge, index) => {
      const [x1, y1] = positions[edge.source];
      const [x2, y2] = positions[edge.target];
      const curve = Math.max(30, Math.abs(x2 - x1) / 3);
      const path = `M ${x1} ${y1} C ${x1 + curve} ${y1}, ${x2 - curve} ${y2}, ${x2} ${y2}`;
      return `
        <path class="graph-edge ${edgeClass(edge)}" d="${path}" marker-end="url(#arrow)" />
        <path class="edge-hotspot" d="${path}" data-edge-index="${index}" />
      `;
    })
    .join("");

  const nodeMarkup = state.graph.nodes
    .map((node) => {
      const [x, y] = positions[node.id];
      if (!x || !y) return "";
      return `
        <g>
          <rect class="graph-node ${node.kind}" x="${x - 70}" y="${y - 24}" width="140" height="48" rx="8" />
          <text class="graph-label" x="${x}" y="${y + 4}">${node.label}</text>
        </g>
      `;
    })
    .join("");

  document.getElementById("graph-canvas").innerHTML = `
    <svg class="graph-svg" viewBox="0 0 720 560" role="img">
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
          <path d="M0,0 L0,6 L9,3 z" fill="#9aa4b2"></path>
        </marker>
      </defs>
      ${edgeMarkup}
      ${nodeMarkup}
    </svg>
  `;

  document.querySelectorAll(".edge-hotspot").forEach((path) => {
    path.addEventListener("click", () => {
      const edge = edges[Number(path.dataset.edgeIndex)];
      renderEdgeDetail(edge, nodeById);
    });
  });
}

function renderEdgeDetail(edge, nodeById) {
  const evidence = edge.evidence || {};
  document.getElementById("edge-detail-content").innerHTML = `
    <strong>${nodeById[edge.source].label} -> ${nodeById[edge.target].label}</strong>
    <dl>
      <dt>Edge kind</dt>
      <dd>${edge.kind}</dd>
      <dt>Weight</dt>
      <dd>${edge.weight === undefined ? "n/a" : formatRate(edge.weight)}</dd>
      <dt>Evidence source</dt>
      <dd>${evidence.source || "n/a"}</dd>
      <dt>Evidence level</dt>
      <dd>${evidence.evidence_level || "Structural prior"}</dd>
    </dl>
  `;
}

function renderTests() {
  document.getElementById("test-list").innerHTML = NEXT_TESTS.map(
    (test) => `
      <article class="test-card">
        <h3>${test.title}</h3>
        <p>${test.body}</p>
        <strong>${test.why}</strong>
      </article>
    `
  ).join("");
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });
}

function setupQuestionForm() {
  document.getElementById("question-form").addEventListener("submit", (event) => {
    event.preventDefault();
    renderAnswer(document.getElementById("question-input").value);
  });
}

function renderAll() {
  renderAnswer(document.getElementById("question-input").value);
  renderConfounders();
  renderInsightCards();
  renderEvidenceTable();
  renderWindows();
  renderGraph();
  renderTests();
}

async function main() {
  setupTabs();
  setupQuestionForm();

  try {
    const [effects, windows, graph] = await Promise.all([
      fetchFirst(DATA_PATHS.effects),
      fetchFirst(DATA_PATHS.windows),
      fetchFirst(DATA_PATHS.graph),
    ]);
    state = { effects, windows, graph };
    renderAll();
    setStatus("Evidence loaded", "loaded");
  } catch (error) {
    console.error(error);
    setStatus("Could not load data", "error");
    document.getElementById("answer-body").textContent =
      "Start a local server from the repository root so the dashboard can fetch experiment JSON files.";
  }
}

main();
