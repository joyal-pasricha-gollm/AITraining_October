import React, { useEffect, useRef, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import api, { apiErrorMessage, newIdempotencyKey } from "./api";

const EMPTY_REPORT = {
  report_type: "LOST",
  category_id: "",
  item_name: "",
  colour: "",
  brand: "",
  event_date: new Date().toISOString().slice(0, 10),
  approximate_time: "",
  area: "",
  location_details: "",
  description: "",
  distinguishing_features: "",
  verification_question: "",
  verification_answer: "",
  storage_instructions: "",
  image_url: "",
};

function ErrorMessage({ children }) {
  return children ? <p className="notice error" role="alert">{children}</p> : null;
}

function SuccessMessage({ children }) {
  return children ? <p className="notice success" role="status">{children}</p> : null;
}

function Loading({ label = "Loading..." }) {
  return <p className="muted" role="status">{label}</p>;
}

function Field({ label, required = false, ...props }) {
  return (
    <label className="field">
      <span>{label}{required && <span className="required-mark" aria-hidden="true"> *</span>}</span>
      <input {...props} required={required} />
    </label>
  );
}

function ProtectedRoute({ user, children, admin = false }) {
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "ADMIN") return <Navigate to="/activity" replace />;
  return children;
}

function Layout({ user, onLogout }) {
  return (
    <>
      <header className="site-header">
        <Link to="/" className="brand">ReclaimAI</Link>
        <nav aria-label="Main navigation">
          <Link to="/reports">Browse reports</Link>
          {user && (
            <>
              <Link to="/report/lost">Report lost</Link>
              <Link to="/report/found">Report found</Link>
              <Link to="/activity">My activity</Link>
              {user.role === "ADMIN" && <Link to="/admin">Admin</Link>}
              <button className="nav-button" onClick={onLogout}>Sign out</button>
            </>
          )}
          {!user && (
            <>
              <Link to="/login">Sign in</Link>
              <Link to="/register" className="nav-cta">Create account</Link>
            </>
          )}
        </nav>
      </header>
      <main className="page-shell">
        <Routes>
          <Route path="/" element={<Home user={user} />} />
          <Route path="/login" element={user ? <Navigate to="/activity" replace /> : <Login />} />
          <Route path="/register" element={user ? <Navigate to="/activity" replace /> : <Register />} />
          <Route path="/reports" element={<BrowseReports />} />
          <Route path="/reports/:reportId" element={<ReportDetails user={user} />} />
          <Route
            path="/reports/:reportId/edit"
            element={<ProtectedRoute user={user}><ReportForm /></ProtectedRoute>}
          />
          <Route
            path="/report/:type"
            element={<ProtectedRoute user={user}><ReportForm /></ProtectedRoute>}
          />
          <Route
            path="/claims/new"
            element={<ProtectedRoute user={user}><ClaimForm /></ProtectedRoute>}
          />
          <Route
            path="/activity"
            element={<ProtectedRoute user={user}><ActivityPage user={user} /></ProtectedRoute>}
          />
          <Route
            path="/admin"
            element={<ProtectedRoute user={user} admin><AdminPage /></ProtectedRoute>}
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="site-footer">ReclaimAI helps people find and return lost belongings.</footer>
    </>
  );
}

function Home({ user }) {
  return (
    <section className="hero">
      <span className="eyebrow">SMART LOST-AND-FOUND</span>
      <h1>Help the right report find its match.</h1>
      <p>Report missing or found items, explore explainable matches, and track a secure return.</p>
      <div className="hero-actions">
        {user ? (
          <>
            <Link className="button primary" to="/report/lost">Report a lost item</Link>
            <Link className="button secondary" to="/report/found">Report a found item</Link>
          </>
        ) : (
          <>
            <Link className="button primary" to="/register">Get started</Link>
            <Link className="button secondary" to="/reports">Browse active reports</Link>
          </>
        )}
      </div>
      <div className="feature-grid">
        <article><span>01</span><h2>Share a report</h2><p>Describe the item and where it was lost or found.</p></article>
        <article><span>02</span><h2>Review a match</h2><p>See ranked suggestions with clear reasons behind every score.</p></article>
        <article><span>03</span><h2>Confirm a return</h2><p>Submit a private claim and follow its review in your activity.</p></article>
      </div>
    </section>
  );
}

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [values, setValues] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const { data } = await api.post("/auth/login", values);
      localStorage.setItem("token", data.access_token);
      window.dispatchEvent(new CustomEvent("reclaimai:authenticated", { detail: data.user }));
      navigate("/activity");
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card auth-card" onSubmit={submit}>
      <span className="eyebrow">WELCOME BACK</span>
      <h1>Sign in</h1>
      <SuccessMessage>{location.state?.registered ? "Your account is ready. Sign in to continue." : ""}</SuccessMessage>
      <p className="muted">Use your ReclaimAI account to manage reports and claims.</p>
      <ErrorMessage>{error}</ErrorMessage>
      <Field label="Email" type="email" autoComplete="email" value={values.email} required
        onChange={(event) => setValues({ ...values, email: event.target.value })} />
      <Field label="Password" type="password" autoComplete="current-password" value={values.password} required
        onChange={(event) => setValues({ ...values, password: event.target.value })} />
      <button className="button primary full-width" disabled={pending}>{pending ? "Signing in..." : "Sign in"}</button>
      <p className="form-footnote">New to ReclaimAI? <Link to="/register">Create an account</Link></p>
    </form>
  );
}

function Register() {
  const navigate = useNavigate();
  const [values, setValues] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      await api.post("/auth/register", values);
      navigate("/login", { state: { registered: true } });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card auth-card" onSubmit={submit}>
      <span className="eyebrow">JOIN RECLAIMAI</span>
      <h1>Create an account</h1>
      <ErrorMessage>{error}</ErrorMessage>
      <Field label="Full name" autoComplete="name" minLength={2} maxLength={100} value={values.full_name} required
        onChange={(event) => setValues({ ...values, full_name: event.target.value })} />
      <Field label="Email" type="email" autoComplete="email" maxLength={254} value={values.email} required
        onChange={(event) => setValues({ ...values, email: event.target.value })} />
      <Field label="Password" type="password" autoComplete="new-password" minLength={8} maxLength={128}
        value={values.password} required aria-describedby="password-hint"
        onChange={(event) => setValues({ ...values, password: event.target.value })} />
      <p id="password-hint" className="hint">Use at least 8 characters with uppercase, lowercase, and a number.</p>
      <button className="button primary full-width" disabled={pending}>{pending ? "Creating account..." : "Create account"}</button>
      <p className="form-footnote">Already registered? <Link to="/login">Sign in</Link></p>
    </form>
  );
}

function BrowseReports() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.toString();
  const [filters, setFilters] = useState({});
  const [categories, setCategories] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams(query);
    const initial = {};
    for (const key of ["q", "report_type", "category_id", "colour", "brand", "area", "from_date", "to_date"]) {
      initial[key] = params.get(key) || "";
    }
    setFilters(initial);
  }, [query]);

  useEffect(() => {
    api.get("/categories")
      .then(({ data }) => setCategories(data.items))
      .catch((requestError) => setError(apiErrorMessage(requestError)));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api.get(`/reports${query ? `?${query}` : ""}`)
      .then(({ data }) => { if (active) setResult(data); })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query]);

  function applyFilters(event) {
    event.preventDefault();
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
    params.set("page", "1");
    setSearchParams(params);
  }

  function changePage(page) {
    const params = new URLSearchParams(query);
    params.set("page", String(page));
    setSearchParams(params);
  }

  function clearFilters() {
    setSearchParams({});
  }

  return (
    <section>
      <div className="section-heading">
        <div><span className="eyebrow">COMMUNITY REPORTS</span><h1>Browse items</h1></div>
        <p className="muted">Public listings never include contact or private verification details.</p>
      </div>
      <form className="filter-panel" onSubmit={applyFilters}>
        <Field label="Search" placeholder="Item, brand, area, description" value={filters.q || ""}
          onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
        <label className="field"><span>Report type</span>
          <select value={filters.report_type || ""} onChange={(event) => setFilters({ ...filters, report_type: event.target.value })}>
            <option value="">Lost and found</option><option value="LOST">Lost</option><option value="FOUND">Found</option>
          </select>
        </label>
        <label className="field"><span>Category</span>
          <select value={filters.category_id || ""} onChange={(event) => setFilters({ ...filters, category_id: event.target.value })}>
            <option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
        </label>
        <Field label="Colour" value={filters.colour || ""} onChange={(event) => setFilters({ ...filters, colour: event.target.value })} />
        <Field label="Brand" value={filters.brand || ""} onChange={(event) => setFilters({ ...filters, brand: event.target.value })} />
        <Field label="Area" value={filters.area || ""} onChange={(event) => setFilters({ ...filters, area: event.target.value })} />
        <Field label="From date" type="date" value={filters.from_date || ""} onChange={(event) => setFilters({ ...filters, from_date: event.target.value })} />
        <Field label="To date" type="date" value={filters.to_date || ""} onChange={(event) => setFilters({ ...filters, to_date: event.target.value })} />
        <div className="filter-actions"><button className="button primary">Apply filters</button><button type="button" className="button text-button" onClick={clearFilters}>Clear filters</button></div>
      </form>
      <ErrorMessage>{error}</ErrorMessage>
      {loading ? <Loading label="Loading reports..." /> : (
        <>
          <p className="result-count">{result?.total || 0} active report{result?.total === 1 ? "" : "s"}</p>
          {result?.items?.length ? (
            <div className="report-grid">{result.items.map((report) => <ReportCard key={report.id} report={report} />)}</div>
          ) : <div className="empty-state"><h2>No reports found</h2><p>Try changing or clearing the filters.</p></div>}
          {result?.total > result?.page_size && (
            <div className="pagination">
              <button className="button secondary" disabled={result.page <= 1} onClick={() => changePage(result.page - 1)}>Previous</button>
              <span>Page {result.page} of {Math.ceil(result.total / result.page_size)}</span>
              <button className="button secondary" disabled={result.page * result.page_size >= result.total} onClick={() => changePage(result.page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ReportCard({ report }) {
  return (
    <article className="report-card">
      <div className="card-topline"><span className={`type-badge ${report.report_type.toLowerCase()}`}>{report.report_type}</span><span className="muted">{report.reference}</span></div>
      <h2><Link to={`/reports/${report.id}`}>{report.item_name}</Link></h2>
      <p>{report.colour}{report.brand ? ` · ${report.brand}` : ""}</p>
      <p className="muted">{report.area} · {report.event_date}</p>
      <p className="report-description">{report.description}</p>
      <Link className="inline-link" to={`/reports/${report.id}`}>View report <span aria-hidden="true">→</span></Link>
    </article>
  );
}

function ReportForm() {
  const { type, reportId } = useParams();
  const navigate = useNavigate();
  const editing = Boolean(reportId);
  const [values, setValues] = useState({ ...EMPTY_REPORT, report_type: type?.toLowerCase() === "found" ? "FOUND" : "LOST" });
  const [categories, setCategories] = useState([]);
  const [report, setReport] = useState(null);
  const [review, setReview] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const idempotency = useRef(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get("/categories"),
      editing ? api.get(`/reports/${reportId}`) : Promise.resolve(null),
    ]).then(([categoryResponse, reportResponse]) => {
      if (!active) return;
      setCategories(categoryResponse.data.items);
      if (reportResponse) {
        const saved = reportResponse.data;
        setReport(saved);
        setValues({
          ...EMPTY_REPORT,
          ...saved,
          approximate_time: saved.approximate_time || "",
          image_url: saved.image_url || "",
          verification_answer: "",
        });
      }
    }).catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); });
    return () => { active = false; };
  }, [editing, reportId]);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    if (!review) {
      setError("");
      setReview(true);
      return;
    }
    setError("");
    setPending(true);
    const body = { ...values };
    for (const [key, value] of Object.entries(body)) {
      if (value === "" || value == null) delete body[key];
    }
    if (editing) delete body.report_type;
    if (editing && !body.verification_answer) delete body.verification_answer;
    try {
      let saved;
      if (editing) {
        const response = await api.patch(`/reports/${reportId}`, body, {
          headers: { "If-Match": String(report.version) },
        });
        saved = response.data;
      } else {
        const signature = JSON.stringify(body);
        if (idempotency.current?.signature !== signature) {
          idempotency.current = { signature, key: newIdempotencyKey() };
        }
        const response = await api.post("/reports", body, {
          headers: { "Idempotency-Key": idempotency.current.key },
        });
        saved = response.data;
        idempotency.current = null;
      }
      navigate(`/reports/${saved.id}`, { state: { saved: true } });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
      setReview(false);
    } finally {
      setPending(false);
    }
  }

  if (editing && !report && !error) return <Loading label="Loading your report..." />;
  if (!categories.length && !error) return <Loading label="Loading report categories..." />;

  return (
    <section className="form-page">
      <div className="section-heading"><div><span className="eyebrow">{editing ? "UPDATE YOUR REPORT" : "NEW COMMUNITY REPORT"}</span><h1>{editing ? "Edit report" : `Report a ${values.report_type.toLowerCase()} item`}</h1></div></div>
      <form className="card wide-card" onSubmit={submit}>
        <ErrorMessage>{error}</ErrorMessage>
        {!review ? (
          <>
            <div className="form-section"><h2>Item details</h2>
              <label className="field"><span>Category <span className="required-mark">*</span></span>
                <select required value={values.category_id} onChange={(event) => update("category_id", event.target.value)}>
                  <option value="">Choose a category</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
                </select>
              </label>
              <Field label="Item name" minLength={2} maxLength={120} required value={values.item_name} onChange={(event) => update("item_name", event.target.value)} />
              <div className="form-row">
                <Field label="Colour" minLength={2} maxLength={40} required value={values.colour} onChange={(event) => update("colour", event.target.value)} />
                <Field label="Brand (optional)" maxLength={80} value={values.brand || ""} onChange={(event) => update("brand", event.target.value)} />
              </div>
              <div className="form-row">
                <Field label="Date lost / found" type="date" required value={values.event_date} onChange={(event) => update("event_date", event.target.value)} />
                <Field label="Approximate time" type="time" value={values.approximate_time || ""} onChange={(event) => update("approximate_time", event.target.value)} />
              </div>
            </div>
            <div className="form-section"><h2>Where and what happened</h2>
              <Field label="Area (shown publicly)" minLength={2} maxLength={120} required value={values.area} onChange={(event) => update("area", event.target.value)} />
              <Field label="Exact location details (private)" maxLength={300} value={values.location_details || ""} onChange={(event) => update("location_details", event.target.value)} />
              <label className="field"><span>Public description <span className="required-mark">*</span></span>
                <textarea minLength={10} maxLength={1500} required rows={4} value={values.description} onChange={(event) => update("description", event.target.value)} />
              </label>
              <label className="field"><span>Distinguishing features (public)</span>
                <textarea maxLength={800} rows={3} value={values.distinguishing_features || ""} onChange={(event) => update("distinguishing_features", event.target.value)} />
              </label>
              <Field label="Image URL (optional)" type="url" maxLength={500} value={values.image_url || ""} onChange={(event) => update("image_url", event.target.value)} />
            </div>
            {values.report_type === "FOUND" && (
              <div className="form-section"><h2>Private ownership check</h2>
                <p className="privacy-note">This question and its answer are never shown on public reports. The answer is used only to help verify a claim.</p>
                <Field label="Verification question" minLength={10} maxLength={300} required value={values.verification_question || ""} onChange={(event) => update("verification_question", event.target.value)} />
                <Field label={editing ? "New verification answer (leave blank to keep current)" : "Verification answer"} minLength={2} maxLength={300} required={!editing} type="password" value={values.verification_answer || ""} onChange={(event) => update("verification_answer", event.target.value)} />
                <Field label="Storage instructions (private)" maxLength={300} value={values.storage_instructions || ""} onChange={(event) => update("storage_instructions", event.target.value)} />
              </div>
            )}
            <p className="privacy-note">Your account is the reporter identity. Do not include phone numbers or private details in the public description.</p>
            <button className="button primary">{editing ? "Review changes" : "Review report"}</button>
          </>
        ) : (
          <>
            <div className="review-panel"><h2>Review before submitting</h2><p>Confirm that the public details are accurate. Private fields stay private.</p>
              <dl className="review-list">
                <dt>Report type</dt><dd>{values.report_type}</dd>
                <dt>Item</dt><dd>{values.item_name}</dd>
                <dt>Category</dt><dd>{categories.find((category) => category.id === values.category_id)?.name || "Selected category"}</dd>
                <dt>Colour and brand</dt><dd>{values.colour}{values.brand ? ` · ${values.brand}` : ""}</dd>
                <dt>Date and area</dt><dd>{values.event_date} · {values.area}</dd>
                <dt>Public description</dt><dd>{values.description}</dd>
                {values.report_type === "FOUND" && <><dt>Verification question</dt><dd>{values.verification_question}</dd><dt>Verification answer</dt><dd>{editing && !values.verification_answer ? "Current answer retained" : "Provided privately"}</dd></>}
              </dl>
              <div className="privacy-note">We’ll show a reference number and match status after the report is saved.</div>
            </div>
            <div className="button-row">
              <button type="button" className="button secondary" onClick={() => setReview(false)} disabled={pending}>Back to edit</button>
              <button className="button primary" disabled={pending}>{pending ? "Saving..." : editing ? "Save changes" : "Submit report"}</button>
            </div>
          </>
        )}
      </form>
    </section>
  );
}

function ReportDetails({ user }) {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [showMatches, setShowMatches] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [pending, setPending] = useState(false);

  async function loadReport() {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get(`/reports/${reportId}`);
      setReport(data);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadReport(); }, [reportId]);

  async function withdraw() {
    setError("");
    setPending(true);
    try {
      const { data } = await api.post(`/reports/${reportId}/withdraw`, { reason: withdrawReason }, {
        headers: { "If-Match": String(report.version) },
      });
      setReport(data);
      setWithdrawReason("");
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }

  if (loading) return <Loading label="Loading report..." />;
  if (!report) return <div className="empty-state"><ErrorMessage>{error}</ErrorMessage><Link className="button secondary" to="/reports">Back to reports</Link></div>;

  const isOwner = user && report.reporter_id === user.id;
  const isAdmin = user?.role === "ADMIN";
  const canManage = Boolean(isOwner || isAdmin);
  const terminal = ["CLOSED", "EXPIRED", "RECOVERED", "RETURNED"].includes(report.status);

  return (
    <article className="detail-page">
      <Link to="/reports" className="back-link">← Back to reports</Link>
      <ErrorMessage>{error}</ErrorMessage>
      <div className="detail-heading">
        <span className={`type-badge ${report.report_type.toLowerCase()}`}>{report.report_type}</span>
        <span className="reference">{report.reference}</span>
        <span className={`status-badge status-${report.status.toLowerCase()}`}>{report.status.replaceAll("_", " ")}</span>
      </div>
      <h1>{report.item_name}</h1>
      <p className="detail-subtitle">{report.colour}{report.brand ? ` · ${report.brand}` : ""} · {report.event_date} · {report.area}</p>
      {report.image_url && <img className="report-image" src={report.image_url} alt={`Reported ${report.item_name}`} />}
      <section className="detail-panel"><h2>About this item</h2><p className="preserve-text">{report.description}</p>
        {report.distinguishing_features && <p><strong>Distinguishing features:</strong> {report.distinguishing_features}</p>}
      </section>
      {canManage && (
        <section className="detail-panel private-panel">
          <h2>Private report details</h2>
          {report.location_details && <p><strong>Exact location:</strong> {report.location_details}</p>}
          {report.storage_instructions && <p><strong>Storage:</strong> {report.storage_instructions}</p>}
          {report.verification_question && <p><strong>Claim verification question:</strong> {report.verification_question}</p>}
          <p><strong>Version:</strong> {report.version} · <strong>Matching:</strong> {report.matching_status}</p>
        </section>
      )}
      {canManage && (
        <section className="owner-actions">
          <h2>Manage report</h2>
          {!terminal && <div className="button-row">
            <Link className="button secondary" to={`/reports/${report.id}/edit`}>Edit report</Link>
            <button className="button secondary" onClick={() => setShowMatches((visible) => !visible)}>{showMatches ? "Hide matches" : "View matches"}</button>
          </div>}
          {showMatches && <MatchesList report={report} />}
          {!terminal && <div className="withdraw-box">
            <label className="field"><span>Reason for withdrawing</span><input value={withdrawReason} minLength={3} maxLength={500} onChange={(event) => setWithdrawReason(event.target.value)} /></label>
            <button className="button danger" disabled={pending || withdrawReason.trim().length < 3} onClick={withdraw}>{pending ? "Withdrawing..." : "Withdraw report"}</button>
          </div>}
        </section>
      )}
      {user && !canManage && report.report_type === "FOUND" && !terminal && (
        <section className="detail-panel"><h2>Think this item is yours?</h2><p>Open your lost report and submit a claim from a qualifying match. The finder’s private answer is never displayed.</p><Link className="button primary" to="/activity">Go to my activity</Link></section>
      )}
    </article>
  );
}

function MatchesList({ report }) {
  const [matches, setMatches] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const { data } = await api.get(`/reports/${report.id}/matches`);
        const expanded = await Promise.all(data.map(async (match) => {
          const otherId = report.report_type === "LOST" ? match.found_report_id : match.lost_report_id;
          const response = await api.get(`/reports/${otherId}`);
          return { ...match, other: response.data };
        }));
        if (active) setMatches(expanded);
      } catch (requestError) {
        if (active) setError(apiErrorMessage(requestError));
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, [report.id, report.report_type]);

  if (loading) return <Loading label="Finding potential matches..." />;
  return (
    <div className="match-list">
      <h3>Potential matches</h3>
      <ErrorMessage>{error}</ErrorMessage>
      {!matches.length && !error && <p className="muted">No visible matches yet. New reports may create a match later.</p>}
      {matches.map((match) => (
        <article className="match-card" key={match.id}>
          <div className="match-score"><strong>{match.total_score}%</strong><span>{match.match_level}</span></div>
          <div className="match-content">
            <h4><Link to={`/reports/${match.other.id}`}>{match.other.item_name}</Link></h4>
            <p className="muted">{match.other.colour} · {match.other.area} · {match.other.event_date}</p>
            <ul>{(match.explanation?.reasons || []).map((reason) => <li key={reason}>{reason}</li>)}</ul>
            <Link className="inline-link" to={`/reports/${match.other.id}`}>Review public report</Link>
            {report.report_type === "LOST" && match.total_score >= 60 && (
              <Link className="button small primary" to={`/claims/new?lost_id=${report.id}&found_id=${match.other.id}`}>Submit a claim</Link>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

function ClaimForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedMatch = useRef({
    lost: searchParams.get("lost_id") || "",
    found: searchParams.get("found_id") || "",
  });
  const [reports, setReports] = useState([]);
  const [selectedLost, setSelectedLost] = useState(searchParams.get("lost_id") || "");
  const [foundReports, setFoundReports] = useState([]);
  const [selectedFound, setSelectedFound] = useState(searchParams.get("found_id") || "");
  const [question, setQuestion] = useState("");
  const [explanation, setExplanation] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [review, setReview] = useState(false);
  const idempotency = useRef(null);

  useEffect(() => {
    let active = true;
    api.get("/reports/mine?page_size=100")
      .then(({ data }) => {
        if (active) setReports(data.items.filter((report) => report.report_type === "LOST" && ["ACTIVE", "POTENTIAL_MATCH_FOUND", "CLAIM_UNDER_REVIEW"].includes(report.status)));
      })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setFoundReports([]);
    setSelectedFound(requestedMatch.current.lost === selectedLost ? requestedMatch.current.found : "");
    setQuestion("");
    if (!selectedLost) return () => { active = false; };
    api.get(`/reports/${selectedLost}/matches`)
      .then(async ({ data }) => {
        const candidates = data.filter((match) => match.total_score >= 60);
        const details = await Promise.all(candidates.map(async (match) => {
          const { data: report } = await api.get(`/reports/${match.found_report_id}`);
          return { ...report, score: match.total_score };
        }));
        if (active) setFoundReports(details);
      })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); });
    return () => { active = false; };
  }, [selectedLost]);

  useEffect(() => {
    let active = true;
    setError("");
    setQuestion("");
    if (!selectedLost || !selectedFound) return () => { active = false; };
    api.get(`/reports/${selectedFound}/claim-question`, { params: { lost_report_id: selectedLost } })
      .then(({ data }) => { if (active) setQuestion(data.question); })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); });
    return () => { active = false; };
  }, [selectedLost, selectedFound]);

  async function submit(event) {
    event.preventDefault();
    if (!review) {
      setError("");
      setReview(true);
      return;
    }
    setError("");
    setPending(true);
    const body = {
      lost_report_id: selectedLost,
      found_report_id: selectedFound,
      ownership_explanation: explanation,
      verification_answer: answer,
    };
    const signature = JSON.stringify(body);
    if (idempotency.current?.signature !== signature) {
      idempotency.current = { signature, key: newIdempotencyKey() };
    }
    try {
      const { data } = await api.post("/claims", body, {
        headers: { "Idempotency-Key": idempotency.current.key },
      });
      navigate("/activity", { state: { createdClaim: data.id } });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }

  if (loading) return <Loading label="Loading your lost reports..." />;
  return (
    <section className="form-page">
      <Link to="/activity" className="back-link">← Back to my activity</Link>
      <div className="section-heading"><div><span className="eyebrow">PRIVATE CLAIM</span><h1>Claim a potential match</h1></div></div>
      <form className="card wide-card" onSubmit={submit}>
        <ErrorMessage>{error}</ErrorMessage>
        {!reports.length ? <div className="empty-state"><p>Create a lost-item report before submitting a claim.</p><Link className="button primary" to="/report/lost">Create lost report</Link></div> : !review ? (
          <>
            <label className="field"><span>Your lost report</span><select required value={selectedLost} onChange={(event) => setSelectedLost(event.target.value)}>
              <option value="">Choose one of your active lost reports</option>
              {reports.map((report) => <option key={report.id} value={report.id}>{report.reference} · {report.item_name}</option>)}
            </select></label>
            <label className="field"><span>Matching found report</span><select required value={selectedFound} onChange={(event) => setSelectedFound(event.target.value)}>
              <option value="">Choose a qualifying match</option>{foundReports.map((report) => <option key={report.id} value={report.id}>{report.item_name} · {report.area} · {report.score}%</option>)}
            </select></label>
            {selectedLost && !foundReports.length && <p className="muted">No qualifying (60%+) found-item matches are available for this report.</p>}
            {question && <div className="question-card"><span className="eyebrow">PRIVATE VERIFICATION QUESTION</span><p>{question}</p></div>}
            <label className="field"><span>Why do you believe this item is yours?</span><textarea required minLength={20} maxLength={1500} rows={5} value={explanation} onChange={(event) => setExplanation(event.target.value)} /></label>
            <Field label="Answer to the finder’s question" required minLength={2} maxLength={300} value={answer} onChange={(event) => setAnswer(event.target.value)} />
            <p className="privacy-note">Your answer is checked privately and is never shown to the public or included in match scoring. Arrange the handover outside the app.</p>
            <button className="button primary" disabled={!question}>Review claim</button>
          </>
        ) : (
          <>
            <div className="review-panel"><h2>Review your claim</h2><p>Confirm the match and ownership details before submitting. Your verification answer is checked privately.</p>
              <dl className="review-list">
                <dt>Lost report</dt><dd>{reports.find((report) => report.id === selectedLost)?.item_name}</dd>
                <dt>Found report</dt><dd>{foundReports.find((report) => report.id === selectedFound)?.item_name}</dd>
                <dt>Ownership explanation</dt><dd>{explanation}</dd>
                <dt>Verification answer</dt><dd>Provided privately</dd>
              </dl>
            </div>
            <div className="button-row">
              <button type="button" className="button secondary" onClick={() => setReview(false)} disabled={pending}>Back to edit</button>
              <button className="button primary" disabled={pending || !question}>{pending ? "Submitting claim..." : "Submit claim"}</button>
            </div>
          </>
        )}
      </form>
    </section>
  );
}

function ActivityPage({ user }) {
  const [dashboard, setDashboard] = useState(null);
  const [reports, setReports] = useState([]);
  const [claims, setClaims] = useState([]);
  const [tab, setTab] = useState("reports");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function reload() {
    setError("");
    try {
      const [dashboardResponse, reportsResponse, claimsResponse] = await Promise.all([
        api.get("/dashboard/me"),
        api.get("/reports/mine?page_size=100"),
        api.get("/claims?page_size=100"),
      ]);
      setDashboard(dashboardResponse.data);
      setReports(reportsResponse.data.items);
      setClaims(claimsResponse.data.items);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, []);

  async function updateClaim(claim, status, reviewComment) {
    setError("");
    try {
      await api.patch(`/claims/${claim.id}/status`, { status, review_comment: reviewComment || null }, {
        headers: { "If-Match": String(claim.version) },
      });
      await reload();
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    }
  }

  async function completeClaim(claim) {
    setError("");
    try {
      await api.post(`/claims/${claim.id}/complete`);
      await reload();
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    }
  }

  return (
    <section>
      <div className="section-heading"><div><span className="eyebrow">YOUR ACCOUNT</span><h1>My activity</h1><p className="muted">Signed in as {user.full_name}</p></div>
        <div className="button-row"><Link className="button primary" to="/report/lost">New lost report</Link><Link className="button secondary" to="/report/found">New found report</Link></div>
      </div>
      <ErrorMessage>{error}</ErrorMessage>
      {loading ? <Loading label="Loading your activity..." /> : (
        <>
          <div className="stats-grid">{Object.entries(dashboard || {}).map(([key, value]) => <div className="stat-card" key={key}><strong>{value}</strong><span>{key.replaceAll("_", " ")}</span></div>)}</div>
          <div className="tabs" role="tablist" aria-label="My activity">
            <button role="tab" aria-selected={tab === "reports"} className={tab === "reports" ? "active" : ""} onClick={() => setTab("reports")}>My reports ({reports.length})</button>
            <button role="tab" aria-selected={tab === "claims"} className={tab === "claims" ? "active" : ""} onClick={() => setTab("claims")}>My claims ({claims.length})</button>
            <button role="tab" aria-selected={tab === "matches"} className={tab === "matches" ? "active" : ""} onClick={() => setTab("matches")}>Matches</button>
          </div>
          {tab === "reports" && <div className="stack-list">{reports.length ? reports.map((report) => <OwnedReportCard key={report.id} report={report} />) : <EmptyActivity title="No reports yet" to="/report/lost" action="Report a lost item" />}</div>}
          {tab === "matches" && <div className="stack-list">{reports.filter((report) => !["CLOSED", "EXPIRED", "RECOVERED", "RETURNED"].includes(report.status)).map((report) => <section className="activity-report" key={report.id}><h2>{report.item_name} <StatusBadge status={report.status} /></h2><MatchesList report={report} /></section>)}{!reports.length && <EmptyActivity title="No active reports to match" to="/report/lost" action="Create a lost report" />}</div>}
          {tab === "claims" && <div className="stack-list">{claims.length ? claims.map((claim) => <ClaimActivityCard key={claim.id} claim={claim} onCancel={() => updateClaim(claim, "CANCELLED", "Cancelled by claimant")} onComplete={() => completeClaim(claim)} />) : <EmptyActivity title="No claims yet" to="/reports" action="Browse reports" />}</div>}
        </>
      )}
    </section>
  );
}

function OwnedReportCard({ report }) {
  return (
    <article className="activity-card">
      <div className="activity-card-main"><span className={`type-badge ${report.report_type.toLowerCase()}`}>{report.report_type}</span><h2><Link to={`/reports/${report.id}`}>{report.item_name}</Link></h2><p className="muted">{report.reference} · {report.area} · {report.event_date}</p></div>
      <StatusBadge status={report.status} />
      <div className="button-row"><Link className="button secondary small" to={`/reports/${report.id}`}>Open details</Link>{!["CLOSED", "EXPIRED", "RECOVERED", "RETURNED"].includes(report.status) && <Link className="button secondary small" to={`/reports/${report.id}/edit`}>Edit</Link>}</div>
    </article>
  );
}

function ClaimActivityCard({ claim, onCancel, onComplete }) {
  const [reports, setReports] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([
      api.get(`/reports/${claim.lost_report_id}`),
      api.get(`/reports/${claim.found_report_id}`),
    ]).then(([lost, found]) => { if (active) setReports([lost.data, found.data]); })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); });
    return () => { active = false; };
  }, [claim.lost_report_id, claim.found_report_id]);
  return (
    <article className="activity-card claim-activity">
      <div><h2>Claim {claim.id.slice(0, 8)} <StatusBadge status={claim.status} /></h2>
        {reports ? <p>{reports[0].item_name} <span aria-hidden="true">↔</span> {reports[1].item_name}</p> : <Loading label="Loading claim items..." />}
        <p className="muted">Submitted {new Date(claim.created_at).toLocaleString()}</p>
        <p>{claim.ownership_explanation}</p>{claim.review_comment && <p className="review-comment"><strong>Review note:</strong> {claim.review_comment}</p>}
        <ErrorMessage>{error}</ErrorMessage>
      </div>
      {claim.status === "PENDING" && <button className="button secondary small" onClick={onCancel}>Cancel claim</button>}
      {claim.status === "APPROVED" && <button className="button primary small" onClick={onComplete}>Confirm handover</button>}
    </article>
  );
}

function StatusBadge({ status }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{status.replaceAll("_", " ")}</span>;
}

function EmptyActivity({ title, to, action }) {
  return <div className="empty-state"><h2>{title}</h2><Link className="button secondary" to={to}>{action}</Link></div>;
}

function AdminPage() {
  const [tab, setTab] = useState("overview");
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    api.get("/dashboard/admin")
      .then(({ data }) => setDashboard(data))
      .catch((requestError) => setError(apiErrorMessage(requestError)));
  }, [refresh]);

  return (
    <section>
      <div className="section-heading"><div><span className="eyebrow">ADMINISTRATION</span><h1>Admin dashboard</h1></div></div>
      <ErrorMessage>{error}</ErrorMessage>
      <div className="tabs" role="tablist" aria-label="Administration">
        {["overview", "claims", "reports", "categories"].map((item) => <button key={item} role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}
      </div>
      {tab === "overview" && <AdminOverview dashboard={dashboard} />}
      {tab === "claims" && <AdminClaims onChanged={() => setRefresh((value) => value + 1)} />}
      {tab === "reports" && <AdminReports />}
      {tab === "categories" && <AdminCategories />}
    </section>
  );
}

function AdminOverview({ dashboard }) {
  if (!dashboard) return <Loading label="Loading system statistics..." />;
  const counts = ["active_lost", "active_found", "strong_matches", "pending_claims", "completed_returns"];
  return (
    <div>
      <div className="stats-grid">{counts.map((key) => <div className="stat-card" key={key}><strong>{dashboard[key]}</strong><span>{key.replaceAll("_", " ")}</span></div>)}</div>
      <div className="admin-overview-grid">
        <section className="detail-panel"><h2>Reports by category</h2>
          {dashboard.category_distribution.length ? <ul className="distribution-list">{dashboard.category_distribution.map((item) => <li key={item.category_id}><span>{item.category}</span><strong>{item.reports}</strong></li>)}</ul> : <p className="muted">No categories found.</p>}
        </section>
        <section className="detail-panel"><h2>Recent activity</h2>
          {dashboard.recent_activity.length ? <ul className="activity-feed">{dashboard.recent_activity.map((event, index) => <li key={`${event.action}-${index}`}><strong>{event.action.replaceAll("_", " ")}</strong><span>{event.resource_type}</span><time>{new Date(event.occurred_at).toLocaleString()}</time></li>)}</ul> : <p className="muted">No activity recorded yet.</p>}
        </section>
      </div>
    </div>
  );
}

function AdminClaims({ onChanged }) {
  const [claims, setClaims] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() {
    try {
      const { data } = await api.get("/claims?scope=all&page_size=100");
      setClaims(data.items);
      setError("");
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);
  if (loading) return <Loading label="Loading claims for review..." />;
  return <section><ErrorMessage>{error}</ErrorMessage>{claims.length ? <div className="stack-list">{claims.map((claim) => <AdminClaimCard key={claim.id} claim={claim} onUpdated={async () => { await load(); onChanged(); }} />)}</div> : <div className="empty-state"><h2>No claims to review</h2></div>}</section>;
}

function AdminClaimCard({ claim, onUpdated }) {
  const [reports, setReports] = useState(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get(`/reports/${claim.lost_report_id}`),
      api.get(`/reports/${claim.found_report_id}`),
    ]).then(([lost, found]) => { if (active) setReports([lost.data, found.data]); })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); });
    return () => { active = false; };
  }, [claim.lost_report_id, claim.found_report_id]);

  async function changeStatus(status) {
    setError("");
    setPending(true);
    try {
      await api.patch(`/claims/${claim.id}/status`, { status, review_comment: comment || null }, {
        headers: { "If-Match": String(claim.version) },
      });
      setComment("");
      await onUpdated();
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }

  async function complete() {
    setError("");
    setPending(true);
    try {
      await api.post(`/claims/${claim.id}/complete`);
      await onUpdated();
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }

  return (
    <article className="admin-claim-card">
      <div className="card-topline"><h2>Claim {claim.id.slice(0, 8)}</h2><StatusBadge status={claim.status} /></div>
      {reports ? (
        <div className="claim-comparison">
          {reports.map((report) => (
            <section key={report.id}>
              <span className={`type-badge ${report.report_type.toLowerCase()}`}>{report.report_type}</span>
              <h3><Link to={`/reports/${report.id}`}>{report.item_name}</Link></h3>
              <p>{report.colour}{report.brand ? ` · ${report.brand}` : ""}</p>
              <p>{report.event_date} · {report.area}</p>
              <p>{report.description}</p>
              {report.location_details && <p><strong>Private location:</strong> {report.location_details}</p>}
              {report.verification_question && <p><strong>Verification question:</strong> {report.verification_question}</p>}
              {report.storage_instructions && <p><strong>Storage:</strong> {report.storage_instructions}</p>}
            </section>
          ))}
        </div>
      ) : <Loading label="Loading report details..." />}
      <div className="claim-evidence"><h3>Claimant’s explanation</h3><p>{claim.ownership_explanation}</p><p className="muted">Verification answer is protected and is not shown in this screen.</p>{claim.review_comment && <p><strong>Previous review note:</strong> {claim.review_comment}</p>}</div>
      <ErrorMessage>{error}</ErrorMessage>
      {["PENDING", "UNDER_REVIEW", "APPROVED"].includes(claim.status) && <label className="field"><span>{claim.status === "APPROVED" ? "Reason to revoke (if needed)" : "Review / decision note"}</span><textarea rows={2} minLength={3} maxLength={1500} value={comment} onChange={(event) => setComment(event.target.value)} /></label>}
      <div className="button-row">
        {claim.status === "PENDING" && <button className="button secondary" disabled={pending} onClick={() => changeStatus("UNDER_REVIEW")}>Start review</button>}
        {["PENDING", "UNDER_REVIEW"].includes(claim.status) && <><button className="button primary" disabled={pending || comment.trim().length < 3} onClick={() => changeStatus("APPROVED")}>Approve</button><button className="button danger" disabled={pending || comment.trim().length < 3} onClick={() => changeStatus("REJECTED")}>Reject</button></>}
        {claim.status === "APPROVED" && <><button className="button primary" disabled={pending} onClick={complete}>Confirm return</button><button className="button danger" disabled={pending || comment.trim().length < 3} onClick={() => changeStatus("REVOKED")}>Revoke approval</button></>}
      </div>
    </article>
  );
}

function AdminReports() {
  const [reports, setReports] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const query = status ? `?status=${status}&page_size=100` : "?page_size=100";
    api.get(`/admin/reports${query}`).then(({ data }) => { if (active) setReports(data.items); })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [status]);
  return (
    <section><div className="filter-heading"><h2>All reports</h2><label className="field compact-field"><span>Filter status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option>{["ACTIVE", "POTENTIAL_MATCH_FOUND", "CLAIM_UNDER_REVIEW", "CLOSED", "EXPIRED", "RECOVERED", "RETURNED"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label></div>
      <ErrorMessage>{error}</ErrorMessage>{loading ? <Loading /> : reports.length ? <div className="report-grid">{reports.map((report) => <article className="report-card" key={report.id}><div className="card-topline"><span className={`type-badge ${report.report_type.toLowerCase()}`}>{report.report_type}</span><StatusBadge status={report.status} /></div><h2><Link to={`/reports/${report.id}`}>{report.item_name}</Link></h2><p>{report.reference} · {report.area}</p><Link className="inline-link" to={`/reports/${report.id}`}>Moderate report →</Link></article>)}</div> : <div className="empty-state"><p>No reports for this filter.</p></div>}</section>
  );
}

function AdminCategories() {
  const [categories, setCategories] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  async function load() {
    const { data } = await api.get("/categories?include_inactive=true");
    setCategories(data.items);
  }
  useEffect(() => { load().catch((requestError) => setError(apiErrorMessage(requestError))); }, []);
  async function createCategory(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setPending(true);
    try {
      await api.post("/categories", { name, description: description || null });
      setName("");
      setDescription("");
      setNotice("Category created.");
      await load();
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setPending(false);
    }
  }
  async function toggle(category) {
    setError("");
    setNotice("");
    try {
      await api.patch(`/categories/${category.id}`, { is_active: !category.is_active });
      setNotice(`${category.name} ${category.is_active ? "deactivated" : "activated"}.`);
      await load();
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    }
  }
  return (
    <section className="admin-overview-grid">
      <form className="card category-form" onSubmit={createCategory}><h2>Add category</h2><ErrorMessage>{error}</ErrorMessage><SuccessMessage>{notice}</SuccessMessage>
        <Field label="Category name" minLength={2} maxLength={60} required value={name} onChange={(event) => setName(event.target.value)} />
        <label className="field"><span>Description</span><textarea maxLength={300} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <button className="button primary" disabled={pending}>{pending ? "Saving..." : "Create category"}</button>
      </form>
      <section className="detail-panel"><h2>Manage categories</h2>{categories.length ? <ul className="category-list">{categories.map((category) => <li key={category.id}><div><strong>{category.name}</strong><span className="muted">{category.description}</span></div><div><StatusBadge status={category.is_active ? "ACTIVE" : "INACTIVE"} /><button className="button secondary small" onClick={() => toggle(category)}>{category.is_active ? "Deactivate" : "Activate"}</button></div></li>)}</ul> : <p className="muted">No categories have been seeded yet.</p>}</section>
    </section>
  );
}

function NotFound() {
  return <div className="empty-state"><h1>Page not found</h1><p>This page may have moved or is unavailable.</p><Link className="button primary" to="/">Return home</Link></div>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem("token")));
  useEffect(() => {
    const authenticated = (event) => setUser(event.detail);
    const unauthorized = () => setUser(null);
    window.addEventListener("reclaimai:authenticated", authenticated);
    window.addEventListener("reclaimai:unauthorized", unauthorized);
    const token = localStorage.getItem("token");
    if (token) {
      api.get("/users/me")
        .then(({ data }) => setUser(data))
        .catch(() => localStorage.removeItem("token"))
        .finally(() => setLoading(false));
    }
    return () => {
      window.removeEventListener("reclaimai:authenticated", authenticated);
      window.removeEventListener("reclaimai:unauthorized", unauthorized);
    };
  }, []);

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
  }

  if (loading) return <main className="page-shell"><Loading label="Restoring your session..." /></main>;
  return <Layout user={user} onLogout={logout} />;
}
