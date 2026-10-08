/* EXIOR OS — front-end prototype. All data is demo data kept in localStorage. */
(function () {
  'use strict';

  /* ---------- helpers ---------- */
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const uid = (p) => p + Math.random().toString(36).slice(2, 8);
  const now = () => Date.now();
  const MIN = 60000, HOUR = 60 * MIN, DAY = 24 * HOUR;
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function ago(t) {
    const d = now() - t;
    if (d < MIN) return 'just now';
    if (d < HOUR) return Math.floor(d / MIN) + 'm ago';
    if (d < DAY) return Math.floor(d / HOUR) + 'h ago';
    return Math.floor(d / DAY) + 'd ago';
  }
  const fmtDur = (s) => (s < 60 ? s.toFixed(1) + 's' : Math.floor(s / 60) + 'm ' + Math.round(s % 60) + 's');
  const fmtN = (n) => n.toLocaleString('en-US');

  /* ---------- icons ---------- */
  const sv = (d, w = 16) => `<svg width="${w}" height="${w}" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const I = {
    home: sv('<path d="M2.5 7L8 2.5 13.5 7v6a1 1 0 01-1 1h-9a1 1 0 01-1-1z"/><path d="M6.5 14V10h3v4"/>'),
    inbox: sv('<path d="M2 9l1.6-5.2A1 1 0 014.6 3h6.8a1 1 0 011 .8L14 9v3.5a1 1 0 01-1 1H3a1 1 0 01-1-1z"/><path d="M2 9h3.5l1 1.8h3L10.5 9H14"/>'),
    agent: sv('<path d="M8 1.8l1.5 4.2 4.2 1.5-4.2 1.5L8 13.2 6.5 9 2.3 7.5 6.5 6z"/>'),
    flow: sv('<rect x="1.8" y="2" width="4.5" height="4" rx="1.2"/><rect x="9.7" y="10" width="4.5" height="4" rx="1.2"/><path d="M6.3 4h3a2 2 0 012 2v4"/>'),
    map: sv('<rect x="2" y="2" width="5" height="5" rx="1.2"/><rect x="9" y="2" width="5" height="5" rx="1.2"/><rect x="2" y="9" width="5" height="5" rx="1.2"/><rect x="9" y="9" width="5" height="5" rx="1.2"/>'),
    runs: sv('<path d="M5.5 4h8M5.5 8h8M5.5 12h8"/><circle cx="2.6" cy="4" r=".6"/><circle cx="2.6" cy="8" r=".6"/><circle cx="2.6" cy="12" r=".6"/>'),
    gear: sv('<circle cx="8" cy="8" r="2.2"/><path d="M8 1.8v1.6M8 12.6v1.6M3.6 3.6l1.1 1.1M11.3 11.3l1.1 1.1M1.8 8h1.6M12.6 8h1.6M3.6 12.4l1.1-1.1M11.3 4.7l1.1-1.1"/>'),
    check: sv('<path d="M3.2 8.4l3 3L12.8 4.8"/>'),
    x: sv('<path d="M4 4l8 8M12 4l-8 8"/>'),
    alert: sv('<path d="M8 5v3.5M8 11h.01"/><circle cx="8" cy="8" r="6"/>'),
    pause: sv('<path d="M6 3.5v9M10 3.5v9"/>'),
    play: sv('<path d="M5 3.3v9.4L12.5 8z"/>'),
    plus: sv('<path d="M8 3v10M3 8h10"/>'),
    search: sv('<circle cx="7" cy="7" r="4.6"/><path d="M10.5 10.5L14 14"/>'),
    sun: sv('<circle cx="8" cy="8" r="2.8"/><path d="M8 1.5v1.3M8 13.2v1.3M1.5 8h1.3M13.2 8h1.3M3.4 3.4l.9.9M11.7 11.7l.9.9M3.4 12.6l.9-.9M11.7 4.3l.9-.9"/>'),
    moon: sv('<path d="M13.2 9.6A5.5 5.5 0 016.4 2.8 5.5 5.5 0 1013.2 9.6z"/>'),
    arrow: sv('<path d="M3.5 8h9M9 4.5L12.5 8 9 11.5"/>'),
    back: sv('<path d="M12.5 8h-9M7 4.5L3.5 8 7 11.5"/>'),
    more: sv('<circle cx="3.5" cy="8" r=".8"/><circle cx="8" cy="8" r=".8"/><circle cx="12.5" cy="8" r=".8"/>'),
    mail: sv('<rect x="2" y="3.5" width="12" height="9" rx="1.5"/><path d="M2.5 4.5L8 8.5l5.5-4"/>'),
    bolt: sv('<path d="M9 1.8L3.5 9H8l-1 5.2L12.5 7H8z"/>'),
    clock: sv('<circle cx="8" cy="8" r="6"/><path d="M8 4.8V8l2.2 1.4"/>'),
    plug: sv('<path d="M6 2v3M10 2v3M4 5h8v2.5a4 4 0 01-8 0zM8 11.5V14"/>'),
    sliders: sv('<path d="M3 4h10M3 8h10M3 12h10"/><circle cx="6" cy="4" r="1.3" fill="var(--card)"/><circle cx="10.5" cy="8" r="1.3" fill="var(--card)"/><circle cx="5" cy="12" r="1.3" fill="var(--card)"/>'),
    table: sv('<rect x="2" y="2.5" width="12" height="11" rx="1.5"/><path d="M2 6h12M2 9.7h12M6.5 6v7.5"/>'),
    chart: sv('<path d="M2.5 13.5h11"/><path d="M4.5 11V7.5M8 11V4M11.5 11V8.5"/>'),
    keyb: sv('<rect x="1.5" y="4" width="13" height="8.5" rx="2"/><path d="M4.5 7h.01M7 7h.01M9.5 7h.01M12 7h.01M5 9.8h6"/>'),
    trash: sv('<path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.6 8.5a1 1 0 001 .9h3.8a1 1 0 001-.9l.6-8.5"/>')
  };

  /* ---------- seed data ---------- */
  const FUNCS = ['Finance', 'Sales', 'Operations', 'Support', 'People'];
  const ACTS = ['Intake', 'Matching', 'Follow-up', 'Reporting', 'Scheduling', 'Exceptions'];
  const SYSTEMS = ['CRM', 'ERP', 'Accounting', 'Email', 'Docs', 'Spreadsheets', 'Helpdesk', 'Team chat', 'Data warehouse', 'HRIS'];

  const RUN_TITLES = {
    a1: ['Invoice batch coded and posted', 'Supplier invoice matched to PO', 'Duplicate invoice blocked'],
    a2: ['Bank lines reconciled', 'Month-end checklist advanced', 'Card expenses matched'],
    a3: ['Inbound lead enriched and routed', 'Demo request qualified', 'Lead deduplicated in CRM'],
    a4: ['Follow-up sequence sent', 'Stalled deal flagged', 'Meeting notes logged to CRM'],
    a5: ['Order captured from email', 'Order synced to ERP', 'Delivery date confirmed'],
    a6: ['Supplier chased for delivery', 'Reply parsed and logged', 'Late shipment escalated'],
    a7: ['Ticket classified and drafted', 'Refund request routed', 'Answer grounded in docs'],
    a8: ['CV shortlisted against criteria', 'Interview slot proposed', 'Onboarding checklist created']
  };
  const RUN_STEPS = {
    Finance: ['Read source documents', 'Extract and validate fields', 'Match against ledger', 'Post or route exception'],
    Sales: ['Receive event', 'Enrich from public data', 'Score and route', 'Update CRM'],
    Operations: ['Parse inbound message', 'Check ERP state', 'Act on order', 'Notify stakeholders'],
    Support: ['Read ticket', 'Search knowledge base', 'Draft answer', 'Route for review'],
    People: ['Read application', 'Check criteria', 'Shortlist or decline', 'Notify recruiter']
  };

  function seed() {
    const t = now();
    const agents = [
      { id: 'a1', name: 'Invoice Intake', fn: 'Finance', desc: 'Reads supplier invoices from the shared inbox, codes them and posts them to accounting.', status: 'running', autonomy: 'approve', runs7: 412, success: 97.6, hours: 64, schedule: 'On new email', systems: ['Email', 'Accounting', 'ERP'] },
      { id: 'a2', name: 'Reconciliation', fn: 'Finance', desc: 'Matches bank lines to open invoices daily and routes mismatches to finance.', status: 'running', autonomy: 'auto', runs7: 98, success: 99.1, hours: 41, schedule: 'Daily at 06:00', systems: ['Accounting', 'Spreadsheets'] },
      { id: 'a3', name: 'Lead Router', fn: 'Sales', desc: 'Enriches inbound leads, scores them and assigns the right owner in the CRM.', status: 'running', autonomy: 'auto', runs7: 266, success: 98.4, hours: 38, schedule: 'On new lead', systems: ['CRM', 'Email'] },
      { id: 'a4', name: 'Deal Follow-up', fn: 'Sales', desc: 'Keeps every open deal moving with timely follow-ups based on its stage.', status: 'attention', autonomy: 'suggest', runs7: 143, success: 91.2, hours: 22, schedule: 'Hourly', systems: ['CRM', 'Email', 'Team chat'] },
      { id: 'a5', name: 'Order Capture', fn: 'Operations', desc: 'Turns order emails and PDFs into ERP orders and confirms delivery dates.', status: 'running', autonomy: 'approve', runs7: 351, success: 96.8, hours: 71, schedule: 'On new email', systems: ['Email', 'ERP'] },
      { id: 'a6', name: 'Supplier Chaser', fn: 'Operations', desc: 'Chases suppliers on late deliveries and logs every reply against the order.', status: 'running', autonomy: 'auto', runs7: 127, success: 95.3, hours: 29, schedule: 'Daily at 09:00', systems: ['Email', 'ERP', 'Spreadsheets'] },
      { id: 'a7', name: 'Support Triage', fn: 'Support', desc: 'Classifies tickets on arrival and drafts answers grounded in your documentation.', status: 'running', autonomy: 'approve', runs7: 524, success: 94.7, hours: 47, schedule: 'On new ticket', systems: ['Helpdesk', 'Docs'] },
      { id: 'a8', name: 'Candidate Screening', fn: 'People', desc: 'Shortlists applicants against role criteria and proposes interview slots.', status: 'paused', autonomy: 'suggest', runs7: 0, success: 92.5, hours: 0, schedule: 'On new application', systems: ['HRIS', 'Email'] }
    ];
    const approvals = [
      { id: 'p1', agent: 'a1', title: 'Post invoice from Rennes Metals — €12,480', summary: 'Amount is 18% above the PO. Agent recommends posting with a variance note.', risk: 'high', created: t - 12 * MIN, facts: [['Amount', '€12,480'], ['PO value', '€10,560'], ['Variance', '+18.2%']], reason: 'Unit price on line 3 changed from €42 to €51. The supplier price list was updated on 1 Sept and the contract allows annual indexation.' },
      { id: 'p2', agent: 'a7', title: 'Send refund reply to Atelier Brune', summary: 'Customer asks for a €340 refund on a damaged delivery. Draft reply ready.', risk: 'medium', created: t - 38 * MIN, facts: [['Refund', '€340'], ['Customer since', '2021'], ['Past refunds', '0']], reason: 'Photos attached confirm damage. Policy allows refunds under €500 without manager sign-off, but the account is flagged as strategic.' },
      { id: 'p3', agent: 'a4', title: 'Send follow-up to Halden Logistics', summary: 'Deal stalled for 14 days at proposal stage. Draft follow-up references their Q4 deadline.', risk: 'low', created: t - 1.6 * HOUR, facts: [['Deal value', '€48,000'], ['Stage', 'Proposal'], ['Idle', '14 days']], reason: 'Last email from the buyer mentioned a Q4 rollout. The follow-up proposes two dates for a technical call.' },
      { id: 'p4', agent: 'a5', title: 'Confirm order #8841 with new delivery date', summary: 'Stock shortage on one item. Agent proposes splitting the shipment.', risk: 'medium', created: t - 2.4 * HOUR, facts: [['Order', '#8841'], ['Lines', '12'], ['Delay', '+4 days on 1 line']], reason: 'Item SKU-2210 is short by 40 units. Splitting keeps 11 of 12 lines on the original date.' },
      { id: 'p5', agent: 'a2', title: 'Write off €3.20 rounding difference', summary: 'Bank fee rounding on a USD transfer. Below the €5 auto threshold set by finance.', risk: 'low', created: t - 3.1 * HOUR, facts: [['Amount', '€3.20'], ['Threshold', '€5.00'], ['Account', '627 Bank fees']], reason: 'Exchange-rate rounding between bank and invoice date. Same pattern was approved 6 times this quarter.' },
      { id: 'p6', agent: 'a6', title: 'Escalate late shipment from Okafor Parts', summary: 'Third reminder without reply. Agent proposes escalating to the account manager.', risk: 'low', created: t - 5.5 * HOUR, facts: [['PO', 'PO-55120'], ['Days late', '6'], ['Reminders', '3']], reason: 'No reply to the last three emails. The account manager contact is in the supplier record.' }
    ].map((a) => Object.assign({ status: 'pending' }, a));
    const workflows = [
      { id: 'w1', name: 'Invoice to ledger', trigger: 'New email in invoices@', steps: [['trig', 'Invoice email'], ['ag', 'Invoice Intake'], ['hu', 'Approve if > €5k'], ['ag', 'Post to accounting']], enabled: true, runs: 1840, avg: 14 },
      { id: 'w2', name: 'Lead to owner', trigger: 'New lead in CRM', steps: [['trig', 'New lead'], ['ag', 'Lead Router'], ['ag', 'Assign owner'], ['ag', 'Notify in chat']], enabled: true, runs: 1122, avg: 6 },
      { id: 'w3', name: 'Order to delivery', trigger: 'Order email received', steps: [['trig', 'Order email'], ['ag', 'Order Capture'], ['hu', 'Confirm changes'], ['ag', 'Supplier Chaser'], ['ag', 'Customer update']], enabled: true, runs: 1503, avg: 41 },
      { id: 'w4', name: 'Ticket to answer', trigger: 'New helpdesk ticket', steps: [['trig', 'New ticket'], ['ag', 'Support Triage'], ['hu', 'Review draft'], ['ag', 'Send reply']], enabled: true, runs: 2210, avg: 19 },
      { id: 'w5', name: 'Month-end close', trigger: 'Last business day, 18:00', steps: [['trig', 'Schedule'], ['ag', 'Reconciliation'], ['ag', 'Accruals check'], ['hu', 'Controller sign-off']], enabled: false, runs: 9, avg: 840 }
    ];
    const heat = {
      Finance: [62, 48, 20, 34, 6, 18], Sales: [30, 12, 44, 22, 26, 8], Operations: [70, 28, 52, 16, 30, 24],
      Support: [58, 10, 18, 12, 6, 30], People: [26, 14, 10, 8, 22, 6]
    };
    const covered = { Finance: [1, 1, 0, 0, 0, 1], Sales: [1, 0, 1, 0, 0, 0], Operations: [1, 0, 1, 0, 0, 0], Support: [1, 0, 0, 0, 0, 0], People: [0, 0, 0, 0, 0, 0] };
    const weekly = [118, 132, 141, 150, 163, 171, 184, 192, 207, 219, 231, 244];
    const runs = [];
    for (let i = 0; i < 90; i++) runs.push(makeRun(agents[i % 7], t - i * 23 * MIN - Math.random() * 20 * MIN));
    return {
      v: 1, ws: 'Northwind Supply', agents, approvals, workflows, heat, covered, weekly, runs,
      conns: { CRM: true, ERP: true, Accounting: true, Email: true, Docs: true, Spreadsheets: true, Helpdesk: true, 'Team chat': true, 'Data warehouse': false, HRIS: false },
      prefs: { theme: 'system', notify: { approvals: true, failures: true, digest: false } }
    };
  }

  function makeRun(agent, at, forced) {
    const r = Math.random();
    const status = forced || (r < 0.88 ? 'ok' : r < 0.96 ? 'warn' : 'bad');
    const titles = RUN_TITLES[agent.id] || ['Run completed'];
    const steps = (RUN_STEPS[agent.fn] || RUN_STEPS.Operations).map((l, i, arr) => ({ l, s: status === 'bad' && i === arr.length - 1 ? 'bad' : 'ok', d: +(0.2 + Math.random() * 2.4).toFixed(1) }));
    return { id: uid('r'), agent: agent.id, title: titles[Math.floor(Math.random() * titles.length)], status, at, dur: steps.reduce((s, x) => s + x.d, 0), steps };
  }

  /* ---------- state ---------- */
  const KEY = 'exior-os-v1';
  let S;
  try { S = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { S = null; }
  if (!S || S.v !== 1 || !S.agents) S = seed();
  function save() {
    S.runs = S.runs.slice(0, 160);
    try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* storage unavailable: keep in memory */ }
  }
  save();
  const agentById = (id) => S.agents.find((a) => a.id === id);
  const pending = () => S.approvals.filter((a) => a.status === 'pending');

  /* ---------- theme ---------- */
  const mq = matchMedia('(prefers-color-scheme: dark)');
  function applyTheme() {
    const t = S.prefs.theme;
    const dark = t === 'dark' || (t === 'system' && mq.matches);
    if (dark) document.documentElement.dataset.theme = 'dark'; else delete document.documentElement.dataset.theme;
    $('meta[name=theme-color]').content = dark ? '#0e0e10' : '#f3f3f1';
    $('#themeBtn').innerHTML = dark ? I.sun : I.moon;
  }
  mq.addEventListener && mq.addEventListener('change', applyTheme);
  function toggleTheme() {
    const dark = document.documentElement.dataset.theme === 'dark';
    S.prefs.theme = dark ? 'light' : 'dark'; save(); applyTheme();
    if (route.name === 'settings') render();
  }

  /* ---------- status helpers ---------- */
  const AG_ST = { running: ['ok', 'Running', I.check], attention: ['warn', 'Needs attention', I.alert], paused: ['off', 'Paused', I.pause] };
  const RUN_ST = { ok: ['ok', 'Succeeded', I.check], warn: ['warn', 'Routed to human', I.alert], bad: ['bad', 'Failed', I.x] };
  const RISK = { low: ['ok', 'Low risk'], medium: ['warn', 'Medium risk'], high: ['bad', 'High risk'] };
  const AUTON = { suggest: 'Suggest only', approve: 'Act with approval', auto: 'Autonomous' };
  const stBadge = (m) => `<span class="st ${m[0]}">${m[2] || ''}${m[1]}</span>`;

  /* ---------- routing ---------- */
  const NAV = [
    { k: 'overview', l: 'Overview', i: 'home', key: 'o' },
    { k: 'inbox', l: 'Approvals', i: 'inbox', key: 'i' },
    { k: 'agents', l: 'Agents', i: 'agent', key: 'a' },
    { k: 'workflows', l: 'Workflows', i: 'flow', key: 'w' },
    { k: 'map', l: 'Company map', i: 'map', key: 'm' },
    { k: 'runs', l: 'Runs', i: 'runs', key: 'r' },
    { k: 'settings', l: 'Settings', i: 'gear', key: 's' }
  ];
  let route = { name: 'overview', arg: null };
  function parse() {
    const h = location.hash.replace(/^#\/?/, '').split('/');
    const name = NAV.some((n) => n.k === h[0]) ? h[0] : 'overview';
    route = { name, arg: h[1] ? decodeURIComponent(h[1]) : null };
  }
  const go = (name, arg) => { location.hash = '#/' + name + (arg ? '/' + encodeURIComponent(arg) : ''); };
  window.addEventListener('hashchange', () => { parse(); closeDrawer(true); closeSheet(); render(); $('#content').scrollTop = 0; });

  function renderNav() {
    const p = pending().length;
    const cnt = { inbox: p, agents: S.agents.length, workflows: S.workflows.length };
    $('#nav').innerHTML = '<small>Workspace</small>' + NAV.map((n, i) =>
      (i === 4 ? '<small>Company</small>' : '') +
      `<a href="#/${n.k}" class="${route.name === n.k ? 'on' : ''}" title="${n.l}" ${route.name === n.k ? 'aria-current="page"' : ''}>${I[n.i]}<span>${n.l}</span>${cnt[n.k] != null ? `<span class="cnt ${n.k === 'inbox' && p ? 'hot' : ''}">${cnt[n.k]}</span>` : ''}</a>`
    ).join('');
    const b = ['overview', 'inbox', 'agents', 'runs'];
    $('#bnav').innerHTML = b.map((k) => { const n = NAV.find((x) => x.k === k); return `<a href="#/${k}" class="${route.name === k ? 'on' : ''}">${I[n.i].replace('width="16" height="16"', 'width="20" height="20"')}${n.l === 'Company map' ? 'Map' : n.l}${k === 'inbox' && p ? `<span class="badge">${p}</span>` : ''}</a>`; }).join('') +
      `<button id="moreBtn" class="${['workflows', 'map', 'settings'].includes(route.name) ? 'on' : ''}">${I.more.replace('width="16" height="16"', 'width="20" height="20"')}More</button>`;
    $('#moreBtn').onclick = openSheet;
    $('#liveCount').textContent = S.agents.filter((a) => a.status !== 'paused').length;
    $('#wsName').textContent = S.ws;
  }
  function renderCrumbs(extra) {
    const n = NAV.find((x) => x.k === route.name);
    $('#crumbs').innerHTML = `<span class="hide-m">${esc(S.ws)}</span><span class="hide-m">/</span><b>${n.l}</b>${extra ? `<span>/</span><b>${esc(extra)}</b>` : ''}`;
    document.title = n.l + ' · EXIOR OS';
  }

  /* ---------- views ---------- */
  const V = {};
  function render() {
    renderNav(); renderCrumbs();
    const c = $('#content');
    c.innerHTML = `<div class="page" id="page">${V[route.name]()}</div>`;
    (V[route.name + 'After'] || (() => {}))();
  }

  /* Overview */
  V.overview = function () {
    const h = new Date().getHours();
    const greet = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
    const runs7 = S.agents.reduce((s, a) => s + a.runs7, 0);
    const recent = S.runs.filter((r) => now() - r.at < 7 * DAY);
    const auto = recent.length ? Math.round(recent.filter((r) => r.status === 'ok').length / recent.length * 100) : 0;
    const p = pending();
    const w = S.weekly;
    const thisMonth = w.slice(-4).reduce((a, b) => a + b, 0);
    const prevMonth = w.slice(-8, -4).reduce((a, b) => a + b, 0);
    return `
    <div class="ph">
      <div><h1>${greet}, Claire</h1><p>${new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })} · ${p.length ? `${p.length} decision${p.length > 1 ? 's' : ''} waiting for you` : 'Nothing waiting for you'}</p></div>
      <div class="acts"><button class="btn btn-light" data-act="palette">${I.search}Ask or jump</button><button class="btn btn-dark" data-act="new-workflow">${I.plus}New workflow</button></div>
    </div>
    <div class="grid g4" style="margin-bottom:16px">
      ${kpi('Hours reclaimed', fmtN(thisMonth), 'h', `<span class="up">↑ ${Math.round((thisMonth / prevMonth - 1) * 100)}%</span> vs previous 4 weeks`, w.slice(-8))}
      ${kpi('Agent runs · 7 days', fmtN(runs7), '', `<span class="up">↑ 9%</span> vs last week`, [8, 9, 9, 11, 10, 12, 13, 14])}
      ${kpi('Resolved without a human', auto, '%', 'Last 7 days, all agents', [90, 91, 93, 92, 94, 93, 95, auto / 1.03])}
      <a class="card kpi" href="#/inbox" style="display:block"><div class="lbl">${I.inbox}Waiting for you</div><div class="val">${p.length}<small>approvals</small></div><div class="delta">${p.filter((x) => x.risk === 'high').length ? `<span class="down">${p.filter((x) => x.risk === 'high').length} high risk</span> · ` : ''}Review now →</div></a>
    </div>
    <div class="grid g-main" style="margin-bottom:16px">
      <div class="card">
        <div class="card-h"><div><h3>Hours reclaimed per week</h3><div class="muted" style="font-size:12.5px;margin-top:2px">All agents · last 12 weeks</div></div><div class="seg" role="group" aria-label="View"><button aria-pressed="true" data-view="chart">${I.chart}</button><button aria-pressed="false" data-view="table">${I.table}</button></div></div>
        <div class="card-b" id="weeklyBox">${barChart(w)}</div>
      </div>
      <div class="card">
        <div class="card-h"><h3>Needs you</h3><a href="#/inbox">Open approvals →</a></div>
        <div class="list" style="margin-top:8px">${p.slice(0, 4).map((a) => `
          <div class="li click" data-open-approval="${a.id}">
            <span class="ic ${RISK[a.risk][0]}">${a.risk === 'high' ? I.alert : I.inbox}</span>
            <div class="t"><b>${esc(a.title)}</b><span>${esc(agentById(a.agent).name)} · ${ago(a.created)}</span></div>
            <div class="r"><button class="iconbtn" title="Approve" data-approve="${a.id}">${I.check}</button></div>
          </div>`).join('') || `<div class="empty">${I.check.replace('width="16" height="16"', 'width="28" height="28"')}<b>All clear</b>No decisions waiting.</div>`}</div>
      </div>
    </div>
    <div class="grid g-main">
      <div class="card">
        <div class="card-h"><h3>Agents</h3><a href="#/agents">All agents →</a></div>
        <div class="list" style="margin-top:8px">${S.agents.map((a) => `
          <div class="li click" data-agent="${a.id}">
            <span class="ic ${AG_ST[a.status][0] === 'off' ? '' : AG_ST[a.status][0]}">${I.agent}</span>
            <div class="t"><b>${esc(a.name)}</b><span>${a.fn} · ${AUTON[a.autonomy]}</span></div>
            <div class="r"><span class="time hide-m">${a.runs7} runs</span>${stBadge(AG_ST[a.status])}</div>
          </div>`).join('')}</div>
      </div>
      <div class="card">
        <div class="card-h"><h3>Live activity</h3><a href="#/runs">All runs →</a></div>
        <div class="list feed" id="feed" style="margin-top:8px">${S.runs.slice(0, 7).map(feedItem).join('')}</div>
      </div>
    </div>`;
  };
  V.overviewAfter = function () {
    bindChart();
    $$('[data-view]').forEach((b) => b.onclick = () => {
      $$('[data-view]').forEach((x) => x.setAttribute('aria-pressed', x === b));
      $('#weeklyBox').innerHTML = b.dataset.view === 'chart' ? barChart(S.weekly) : weeklyTable();
      bindChart();
    });
  };
  function kpi(label, val, unit, delta, spark) {
    return `<div class="card kpi"><div class="lbl">${label}</div><div class="val">${val}${unit ? `<small>${unit}</small>` : ''}</div><div class="delta">${delta}</div>${sparkline(spark)}</div>`;
  }
  function sparkline(d) {
    const W = 72, H = 26, mx = Math.max(...d), mn = Math.min(...d);
    const pts = d.map((v, i) => [i / (d.length - 1) * W, H - 2 - (v - mn) / ((mx - mn) || 1) * (H - 4)]);
    return `<svg class="spark" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true"><polyline points="${pts.map((p) => p.join(',')).join(' ')}" fill="none" stroke="var(--accent2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${pts[pts.length - 1][0]}" cy="${pts[pts.length - 1][1]}" r="2.5" fill="var(--accent)"/></svg>`;
  }
  const weekLabel = (i, n) => { const d = new Date(now() - (n - 1 - i) * 7 * DAY); return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }); };
  function barChart(d) {
    const narrow = window.innerWidth < 720, W = narrow ? 360 : 640, H = narrow ? 200 : 230, pl = 30, pb = 26, pt = 10, n = d.length;
    const raw = Math.max(...d), step = [10, 20, 25, 50, 100, 200, 250, 500, 1000].find((x) => raw / x <= 5) || 1000;
    const max = Math.ceil(raw / step) * step, ticks = max / step;
    const bw = (W - pl) / n, gap = Math.max(6, bw * 0.34);
    let g = '';
    for (let k = 0; k <= ticks; k++) { const y = pt + (H - pt - pb) * (1 - k / ticks); g += `<line class="gridl" x1="${pl}" x2="${W}" y1="${y}" y2="${y}"/><text class="axis" x="${pl - 8}" y="${y + 3.5}" text-anchor="end">${step * k}</text>`; }
    const bars = d.map((v, i) => {
      const x = pl + i * bw + gap / 2, w = bw - gap, h = (H - pt - pb) * v / max, y = H - pb - h, r = Math.min(4, w / 2);
      const path = `M${x},${H - pb}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${H - pb}Z`;
      return `<path class="bar ${i === n - 1 ? 'cur' : ''}" data-i="${i}" d="${path}"/>` +
        ((n - 1 - i) % (narrow ? 3 : 2) === 0 ? `<text class="axis" x="${x + w / 2}" y="${H - 8}" text-anchor="middle">${weekLabel(i, n)}</text>` : '') +
        `<rect class="hit" data-i="${i}" x="${pl + i * bw}" y="${pt}" width="${bw}" height="${H - pt - pb}"/>`;
    }).join('');
    return `<div class="chart" id="wchart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Hours reclaimed per week, last 12 weeks, from ${d[0]} to ${d[n - 1]} hours">${g}${bars}</svg><div class="tip" id="wtip"></div></div>`;
  }
  function weeklyTable() {
    return `<div class="tbl-wrap" style="max-height:236px"><table><thead><tr><th>Week of</th><th style="text-align:right">Hours reclaimed</th></tr></thead><tbody>${S.weekly.map((v, i) => `<tr style="cursor:default"><td>${weekLabel(i, S.weekly.length)}</td><td style="text-align:right" class="mono">${v} h</td></tr>`).reverse().join('')}</tbody></table></div>`;
  }
  function bindChart() {
    const c = $('#wchart'); if (!c) return;
    const tip = $('#wtip'), svg = $('svg', c);
    $$('.hit', c).forEach((h) => {
      const show = () => {
        const i = +h.dataset.i, v = S.weekly[i], prev = S.weekly[i - 1];
        $$('.bar', c).forEach((b) => b.classList.toggle('hl', +b.dataset.i === i));
        tip.innerHTML = `<span style="opacity:.7">Week of ${weekLabel(i, S.weekly.length)}</span><b>${v} hours</b>${prev ? `<span style="opacity:.7">${v >= prev ? '+' : ''}${v - prev} vs prior week</span>` : ''}`;
        const bar = $(`.bar[data-i="${i}"]`, c).getBBox(), sc = svg.clientWidth / svg.viewBox.baseVal.width;
        tip.style.left = (bar.x + bar.width / 2) * sc + 'px'; tip.style.top = bar.y * sc + 'px'; tip.classList.add('on');
      };
      h.addEventListener('mouseenter', show); h.addEventListener('click', show);
      h.addEventListener('mouseleave', () => { tip.classList.remove('on'); $$('.bar', c).forEach((b) => b.classList.remove('hl')); });
    });
  }
  function feedItem(r) {
    const a = agentById(r.agent) || { name: 'Agent' };
    return `<div class="li click" data-run="${r.id}"><span class="ic ${RUN_ST[r.status][0]}">${RUN_ST[r.status][2]}</span><div class="t"><b>${esc(r.title)}</b><span>${esc(a.name)} · ${fmtDur(r.dur)}</span></div><span class="time">${ago(r.at)}</span></div>`;
  }

  /* Inbox */
  let inboxFilter = 'pending';
  V.inbox = function () {
    const list = S.approvals.filter((a) => inboxFilter === 'all' || a.status === inboxFilter);
    const counts = { pending: pending().length, approved: S.approvals.filter((a) => a.status === 'approved').length, rejected: S.approvals.filter((a) => a.status === 'rejected').length, all: S.approvals.length };
    let sel = route.arg && list.find((a) => a.id === route.arg) ? route.arg : (list[0] && list[0].id);
    const showing = !!route.arg && !!list.find((a) => a.id === route.arg);
    return `
    <div class="ph"><div><h1>Approvals</h1><p>Decisions your agents can't take alone. <span class="hide-m"><span class="kbd">J</span> <span class="kbd">K</span> to move, <span class="kbd">A</span> approve, <span class="kbd">R</span> reject.</span></p></div>
      <div class="chips" role="group" aria-label="Filter">${['pending', 'approved', 'rejected', 'all'].map((f) => `<button class="chip" data-filter="${f}" aria-pressed="${inboxFilter === f}">${f[0].toUpperCase() + f.slice(1)} <span class="n">${counts[f]}</span></button>`).join('')}</div></div>
    <div class="card inbox ${showing ? 'showing' : ''}" id="inbox">
      <div class="q" role="listbox" aria-label="Approvals">${list.map((a) => `
        <div class="qi ${a.id === sel ? 'on' : ''}" role="option" aria-selected="${a.id === sel}" data-sel="${a.id}">
          <span class="ic ${RISK[a.risk][0]}">${a.risk === 'high' ? I.alert : I.agent}</span>
          <div class="t"><b>${esc(a.title)}</b><span>${esc(a.summary)}</span>
            <div class="meta"><span class="st ${RISK[a.risk][0]}">${RISK[a.risk][1]}</span>${a.status !== 'pending' ? stBadge(a.status === 'approved' ? ['ok', 'Approved', I.check] : ['off', 'Rejected', I.x]) : ''}<span class="time">${ago(a.created)}</span></div></div>
        </div>`).join('') || `<div class="empty">${I.check.replace('width="16" height="16"', 'width="28" height="28"')}<b>Inbox zero</b>Your agents have everything they need.</div>`}</div>
      <div class="detail" id="detail">${sel ? approvalDetail(S.approvals.find((a) => a.id === sel)) : `<div class="empty"><b>Nothing selected</b></div>`}</div>
    </div>`;
  };
  function approvalDetail(a) {
    const ag = agentById(a.agent);
    return `
      <button class="btn btn-ghost btn-sm back" data-act="inbox-back">${I.back}Back</button>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px"><span class="st ${RISK[a.risk][0]}">${RISK[a.risk][1]}</span><span class="muted" style="font-size:12.5px">from <a href="#" data-agent="${ag.id}" style="color:var(--ink);font-weight:500">${esc(ag.name)}</a> · ${ago(a.created)}</span></div>
      <h2>${esc(a.title)}</h2>
      <p class="sub">${esc(a.summary)}</p>
      <div class="kv">${a.facts.map((f) => `<div><span>${esc(f[0])}</span><b>${esc(f[1])}</b></div>`).join('')}</div>
      <div class="eyebrow" style="margin-bottom:8px">Agent reasoning</div>
      <p class="reason">${esc(a.reason)}</p>
      <div class="eyebrow" style="margin-bottom:6px">Plan if approved</div>
      <div class="steps" style="margin-bottom:20px">${(RUN_STEPS[ag.fn] || []).slice(-2).concat(['Log decision and notify']).map((l) => `<div class="stp"><span class="b"></span>${esc(l)}</div>`).join('')}</div>
      ${a.status === 'pending' ? `<div class="dacts"><button class="btn btn-ok" data-approve="${a.id}">${I.check}Approve <span class="kbd hide-m" style="background:transparent;border-color:rgba(255,255,255,.35);color:inherit">A</span></button><button class="btn btn-light" data-reject="${a.id}">${I.x}Reject <span class="kbd hide-m">R</span></button><button class="btn btn-ghost" data-agent="${ag.id}">Open agent</button></div>`
        : `<div class="dacts">${stBadge(a.status === 'approved' ? ['ok', 'Approved', I.check] : ['off', 'Rejected', I.x])}<button class="btn btn-ghost btn-sm" data-undo-decision="${a.id}">Move back to pending</button></div>`}`;
  }
  V.inboxAfter = function () {
    $$('[data-filter]').forEach((b) => b.onclick = () => { inboxFilter = b.dataset.filter; route.arg = null; history.replaceState(null, '', '#/inbox'); render(); });
  };
  function inboxMove(dir) {
    const items = $$('.qi'); if (!items.length) return;
    let i = items.findIndex((x) => x.classList.contains('on'));
    i = Math.max(0, Math.min(items.length - 1, i + dir));
    selectApproval(items[i].dataset.sel);
    items[i].scrollIntoView({ block: 'nearest' });
  }
  function selectApproval(id) {
    $$('.qi').forEach((x) => { const on = x.dataset.sel === id; x.classList.toggle('on', on); x.setAttribute('aria-selected', on); });
    $('#detail').innerHTML = approvalDetail(S.approvals.find((a) => a.id === id));
    $('#inbox').classList.add('showing');
    history.replaceState(null, '', '#/inbox/' + id); route.arg = id;
  }
  function decide(id, verdict) {
    const a = S.approvals.find((x) => x.id === id); if (!a || a.status !== 'pending') return;
    const items = $$('.qi'); const idx = items.findIndex((x) => x.dataset.sel === id);
    a.status = verdict; a.decided = now(); save();
    if (verdict === 'approved') { const ag = agentById(a.agent); S.runs.unshift(Object.assign(makeRun(ag, now(), 'ok'), { title: 'Approved: ' + a.title })); save(); }
    toast(`${verdict === 'approved' ? 'Approved' : 'Rejected'} · ${a.title}`, () => { a.status = 'pending'; save(); render(); });
    if (route.name === 'inbox') {
      const rest = S.approvals.filter((x) => inboxFilter === 'all' || x.status === inboxFilter);
      const next = inboxFilter === 'pending' ? (rest[Math.min(idx, rest.length - 1)] || null) : a;
      route.arg = next ? next.id : null;
      history.replaceState(null, '', '#/inbox' + (next ? '/' + next.id : ''));
      render();
      if (!next || window.innerWidth <= 720) { const ib = $('#inbox'); ib && ib.classList.remove('showing'); }
    } else render();
  }

  /* Agents */
  let agentFilter = 'all', agentQ = '';
  V.agents = function () {
    const f = S.agents.filter((a) => (agentFilter === 'all' || a.status === agentFilter) && (a.name + ' ' + a.fn + ' ' + a.desc).toLowerCase().includes(agentQ.toLowerCase()));
    const c = (s) => S.agents.filter((a) => s === 'all' || a.status === s).length;
    return `
    <div class="ph"><div><h1>Agents</h1><p>${S.agents.length} agents across ${new Set(S.agents.map((a) => a.fn)).size} functions.</p></div><div class="acts"><button class="btn btn-dark" data-act="new-agent">${I.plus}New agent</button></div></div>
    <div class="toolbar"><input class="input" id="agentQ" placeholder="Search agents…" value="${esc(agentQ)}" aria-label="Search agents"><div class="chips">${[['all', 'All'], ['running', 'Running'], ['attention', 'Attention'], ['paused', 'Paused']].map(([k, l]) => `<button class="chip" data-af="${k}" aria-pressed="${agentFilter === k}">${l} <span class="n">${c(k)}</span></button>`).join('')}</div></div>
    <div class="agrid" id="agrid">${f.map(agentCard).join('') || `<div class="card empty" style="grid-column:1/-1"><b>No agents match</b>Try another search or filter.</div>`}</div>`;
  };
  function agentCard(a) {
    return `<div class="card acard" data-agent="${a.id}" tabindex="0" role="button" aria-label="Open ${esc(a.name)}">
      <div class="hd"><span class="ic ${AG_ST[a.status][0] === 'off' ? '' : AG_ST[a.status][0]}">${I.agent}</span><div><b>${esc(a.name)}</b><span>${a.fn}</span></div>${stBadge(AG_ST[a.status])}</div>
      <p>${esc(a.desc)}</p>
      <div><div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:6px"><span>Success rate</span><span class="mono">${a.success}%</span></div><div class="meter"><i style="width:${a.success}%"></i></div></div>
      <div class="astats"><div><span>Runs · 7d</span><b>${fmtN(a.runs7)}</b></div><div><span>Hours saved</span><b>${a.hours} h</b></div><div><span>Mode</span><b style="font-size:13px">${AUTON[a.autonomy].split(' ')[0]}</b></div></div>
    </div>`;
  }
  V.agentsAfter = function () {
    const q = $('#agentQ');
    q.oninput = () => { agentQ = q.value; const pos = q.selectionStart; render(); const n = $('#agentQ'); n.focus(); n.setSelectionRange(pos, pos); };
    $$('[data-af]').forEach((b) => b.onclick = () => { agentFilter = b.dataset.af; render(); });
    if (route.arg && agentById(route.arg)) openAgent(route.arg);
  };

  /* Workflows */
  V.workflows = function () {
    return `
    <div class="ph"><div><h1>Workflows</h1><p>How work moves between triggers, agents and people.</p></div><div class="acts"><button class="btn btn-dark" data-act="new-workflow">${I.plus}New workflow</button></div></div>
    <div class="legend" style="margin-bottom:14px"><span><i style="background:var(--info)"></i>Trigger</span><span><i style="background:var(--accent2)"></i>Agent step</span><span><i style="background:var(--warn)"></i>Human step</span></div>
    <div class="grid">${S.workflows.map((w) => `
      <div class="card wf" id="wf-${w.id}">
        <div class="hd"><span class="ic ${w.enabled ? 'ok' : ''}">${I.flow}</span><div><b>${esc(w.name)}</b><span>${esc(w.trigger)}</span></div>
          <div class="r"><span class="muted hide-m" style="font-size:12.5px">${w.enabled ? 'Enabled' : 'Disabled'}</span><button class="switch" role="switch" aria-checked="${w.enabled}" aria-label="Enable ${esc(w.name)}" data-wf-toggle="${w.id}"></button></div></div>
        <div class="chain">${w.steps.map((s, i) => (i ? '<span class="link"></span>' : '') + `<span class="node ${s[0]}" data-n="${i}"><i></i>${esc(s[1])}</span>`).join('')}</div>
        <div class="ft"><span>${I.bolt.replace('<svg', '<svg style="display:inline;vertical-align:-3px;margin-right:4px"')}${fmtN(w.runs)} runs</span><span>${I.clock.replace('<svg', '<svg style="display:inline;vertical-align:-3px;margin-right:4px"')}avg ${fmtDur(w.avg)}</span><button class="btn btn-light btn-sm" data-wf-run="${w.id}" ${w.enabled ? '' : 'disabled style="opacity:.5;cursor:not-allowed"'}>${I.play}Run now</button></div>
      </div>`).join('')}</div>`;
  };
  function runWorkflow(id) {
    const w = S.workflows.find((x) => x.id === id), el = $('#wf-' + id); if (!w || !el) return;
    const btn = $('[data-wf-run]', el); btn.disabled = true; btn.innerHTML = 'Running…';
    const nodes = $$('.node', el); let i = 0;
    const step = () => {
      if (i > 0) { nodes[i - 1].classList.remove('run'); nodes[i - 1].classList.add('done'); }
      if (i === nodes.length) {
        w.runs++; save();
        const agName = w.steps.find((s) => s[0] === 'ag'); const ag = S.agents.find((a) => agName && a.name === agName[1]) || S.agents[0];
        S.runs.unshift(Object.assign(makeRun(ag, now(), 'ok'), { title: 'Workflow run: ' + w.name })); save();
        toast(`${w.name} completed`, null, 'View run', () => go('runs'));
        setTimeout(() => { if (route.name === 'workflows') render(); }, 900);
        return;
      }
      nodes[i].classList.add('run'); i++;
      setTimeout(step, reduce ? 50 : 650);
    };
    step();
  }

  /* Company map */
  let mapSel = null, mapView = 'heat';
  const seqVar = (v, max) => `var(--seq${Math.min(5, Math.floor(v / max * 5.999))})`;
  V.map = function () {
    const max = Math.max(...Object.values(S.heat).flat());
    const total = Object.values(S.heat).flat().reduce((a, b) => a + b, 0);
    const cov = FUNCS.reduce((s, f) => s + S.heat[f].reduce((x, v, i) => x + (S.covered[f][i] ? v : 0), 0), 0);
    if (!mapSel) mapSel = ['Operations', 0];
    return `
    <div class="ph"><div><h1>Company map</h1><p>Manual hours per month, by function and type of work. Darker means more time spent.</p></div>
      <div class="seg" role="group" aria-label="View"><button aria-pressed="${mapView === 'heat'}" data-mv="heat">${I.map} Map</button><button aria-pressed="${mapView === 'table'}" data-mv="table">${I.table} Table</button></div></div>
    <div class="grid g4" style="margin-bottom:16px">
      <div class="card kpi"><div class="lbl">Manual hours mapped</div><div class="val">${fmtN(total)}<small>h / month</small></div></div>
      <div class="card kpi"><div class="lbl">Covered by agents</div><div class="val">${Math.round(cov / total * 100)}<small>%</small></div><div class="delta">${fmtN(cov)} h / month</div></div>
      <div class="card kpi"><div class="lbl">Largest gap</div><div class="val" style="font-size:22px">${largestGap().join(' · ')}</div></div>
      <div class="card kpi"><div class="lbl">Functions</div><div class="val">${FUNCS.length}</div><div class="delta">${ACTS.length} types of work</div></div>
    </div>
    <div class="grid g-main">
      <div class="card"><div class="card-h"><h3>Where the hours go</h3><div class="scale"><span>Less</span><span class="sw">${[0, 1, 2, 3, 4, 5].map((k) => `<i style="background:var(--seq${k})"></i>`).join('')}</span><span>More</span></div></div>
        <div class="card-b" style="overflow-x:auto">${mapView === 'heat' ? `
          <div class="heat" style="grid-template-columns:96px repeat(${ACTS.length},minmax(46px,1fr));min-width:420px">
            <span></span>${ACTS.map((a) => `<span class="ch" title="${a}">${a}</span>`).join('')}
            ${FUNCS.map((f) => `<span class="rh">${f}</span>` + S.heat[f].map((v, i) => `<button class="cell ${mapSel[0] === f && mapSel[1] === i ? 'on' : ''}" style="background:${seqVar(v, max)};color:${v / max > .55 ? 'var(--seqhi)' : 'var(--ink)'}" data-cell="${f}|${i}" aria-label="${f}, ${ACTS[i]}: ${v} hours per month${S.covered[f][i] ? ', covered by an agent' : ''}">${v}${S.covered[f][i] ? '•' : ''}</button>`).join('')).join('')}
          </div><p class="muted" style="font-size:12px;margin:12px 0 0">• covered by an agent. Select a cell for details.</p>` :
      `<div class="tbl-wrap"><table><thead><tr><th>Function</th>${ACTS.map((a) => `<th style="text-align:right">${a}</th>`).join('')}<th style="text-align:right">Total</th></tr></thead><tbody>${FUNCS.map((f) => `<tr style="cursor:default"><td><b style="font-weight:500">${f}</b></td>${S.heat[f].map((v, i) => `<td class="mono" style="text-align:right">${v}${S.covered[f][i] ? '•' : ''}</td>`).join('')}<td class="mono" style="text-align:right">${S.heat[f].reduce((a, b) => a + b, 0)}</td></tr>`).join('')}</tbody></table></div>`}
        </div></div>
      <div class="card" id="cellDetail">${cellDetail()}</div>
    </div>`;
  };
  function largestGap() {
    let best = ['', '', -1];
    FUNCS.forEach((f) => S.heat[f].forEach((v, i) => { if (!S.covered[f][i] && v > best[2]) best = [f, ACTS[i], v]; }));
    return best.slice(0, 2);
  }
  function cellDetail() {
    const [f, i] = mapSel, v = S.heat[f][i], cov = S.covered[f][i];
    const agents = S.agents.filter((a) => a.fn === f);
    return `<div class="card-h"><div><div class="eyebrow">${f}</div><h3 style="margin-top:4px;font-size:18px">${ACTS[i]}</h3></div>${cov ? stBadge(['ok', 'Covered', I.check]) : stBadge(['warn', 'Gap', I.alert])}</div>
      <div class="card-b">
        <div class="kv" style="grid-template-columns:1fr 1fr"><div><span>Manual time</span><b>${v} h / month</b></div><div><span>Est. reclaimable</span><b>${Math.round(v * (cov ? 0.15 : 0.7))} h</b></div></div>
        <div class="eyebrow" style="margin-bottom:8px">Recommendation</div>
        <p class="reason">${cov ? `An agent already handles most of this work. Review its exceptions to push coverage further.` : `This work is repetitive and rule-based. A ${f.toLowerCase()} agent with approval on exceptions would take it over.`}</p>
        <div class="eyebrow" style="margin-bottom:6px">${f} agents</div>
        <div class="list" style="margin:0 -18px">${agents.map((a) => `<div class="li click" data-agent="${a.id}"><span class="ic">${I.agent}</span><div class="t"><b>${esc(a.name)}</b><span>${AUTON[a.autonomy]}</span></div>${stBadge(AG_ST[a.status])}</div>`).join('') || '<div class="li"><span class="muted">No agent yet</span></div>'}</div>
        ${cov ? '' : `<button class="btn btn-dark" style="width:100%;margin-top:14px" data-act="new-agent" data-fn="${f}">${I.plus}Create an agent for this</button>`}
      </div>`;
  }
  V.mapAfter = function () {
    $$('[data-mv]').forEach((b) => b.onclick = () => { mapView = b.dataset.mv; render(); });
    $$('[data-cell]').forEach((b) => b.onclick = () => {
      const [f, i] = b.dataset.cell.split('|'); mapSel = [f, +i];
      $$('.cell').forEach((c) => c.classList.toggle('on', c === b));
      $('#cellDetail').innerHTML = cellDetail();
      if (window.innerWidth <= 1180) $('#cellDetail').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  /* Runs */
  let runQ = '', runSt = 'all', runAg = 'all', runPage = 0;
  const PER = 12;
  V.runs = function () {
    const f = S.runs.filter((r) => (runSt === 'all' || r.status === runSt) && (runAg === 'all' || r.agent === runAg) &&
      (r.title + ' ' + (agentById(r.agent) || {}).name).toLowerCase().includes(runQ.toLowerCase()));
    const pages = Math.max(1, Math.ceil(f.length / PER)); runPage = Math.min(runPage, pages - 1);
    const rows = f.slice(runPage * PER, runPage * PER + PER);
    const c = (s) => S.runs.filter((r) => s === 'all' || r.status === s).length;
    return `
    <div class="ph"><div><h1>Runs</h1><p>Every action an agent took, step by step.</p></div></div>
    <div class="toolbar"><input class="input" id="runQ" placeholder="Search runs…" value="${esc(runQ)}" aria-label="Search runs">
      <select class="select" id="runAg" aria-label="Agent"><option value="all">All agents</option>${S.agents.map((a) => `<option value="${a.id}" ${runAg === a.id ? 'selected' : ''}>${esc(a.name)}</option>`).join('')}</select>
      <span class="sp"></span>
      <div class="chips">${[['all', 'All'], ['ok', 'Succeeded'], ['warn', 'Routed'], ['bad', 'Failed']].map(([k, l]) => `<button class="chip" data-rs="${k}" aria-pressed="${runSt === k}">${l} <span class="n">${c(k)}</span></button>`).join('')}</div></div>
    <div class="card" style="overflow:hidden">
      <div class="tbl-wrap"><table><thead><tr><th>Run</th><th class="hide-m">Agent</th><th>Status</th><th class="hide-m">Duration</th><th style="text-align:right">When</th></tr></thead>
      <tbody>${rows.map((r) => { const a = agentById(r.agent) || { name: '—', fn: '' }; return `<tr data-run="${r.id}" tabindex="0"><td><b style="font-weight:500">${esc(r.title)}</b><span class="subm">${esc(a.name)} · ${fmtDur(r.dur)}</span></td><td class="hide-m"><span class="who"><span class="dot ${a.status === 'paused' ? 'off' : 'ok'}"></span>${esc(a.name)}</span></td><td>${stBadge(RUN_ST[r.status])}</td><td class="mono hide-m">${fmtDur(r.dur)}</td><td style="text-align:right" class="time">${ago(r.at)}</td></tr>`; }).join('') || `<tr><td colspan="5"><div class="empty"><b>No runs match</b>Change the filters to see more.</div></td></tr>`}</tbody></table></div>
      <div class="pager"><span>${f.length ? `${runPage * PER + 1}–${Math.min(f.length, runPage * PER + PER)} of ${f.length}` : '0 runs'}</span><span style="display:flex;gap:6px"><button class="btn btn-light btn-sm" data-pg="-1" ${runPage === 0 ? 'disabled style="opacity:.45"' : ''}>Previous</button><button class="btn btn-light btn-sm" data-pg="1" ${runPage >= pages - 1 ? 'disabled style="opacity:.45"' : ''}>Next</button></span></div>
    </div>`;
  };
  V.runsAfter = function () {
    const q = $('#runQ');
    q.oninput = () => { runQ = q.value; runPage = 0; const pos = q.selectionStart; render(); const n = $('#runQ'); n.focus(); n.setSelectionRange(pos, pos); };
    $('#runAg').onchange = (e) => { runAg = e.target.value; runPage = 0; render(); };
    $$('[data-rs]').forEach((b) => b.onclick = () => { runSt = b.dataset.rs; runPage = 0; render(); });
    $$('[data-pg]').forEach((b) => b.onclick = () => { runPage += +b.dataset.pg; render(); });
  };

  /* Settings */
  V.settings = function () {
    const p = S.prefs;
    return `
    <div class="ph"><div><h1>Settings</h1><p>Workspace, appearance, notifications and connections.</p></div></div>
    <div class="set">
      <nav><a href="#s-ws">Workspace</a><a href="#s-app">Appearance</a><a href="#s-not">Notifications</a><a href="#s-con">Connections</a><a href="#s-data">Data</a></nav>
      <div>
        <section id="s-ws"><div class="eyebrow" style="margin-bottom:10px">Workspace</div><div class="card card-b">
          <div class="field"><label for="wsIn">Company name</label><input class="input" id="wsIn" value="${esc(S.ws)}"><span class="hint">Shown in the sidebar and on reports.</span></div>
          <button class="btn btn-dark btn-sm" id="wsSave">Save</button></div></section>
        <section id="s-app"><div class="eyebrow" style="margin-bottom:10px">Appearance</div><div class="card"><div class="row"><div class="t"><b>Theme</b><span>Follow the system or pick one.</span></div>
          <div class="seg" role="group" aria-label="Theme">${['system', 'light', 'dark'].map((t) => `<button aria-pressed="${p.theme === t}" data-theme-set="${t}">${t[0].toUpperCase() + t.slice(1)}</button>`).join('')}</div></div></div></section>
        <section id="s-not"><div class="eyebrow" style="margin-bottom:10px">Notifications</div><div class="card">${[['approvals', 'New approvals', 'Notify me when an agent needs a decision.'], ['failures', 'Failed runs', 'Notify me when a run fails.'], ['digest', 'Weekly digest', 'A Monday summary of hours reclaimed and open gaps.']].map(([k, t, d]) => `<div class="row"><div class="t"><b>${t}</b><span>${d}</span></div><button class="switch" role="switch" aria-checked="${!!p.notify[k]}" aria-label="${t}" data-notify="${k}"></button></div>`).join('')}</div></section>
        <section id="s-con"><div class="eyebrow" style="margin-bottom:10px">Connections</div><div class="card">${SYSTEMS.map((s) => `<div class="row"><span class="ic ${S.conns[s] ? 'ok' : ''}">${I.plug}</span><div class="t"><b>${s}</b><span>${S.conns[s] ? 'Connected · used by ' + S.agents.filter((a) => a.systems.includes(s)).length + ' agents' : 'Not connected'}</span></div><button class="btn ${S.conns[s] ? 'btn-light' : 'btn-dark'} btn-sm" data-conn="${s}">${S.conns[s] ? 'Disconnect' : 'Connect'}</button></div>`).join('')}</div></section>
        <section id="s-data"><div class="eyebrow" style="margin-bottom:10px">Data</div><div class="card"><div class="row"><div class="t"><b>Reset demo data</b><span>Restore the original agents, approvals and runs.</span></div><button class="btn btn-light btn-sm" data-act="reset" style="color:var(--bad)">${I.trash}Reset</button></div></div></section>
      </div>
    </div>`;
  };
  V.settingsAfter = function () {
    $('#wsSave').onclick = () => { const v = $('#wsIn').value.trim(); if (!v) return toast('Company name can’t be empty'); S.ws = v; save(); render(); toast('Workspace renamed'); };
    $$('[data-theme-set]').forEach((b) => b.onclick = () => { S.prefs.theme = b.dataset.themeSet; save(); applyTheme(); render(); });
    $$('[data-notify]').forEach((b) => b.onclick = () => { const k = b.dataset.notify; S.prefs.notify[k] = !S.prefs.notify[k]; save(); b.setAttribute('aria-checked', S.prefs.notify[k]); });
    $$('[data-conn]').forEach((b) => b.onclick = () => {
      const s = b.dataset.conn, used = S.agents.filter((a) => a.systems.includes(s)).length;
      if (S.conns[s] && used) {
        confirmModal(`Disconnect ${s}?`, `${used} agent${used > 1 ? 's use' : ' uses'} ${s}. They will pause actions that need it until you reconnect.`, 'Disconnect', () => { S.conns[s] = false; save(); render(); toast(`${s} disconnected`, () => { S.conns[s] = true; save(); render(); }); });
      } else { S.conns[s] = !S.conns[s]; save(); render(); toast(`${s} ${S.conns[s] ? 'connected' : 'disconnected'}`); }
    });
    $$('.set nav a').forEach((a) => a.onclick = (e) => { e.preventDefault(); $(a.getAttribute('href')).scrollIntoView({ behavior: 'smooth' }); });
  };

  /* ---------- drawer ---------- */
  let drawerTab = 'overview', drawerId = null;
  function openDrawer(html) {
    const d = $('#drawer'); d.innerHTML = html;
    d.classList.add('on'); $('#scrim').classList.add('on');
    setTimeout(() => { const f = $('.dh .iconbtn', d); f && f.focus(); }, 50);
  }
  function closeDrawer(silent) {
    if (!$('#drawer').classList.contains('on')) return;
    $('#drawer').classList.remove('on'); $('#scrim').classList.remove('on'); drawerId = null;
    if (!silent && route.name === 'agents' && route.arg) history.replaceState(null, '', '#/agents');
    if (!silent) route.arg = route.name === 'agents' ? null : route.arg;
  }
  $('#scrim').onclick = () => closeDrawer();

  function openAgent(id, tab) {
    const a = agentById(id); if (!a) return;
    drawerId = id; drawerTab = tab || (drawerId === id ? drawerTab : 'overview');
    if (route.name === 'agents') history.replaceState(null, '', '#/agents/' + id);
    const runs = S.runs.filter((r) => r.agent === id).slice(0, 12);
    const body = {
      overview: `
        <p style="margin:0 0 18px;color:var(--ink2);line-height:1.6">${esc(a.desc)}</p>
        <div class="kv"><div><span>Runs · 7d</span><b>${fmtN(a.runs7)}</b></div><div><span>Success</span><b>${a.success}%</b></div><div><span>Hours saved</span><b>${a.hours} h</b></div></div>
        <div class="field"><label>Autonomy</label><div class="seg" role="group" aria-label="Autonomy">${Object.entries(AUTON).map(([k, l]) => `<button aria-pressed="${a.autonomy === k}" data-auton="${k}">${l}</button>`).join('')}</div><span class="hint">${a.autonomy === 'suggest' ? 'The agent drafts, a person executes.' : a.autonomy === 'approve' ? 'The agent acts, risky actions wait in Approvals.' : 'The agent acts alone within its rules. Exceptions go to Approvals.'}</span></div>
        <div class="field"><label>Trigger</label><div class="muted">${I.clock.replace('<svg', '<svg style="display:inline;vertical-align:-3px;margin-right:6px"')}${esc(a.schedule)}</div></div>
        <div class="field"><label>Systems</label><div class="chips">${a.systems.map((s) => `<span class="chip" style="cursor:default">${S.conns[s] ? '<span class="dot ok"></span>' : '<span class="dot bad"></span>'}${s}</span>`).join('')}</div></div>`,
      runs: `<div class="list" style="margin:-20px">${runs.map(feedItem).join('') || '<div class="empty"><b>No runs yet</b>Runs appear here as soon as the agent works.</div>'}</div>`,
      config: `
        <div class="field"><label for="agName">Name</label><input class="input" id="agName" value="${esc(a.name)}"></div>
        <div class="field"><label for="agDesc">Instructions</label><textarea class="input" id="agDesc" rows="5">${esc(a.desc)}</textarea><span class="hint">Plain language. The agent follows these within its permissions.</span></div>
        <div class="field"><label for="agSched">Trigger</label><input class="input" id="agSched" value="${esc(a.schedule)}"></div>
        <button class="btn btn-dark" id="agSave">Save changes</button>`
    };
    openDrawer(`
      <div class="dh"><span class="ic ${AG_ST[a.status][0] === 'off' ? '' : AG_ST[a.status][0]}">${I.agent}</span><div><b>${esc(a.name)}</b><span>${a.fn} · ${stBadge(AG_ST[a.status])}</span></div><button class="iconbtn" data-act="close-drawer" aria-label="Close">${I.x}</button></div>
      <div class="dtabs" role="tablist">${[['overview', 'Overview'], ['runs', 'Runs'], ['config', 'Configure']].map(([k, l]) => `<button role="tab" aria-selected="${drawerTab === k}" data-dtab="${k}">${l}</button>`).join('')}</div>
      <div class="db">${body[drawerTab]}</div>
      <div class="df"><button class="btn btn-light" data-act="toggle-agent">${a.status === 'paused' ? I.play + 'Resume' : I.pause + 'Pause'}</button><span class="sp"></span><button class="btn btn-dark" data-act="run-agent" ${a.status === 'paused' ? 'disabled style="opacity:.5"' : ''}>${I.bolt}Run now</button></div>`);
    $$('[data-dtab]').forEach((b) => b.onclick = () => openAgent(id, b.dataset.dtab));
    $$('[data-auton]').forEach((b) => b.onclick = () => { a.autonomy = b.dataset.auton; save(); openAgent(id, 'overview'); refreshBehind(); toast(`${a.name}: ${AUTON[a.autonomy]}`); });
    const sv = $('#agSave');
    if (sv) sv.onclick = () => {
      const n = $('#agName').value.trim(); if (!n) return toast('Name can’t be empty');
      a.name = n; a.desc = $('#agDesc').value.trim() || a.desc; a.schedule = $('#agSched').value.trim() || a.schedule; save(); openAgent(id, 'config'); refreshBehind(); toast('Agent updated');
    };
  }
  function refreshBehind() { const id = drawerId; const t = drawerTab; render(); if (id) { drawerId = id; drawerTab = t; } }

  function openRun(id) {
    const r = S.runs.find((x) => x.id === id); if (!r) return;
    const a = agentById(r.agent) || { name: 'Agent', fn: '' };
    openDrawer(`
      <div class="dh"><span class="ic ${RUN_ST[r.status][0]}">${RUN_ST[r.status][2]}</span><div><b>${esc(r.title)}</b><span>${esc(a.name)} · ${new Date(r.at).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })}</span></div><button class="iconbtn" data-act="close-drawer" aria-label="Close">${I.x}</button></div>
      <div class="db">
        <div class="kv"><div><span>Status</span><b style="font-size:14px">${RUN_ST[r.status][1]}</b></div><div><span>Duration</span><b>${fmtDur(r.dur)}</b></div><div><span>Steps</span><b>${r.steps.length}</b></div></div>
        <div class="eyebrow" style="margin-bottom:6px">Trace</div>
        <div class="steps">${r.steps.map((s) => `<div class="stp ${s.s}"><span class="b">${s.s === 'ok' ? I.check.replace('width="16" height="16"', 'width="11" height="11"') : I.x.replace('width="16" height="16"', 'width="11" height="11"')}</span>${esc(s.l)}<span class="time">${s.d}s</span></div>`).join('')}</div>
        ${r.status !== 'ok' ? `<p class="reason" style="margin-top:18px">${r.status === 'warn' ? 'The agent found something outside its rules and handed it to a person.' : 'A connected system did not respond in time. The run can be retried safely.'}</p>` : ''}
      </div>
      <div class="df"><button class="btn btn-ghost" data-agent="${r.agent}">Open agent</button><span class="sp"></span>${r.status === 'bad' ? `<button class="btn btn-dark" data-retry="${r.id}">Retry run</button>` : ''}</div>`);
  }

  /* ---------- overlays: palette & modals ---------- */
  const ov = $('#palScrim');
  let palIdx = 0, palItems = [], lastFocus = null;
  function openOverlay(html) { lastFocus = document.activeElement; ov.innerHTML = html; ov.classList.add('on'); }
  function closeOverlay() { if (!ov.classList.contains('on')) return false; ov.classList.remove('on'); ov.innerHTML = ''; lastFocus && lastFocus.focus && lastFocus.focus(); return true; }
  ov.addEventListener('mousedown', (e) => { if (e.target === ov) closeOverlay(); });

  function commands() {
    const nav = NAV.map((n) => ({ g: 'Go to', l: n.l, i: I[n.i], k: 'G ' + n.key.toUpperCase(), run: () => go(n.k) }));
    const acts = [
      { g: 'Actions', l: 'Create a new agent', i: I.plus, run: () => newAgentModal() },
      { g: 'Actions', l: 'Create a new workflow', i: I.flow, run: () => newWorkflowModal() },
      { g: 'Actions', l: 'Approve all low-risk approvals', i: I.check, run: approveLowRisk },
      { g: 'Actions', l: document.documentElement.dataset.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme', i: document.documentElement.dataset.theme === 'dark' ? I.sun : I.moon, run: toggleTheme },
      { g: 'Actions', l: 'Keyboard shortcuts', i: I.keyb, k: '?', run: () => setTimeout(helpModal, 0) }
    ];
    const ags = S.agents.map((a) => ({ g: 'Agents', l: a.name, sub: a.fn, i: I.agent, run: () => { go('agents', a.id); } }));
    const aps = pending().map((a) => ({ g: 'Approvals', l: a.title, i: I.inbox, run: () => go('inbox', a.id) }));
    return nav.concat(acts, ags, aps);
  }
  function score(q, s) {
    if (!q) return 1; s = s.toLowerCase(); q = q.toLowerCase();
    if (s.includes(q)) return 100 - s.indexOf(q);
    let i = 0; for (const ch of s) if (ch === q[i]) i++;
    return i === q.length ? 10 : 0;
  }
  function openPalette() {
    openOverlay(`<div class="pal" role="combobox" aria-expanded="true"><div class="pal-in">${I.search}<input id="palIn" placeholder="Search agents, approvals, or type a command…" autocomplete="off" aria-label="Command"><span class="kbd">ESC</span></div><div class="pal-list" id="palList" role="listbox"></div>
      <div class="pal-f"><span><span class="kbd">↑</span><span class="kbd">↓</span>navigate</span><span><span class="kbd">↵</span>open</span><span class="hide-m"><span class="kbd">?</span>shortcuts</span></div></div>`);
    const inp = $('#palIn'); const all = commands();
    const draw = () => {
      const q = inp.value.trim();
      palItems = all.map((c) => Object.assign({ s: score(q, c.l + ' ' + (c.sub || '') + ' ' + c.g) }, c)).filter((c) => c.s > 0).sort((a, b) => q ? b.s - a.s : 0).slice(0, 14);
      palIdx = Math.min(palIdx, Math.max(0, palItems.length - 1));
      let g = '', html = '';
      palItems.forEach((c, i) => { if (c.g !== g) { g = c.g; html += `<div class="pal-g">${g}</div>`; } html += `<div class="pal-i ${i === palIdx ? 'on' : ''}" role="option" aria-selected="${i === palIdx}" data-pi="${i}">${c.i}<span>${esc(c.l)}${c.sub ? ` <span class="muted">· ${c.sub}</span>` : ''}</span>${c.k ? `<span class="kbd">${c.k}</span>` : ''}</div>`; });
      $('#palList').innerHTML = html || `<div class="empty"><b>No results</b>Try “approve” or an agent name.</div>`;
      const on = $('.pal-i.on'); on && on.scrollIntoView({ block: 'nearest' });
    };
    inp.oninput = () => { palIdx = 0; draw(); };
    inp.onkeydown = (e) => {
      if (e.key === 'ArrowDown') { palIdx = Math.min(palItems.length - 1, palIdx + 1); draw(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { palIdx = Math.max(0, palIdx - 1); draw(); e.preventDefault(); }
      else if (e.key === 'Enter' && palItems[palIdx]) { const c = palItems[palIdx]; closeOverlay(); c.run(); e.preventDefault(); }
    };
    $('#palList').onclick = (e) => { const el = e.target.closest('[data-pi]'); if (!el) return; const c = palItems[+el.dataset.pi]; closeOverlay(); c.run(); };
    $('#palList').onmousemove = (e) => { const el = e.target.closest('[data-pi]'); if (el && +el.dataset.pi !== palIdx) { palIdx = +el.dataset.pi; $$('.pal-i').forEach((x, i) => x.classList.toggle('on', i === palIdx)); } };
    palIdx = 0; draw(); inp.focus();
  }

  function modal(title, body, footer) {
    openOverlay(`<div class="modal" role="document"><div class="mh"><b>${title}</b><button class="iconbtn" data-act="close-overlay" aria-label="Close">${I.x}</button></div><div class="mb">${body}</div><div class="mf">${footer}</div></div>`);
    const f = $('.modal input, .modal select, .modal textarea'); (f || $('.modal .btn')).focus();
  }
  function confirmModal(title, text, label, onOk) {
    modal(title, `<p style="margin:0;color:var(--muted);line-height:1.6">${esc(text)}</p>`, `<button class="btn btn-light" data-act="close-overlay">Cancel</button><button class="btn btn-dark" id="cfOk">${label}</button>`);
    $('#cfOk').onclick = () => { closeOverlay(); onOk(); };
  }
  function newAgentModal(fn) {
    modal('New agent', `
      <div class="field"><label for="naName">Name</label><input class="input" id="naName" placeholder="e.g. Expense Checker"></div>
      <div class="field"><label for="naFn">Function</label><select class="select" id="naFn">${FUNCS.map((f) => `<option ${f === fn ? 'selected' : ''}>${f}</option>`).join('')}</select></div>
      <div class="field"><label for="naDesc">What should it do?</label><textarea class="input" id="naDesc" rows="3" placeholder="Describe the work in plain language."></textarea></div>
      <div class="field"><label>Autonomy</label><div class="seg" id="naAut">${Object.entries(AUTON).map(([k, l]) => `<button type="button" aria-pressed="${k === 'suggest'}" data-v="${k}">${l}</button>`).join('')}</div><span class="hint">New agents start safest: suggest only. You can raise it later.</span></div>`,
      `<button class="btn btn-light" data-act="close-overlay">Cancel</button><button class="btn btn-dark" id="naOk">Create agent</button>`);
    $$('#naAut button').forEach((b) => b.onclick = () => $$('#naAut button').forEach((x) => x.setAttribute('aria-pressed', x === b)));
    $('#naOk').onclick = () => {
      const name = $('#naName').value.trim();
      if (!name) { $('#naName').focus(); $('#naName').style.borderColor = 'var(--bad)'; return; }
      const a = { id: uid('a'), name, fn: $('#naFn').value, desc: $('#naDesc').value.trim() || 'New agent. Add instructions in Configure.', status: 'running', autonomy: $('#naAut [aria-pressed="true"]').dataset.v, runs7: 0, success: 100, hours: 0, schedule: 'Manual', systems: ['Email'] };
      S.agents.push(a); save(); closeOverlay(); go('agents', a.id); toast(`${a.name} created`);
    };
  }
  function newWorkflowModal() {
    modal('New workflow', `
      <div class="field"><label for="nwName">Name</label><input class="input" id="nwName" placeholder="e.g. Expense to reimbursement"></div>
      <div class="field"><label for="nwTrig">Trigger</label><select class="select" id="nwTrig"><option>New email</option><option>New record in CRM</option><option>New helpdesk ticket</option><option>Every weekday at 09:00</option></select></div>
      <div class="field"><label for="nwAg">Agent</label><select class="select" id="nwAg">${S.agents.map((a) => `<option value="${a.id}">${esc(a.name)} · ${a.fn}</option>`).join('')}</select></div>
      <label style="display:flex;align-items:center;gap:10px;font-weight:500"><button type="button" class="switch" role="switch" aria-checked="true" id="nwHu"></button>Add a human approval step</label>`,
      `<button class="btn btn-light" data-act="close-overlay">Cancel</button><button class="btn btn-dark" id="nwOk">Create workflow</button>`);
    $('#nwHu').onclick = (e) => e.currentTarget.setAttribute('aria-checked', e.currentTarget.getAttribute('aria-checked') !== 'true');
    $('#nwOk').onclick = () => {
      const name = $('#nwName').value.trim();
      if (!name) { $('#nwName').focus(); $('#nwName').style.borderColor = 'var(--bad)'; return; }
      const ag = agentById($('#nwAg').value), trig = $('#nwTrig').value;
      const steps = [['trig', trig], ['ag', ag.name]];
      if ($('#nwHu').getAttribute('aria-checked') === 'true') steps.push(['hu', 'Approve']);
      steps.push(['ag', 'Log and notify']);
      S.workflows.unshift({ id: uid('w'), name, trigger: trig, steps, enabled: true, runs: 0, avg: 0 });
      save(); closeOverlay(); go('workflows'); toast(`${name} created`);
    };
  }
  function helpModal() {
    const k = (s) => s.split(' ').map((x) => `<span class="kbd">${x}</span>`).join('');
    modal('Keyboard shortcuts', `<div class="keys">
      <span>Command palette</span><span>${k(isMac ? '⌘ K' : 'Ctrl K')}</span>
      <span>Search</span><span>${k('/')}</span>
      ${NAV.map((n) => `<span>Go to ${n.l}</span><span>${k('G ' + n.key.toUpperCase())}</span>`).join('')}
      <span>Next / previous approval</span><span>${k('J K')}</span>
      <span>Approve / reject</span><span>${k('A R')}</span>
      <span>Toggle theme</span><span>${k('T')}</span>
      <span>Close</span><span>${k('Esc')}</span></div>`, `<button class="btn btn-dark" data-act="close-overlay">Got it</button>`);
  }
  function approveLowRisk() {
    const low = pending().filter((a) => a.risk === 'low');
    if (!low.length) return toast('No low-risk approvals waiting');
    low.forEach((a) => { a.status = 'approved'; }); save(); render();
    toast(`Approved ${low.length} low-risk item${low.length > 1 ? 's' : ''}`, () => { low.forEach((a) => { a.status = 'pending'; }); save(); render(); });
  }

  /* mobile sheet */
  function openSheet() {
    const sh = $('#moreSheet');
    sh.innerHTML = '<div class="grab"></div>' + ['workflows', 'map', 'settings'].map((k) => { const n = NAV.find((x) => x.k === k); return `<a href="#/${k}">${I[n.i]}${n.l}</a>`; }).join('') +
      `<button data-act="palette">${I.search}Search or command</button><button data-act="theme">${document.documentElement.dataset.theme === 'dark' ? I.sun + 'Light theme' : I.moon + 'Dark theme'}</button>`;
    sh.classList.add('on'); $('#scrim').classList.add('on');
  }
  function closeSheet() { const sh = $('#moreSheet'); if (sh.classList.contains('on')) { sh.classList.remove('on'); if (!$('#drawer').classList.contains('on')) $('#scrim').classList.remove('on'); return true; } return false; }
  $('#scrim').addEventListener('click', closeSheet);

  /* ---------- toasts ---------- */
  function toast(msg, undo, label, action) {
    const t = document.createElement('div'); t.className = 'toast';
    t.innerHTML = `<span>${esc(msg)}</span>${undo ? '<button data-u>Undo</button>' : ''}${action ? `<button data-a>${esc(label)}</button>` : ''}`;
    $('#toasts').appendChild(t);
    const kill = () => { t.classList.add('out'); setTimeout(() => t.remove(), 250); };
    if (undo) $('[data-u]', t).onclick = () => { undo(); kill(); };
    if (action) $('[data-a]', t).onclick = () => { action(); kill(); };
    setTimeout(kill, undo || action ? 5500 : 3000);
    while ($('#toasts').children.length > 3) $('#toasts').firstChild.remove();
  }

  /* ---------- global click delegation ---------- */
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-act],[data-agent],[data-run],[data-approve],[data-reject],[data-sel],[data-open-approval],[data-wf-toggle],[data-wf-run],[data-retry],[data-undo-decision]');
    if (!t) return;
    const d = t.dataset;
    if (d.approve) { e.stopPropagation(); return decide(d.approve, 'approved'); }
    if (d.reject) return decide(d.reject, 'rejected');
    if (d.undoDecision) { const a = S.approvals.find((x) => x.id === d.undoDecision); a.status = 'pending'; save(); return render(); }
    if (d.sel) return selectApproval(d.sel);
    if (d.openApproval) return go('inbox', d.openApproval);
    if (d.wfToggle) { const w = S.workflows.find((x) => x.id === d.wfToggle); w.enabled = !w.enabled; save(); render(); return toast(`${w.name} ${w.enabled ? 'enabled' : 'disabled'}`, () => { w.enabled = !w.enabled; save(); render(); }); }
    if (d.wfRun) return runWorkflow(d.wfRun);
    if (d.retry) { const r = S.runs.find((x) => x.id === d.retry); const nr = makeRun(agentById(r.agent), now(), 'ok'); nr.title = r.title; S.runs.unshift(nr); save(); closeDrawer(); render(); return toast('Run retried successfully', null, 'View', () => openRun(nr.id)); }
    if (d.agent) { e.preventDefault(); closeOverlay(); if (route.name === 'agents') return openAgent(d.agent); return openAgent(d.agent); }
    if (d.run) return openRun(d.run);
    switch (d.act) {
      case 'palette': closeSheet(); return openPalette();
      case 'theme': closeSheet(); return toggleTheme();
      case 'new-agent': return newAgentModal(d.fn);
      case 'new-workflow': return newWorkflowModal();
      case 'close-drawer': return closeDrawer();
      case 'close-overlay': return closeOverlay();
      case 'inbox-back': $('#inbox').classList.remove('showing'); history.replaceState(null, '', '#/inbox'); route.arg = null; return;
      case 'reset': return confirmModal('Reset demo data?', 'All agents, approvals, workflows and runs go back to their original state. Your theme is kept.', 'Reset', () => { const theme = S.prefs.theme; S = seed(); S.prefs.theme = theme; save(); closeDrawer(true); render(); toast('Demo data restored'); });
      case 'toggle-agent': { const a = agentById(drawerId); a.status = a.status === 'paused' ? 'running' : 'paused'; save(); const id = drawerId; refreshBehind(); openAgent(id); return toast(`${a.name} ${a.status === 'paused' ? 'paused' : 'resumed'}`, () => { a.status = a.status === 'paused' ? 'running' : 'paused'; save(); refreshBehind(); openAgent(id); }); }
      case 'run-agent': { const a = agentById(drawerId); const r = makeRun(a, now(), 'ok'); S.runs.unshift(r); a.runs7++; save(); const id = drawerId; refreshBehind(); openAgent(id, 'runs'); return toast(`${a.name} ran: ${r.title}`); }
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.matches('[data-agent][tabindex],tr[data-run]')) { e.target.click(); }
  });
  $('#searchBtn').onclick = openPalette; $('#searchBtn2').onclick = openPalette;
  $('#themeBtn').onclick = toggleTheme; $('#helpBtn').onclick = helpModal;
  $('#wsBtn').onclick = () => go('settings');
  $('#kbdHint').textContent = isMac ? '⌘K' : 'Ctrl K';

  /* ---------- keyboard ---------- */
  let gPending = 0;
  document.addEventListener('keydown', (e) => {
    const typing = e.target.matches('input,textarea,select,[contenteditable]');
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); if (!closeOverlay()) openPalette(); return; }
    if (e.key === 'Escape') { if (closeOverlay() || closeSheet()) return; if ($('#drawer').classList.contains('on')) return closeDrawer(); if (typing) e.target.blur(); return; }
    if (typing || e.metaKey || e.ctrlKey || e.altKey || ov.classList.contains('on')) return;
    const k = e.key.toLowerCase();
    if (gPending && now() - gPending < 1200) { gPending = 0; const n = NAV.find((x) => x.key === k); if (n) { e.preventDefault(); go(n.k); } return; }
    if (k === 'g') { gPending = now(); return; }
    if (k === '/') { e.preventDefault(); return openPalette(); }
    if (e.key === '?') return helpModal();
    if (k === 't') return toggleTheme();
    if (route.name === 'inbox' && !$('#drawer').classList.contains('on')) {
      if (k === 'j' || e.key === 'ArrowDown') { e.preventDefault(); inboxMove(1); }
      else if (k === 'k' || e.key === 'ArrowUp') { e.preventDefault(); inboxMove(-1); }
      else if (k === 'a' || k === 'r') { const on = $('.qi.on'); if (on) decide(on.dataset.sel, k === 'a' ? 'approved' : 'rejected'); }
    }
  });

  /* ---------- live simulation ---------- */
  let tick = 0;
  setInterval(() => {
    if (document.hidden) return;
    tick++;
    const live = S.agents.filter((a) => a.status !== 'paused');
    if (!live.length) return;
    const a = live[Math.floor(Math.random() * live.length)];
    const r = makeRun(a, now()); S.runs.unshift(r); a.runs7++;
    if (tick % 9 === 0 && pending().length < 9) {
      const tpl = [['Pay supplier invoice — €2,940', 'Invoice matches PO and receipt. Payment run is tomorrow.', 'low', 'a1'], ['Reply to escalated ticket from Maison Vey', 'Customer threatens to cancel. Draft offers a call with their account manager.', 'medium', 'a7'], ['Reassign lead from Corvel Group', 'Lead is in a territory without an owner this week.', 'low', 'a3']][tick % 3];
      const ap = { id: uid('p'), agent: tpl[3], title: tpl[0], summary: tpl[1], risk: tpl[2], created: now(), status: 'pending', facts: [['Agent confidence', '92%'], ['Similar decisions', '14'], ['Time to decide', '< 1 min']], reason: tpl[1] + ' The agent stops here because this action is above its approval threshold.' };
      S.approvals.unshift(ap); save(); renderNav();
      if (S.prefs.notify.approvals) toast('New approval: ' + ap.title, null, 'Review', () => go('inbox', ap.id));
      if (route.name === 'overview' || (route.name === 'inbox' && !route.arg)) render();
      return;
    }
    save();
    if (r.status === 'bad' && S.prefs.notify.failures) toast(`${a.name}: run failed`, null, 'Open', () => openRun(r.id));
    if (route.name === 'overview') {
      const f = $('#feed');
      if (f) { f.insertAdjacentHTML('afterbegin', feedItem(r)); while (f.children.length > 7) f.lastElementChild.remove(); }
    }
  }, 5000);

  /* ---------- boot ---------- */
  applyTheme(); parse(); render();
})();
