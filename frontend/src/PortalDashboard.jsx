import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, Bell, Building2, CalendarDays, CheckCircle2, CircleDollarSign,
  ClipboardCheck, FileText, Film, HeartHandshake, KeyRound, MapPin, RefreshCw,
  Search, ShieldCheck, Ticket, Users, Wallet, X
} from "lucide-react";

const api = (base, route) => `${base.replace(/\/$/, "")}/api/v1${route}`;

async function request(base, token, route, options = {}) {
  const response = await fetch(api(base, route), {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail || data?.message || `Request failed (${response.status})`);
  return data;
}

function StatCard({ icon: Icon, label, value, hint }) {
  return <article className="portal-stat"><span className="portal-stat-icon"><Icon size={18} /></span><span className="portal-stat-label">{label}</span><strong>{value ?? "—"}</strong>{hint && <small>{hint}</small>}</article>;
}

function Panel({ title, subtitle, children, action }) {
  return <section className="portal-panel"><div className="portal-panel-head"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}

function Status({ value }) {
  const kind = String(value || "unknown").toLowerCase().replaceAll("_", "-");
  return <span className={`portal-status status-${kind}`}>{String(value || "unknown").replaceAll("_", " ")}</span>;
}

export default function PortalDashboard({ apiBase, token, currentUser, onNotice, onClose }) {
  const [section, setSection] = useState("overview");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [profile, setProfile] = useState({ name: currentUser?.name || "", phone: currentUser?.phone || "" });
  const [notifications, setNotifications] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [cities, setCities] = useState([]);
  const [venues, setVenues] = useState([]);
  const [categories, setCategories] = useState([]);
  const [myEvents, setMyEvents] = useState([]);
  const [myApplication, setMyApplication] = useState(null);
  const [organizerApps, setOrganizerApps] = useState([]);
  const [pendingEvents, setPendingEvents] = useState([]);
  const [users, setUsers] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [auditRows, setAuditRows] = useState([]);
  const [report, setReport] = useState([]);
  const [applicationForm, setApplicationForm] = useState({ organization_name: "", contact_phone: currentUser?.phone || "", website: "", description: "" });
  const [eventForm, setEventForm] = useState({ title: "", description: "", city_id: "", category_id: "", venue_id: "", venue_space_id: "", starts_at: "", duration: 120, booking_mode: "general_admission", price: 499, premium_price: 799, capacity: 100, poster_url: "" });
  const [newVenue, setNewVenue] = useState({ city_id: "", name: "", venue_type: "auditorium", address: "" });
  const [userQuery, setUserQuery] = useState("");
  const [tmdbQuery, setTmdbQuery] = useState("");
  const [tmdbResults, setTmdbResults] = useState([]);
  const [ticketmasterCity, setTicketmasterCity] = useState("Mumbai");
  const [ticketmasterResults, setTicketmasterResults] = useState([]);
  const [ticketCode, setTicketCode] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [refundReasons, setRefundReasons] = useState({});
  const [reviewReason, setReviewReason] = useState("");

  const role = currentUser?.role || "customer";
  const isAdmin = role === "admin";
  const isOrganizer = role === "organizer";
  const isCustomer = role === "customer";

  const showMessage = (message) => {
    setNotice(message);
    onNotice?.(message);
  };

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const common = [
        request(apiBase, token, "/portal/dashboard"),
        request(apiBase, token, "/portal/notifications?limit=50"),
        request(apiBase, token, "/bookings/me"),
        request(apiBase, token, "/cities"),
        request(apiBase, token, "/venues"),
        request(apiBase, token, "/event-categories"),
      ];
      const [stats, notificationData, bookingData, cityData, venueData, categoryData] = await Promise.all(common);
      setDashboard(stats);
      setNotifications(notificationData?.items || []);
      setBookings(Array.isArray(bookingData) ? bookingData : []);
      setCities(Array.isArray(cityData) ? cityData : []);
      setVenues(Array.isArray(venueData) ? venueData : []);
      setCategories(Array.isArray(categoryData) ? categoryData : []);

      if (isOrganizer || isAdmin) {
        const mine = await request(apiBase, token, "/portal/events/mine");
        setMyEvents(mine?.items || []);
      }
      if (isCustomer) {
        const application = await request(apiBase, token, "/portal/organizer-applications/me");
        setMyApplication(application);
      }
      if (isAdmin) {
        const [apps, events, people, refundList, audits, sales] = await Promise.all([
          request(apiBase, token, "/portal/admin/organizer-applications?status_filter=pending"),
          request(apiBase, token, "/portal/admin/events/pending"),
          request(apiBase, token, "/portal/admin/users?page=1&page_size=100"),
          request(apiBase, token, "/portal/admin/refunds?status_filter=requested"),
          request(apiBase, token, "/portal/admin/audit?limit=100"),
          request(apiBase, token, "/portal/reports/sales?days=30"),
        ]);
        setOrganizerApps(apps?.items || []);
        setPendingEvents(Array.isArray(events) ? events : []);
        setUsers(people?.items || []);
        setRefunds(refundList?.items || []);
        setAuditRows(audits?.items || []);
        setReport(sales?.series || []);
      }
    } catch (failure) {
      setError(failure.message || "Could not load the portal.");
    } finally {
      setBusy(false);
    }
  }, [apiBase, token, isAdmin, isOrganizer, isCustomer]);

  useEffect(() => { load(); }, [load]);

  const spacesForVenue = useMemo(
    () => venues.find((venue) => String(venue.id) === String(eventForm.venue_id))?.spaces || [],
    [venues, eventForm.venue_id],
  );

  async function runAction(fn, success) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      if (success) showMessage(success);
      await load();
    } catch (failure) {
      setError(failure.message || "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    await runAction(
      () => request(apiBase, token, "/portal/profile", { method: "PATCH", body: JSON.stringify(profile) }),
      "Profile updated.",
    );
  }

  async function submitOrganizerApplication(event) {
    event.preventDefault();
    await runAction(() => request(apiBase, token, "/portal/organizer-applications", {
      method: "POST",
      body: JSON.stringify({
        ...applicationForm,
        website: applicationForm.website || null,
      }),
    }), "Organizer application submitted for admin review.");
  }

  async function createEventAndSession(event) {
    event.preventDefault();
    const start = new Date(eventForm.starts_at);
    if (!eventForm.venue_space_id || Number.isNaN(start.getTime())) {
      setError("Choose a venue space and a valid future date/time.");
      return;
    }
    await runAction(async () => {
      const venue = venues.find((item) => String(item.id) === String(eventForm.venue_id));
      const created = await request(apiBase, token, "/manage/events", {
        method: "POST",
        body: JSON.stringify({
          organizer_id: currentUser.id,
          city_id: Number(eventForm.city_id),
          category_id: Number(eventForm.category_id),
          venue_id: Number(eventForm.venue_id),
          title: eventForm.title,
          description: eventForm.description,
          event_type: "local",
          poster_url: eventForm.poster_url || null,
        }),
      });
      const session = await request(apiBase, token, "/manage/sessions", {
        method: "POST",
        body: JSON.stringify({
          event_id: created.id,
          venue_space_id: Number(eventForm.venue_space_id),
          starts_at: start.toISOString(),
          ends_at: new Date(start.getTime() + Number(eventForm.duration) * 60000).toISOString(),
          base_price: Number(eventForm.price),
          tax_percent: 18,
          convenience_fee: 25,
          booking_mode: eventForm.booking_mode,
        }),
      });
      if (eventForm.booking_mode === "general_admission") {
        await request(apiBase, token, "/manage/ticket-types", {
          method: "POST",
          body: JSON.stringify({
            session_id: session.id,
            name: "General Admission",
            description: "Standard admission",
            price: Number(eventForm.price),
            capacity: Number(eventForm.capacity),
          }),
        }).catch(() => null);
      }
      if (isOrganizer) {
        await request(apiBase, token, `/portal/events/${created.id}/submit`, { method: "POST" });
      } else {
        await request(apiBase, token, `/manage/events/${created.id}/publish`, { method: "POST" });
      }
    }, isOrganizer ? "Event and session created. Submitted for admin approval." : "Event and session created and published.");
  }

  async function decide(path, body, success) {
    await runAction(
      () => request(apiBase, token, path, { method: "POST", body: JSON.stringify(body) }),
      success,
    );
  }

  async function toggleUser(userId, isActive) {
    await runAction(() => request(apiBase, token, `/portal/admin/users/${userId}/status`, {
      method: "PATCH", body: JSON.stringify({ is_active: !isActive }),
    }), "User status updated.");
  }

  async function createVenue(event) {
    event.preventDefault();
    await runAction(() => request(apiBase, token, "/manage/venues", {
      method: "POST", body: JSON.stringify({ ...newVenue, city_id: Number(newVenue.city_id) }),
    }), "Venue created.");
  }

  async function searchTmdb(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await request(apiBase, token, `/integrations/tmdb/search?query=${encodeURIComponent(tmdbQuery)}`);
      setTmdbResults(data.results || []);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }

  async function importTmdb(tmdbId) {
    await runAction(() => request(apiBase, token, "/integrations/tmdb/import", {
      method: "POST", body: JSON.stringify({ tmdb_id: tmdbId, language: "hi", import_poster: true }),
    }), "Movie imported into CineBook.");
  }

  async function searchTicketmaster(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await request(apiBase, token, `/integrations/ticketmaster/events?city=${encodeURIComponent(ticketmasterCity)}`);
      setTicketmasterResults(data.events || []);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }

  const tabs = [
    ["overview", "Overview", Activity],
    ...(isCustomer ? [["organizer", "Become organizer", HeartHandshake], ["refunds", "My bookings & refunds", Wallet]] : []),
    ...(isOrganizer || isAdmin ? [["events", "My events", CalendarDays], ["analytics", "Analytics", CircleDollarSign]] : []),
    ...(isAdmin ? [["moderation", "Moderation", ShieldCheck], ["users", "Users & venues", Users], ["refund-queue", "Refund queue", Wallet], ["reports", "Reports & audit", FileText], ["integrations", "Movie & event imports", Film], ["checkin", "Ticket check-in", ClipboardCheck]] : []),
    ["notifications", "Notifications", Bell],
    ["profile", "Profile", Users],
  ];

  return (
    <section className="portal-shell">
      <div className="portal-heading">
        <div><span className="mini-label">CINEBOOK CONTROL CENTRE</span><h2>{isAdmin ? "Admin dashboard" : isOrganizer ? "Organizer studio" : "Your account hub"}</h2><p>{currentUser?.name} · {role}</p></div>
        <div className="portal-heading-actions"><button className="secondary-button" onClick={load} disabled={busy}><RefreshCw size={15} /> Refresh</button><button className="icon-button" onClick={onClose} aria-label="Close dashboard"><X /></button></div>
      </div>

      <div className="portal-layout">
        <aside className="portal-sidebar">
          {tabs.map(([id, label, Icon]) => <button type="button" key={id} className={section === id ? "active" : ""} onClick={() => setSection(id)}><Icon size={16} />{label}</button>)}
        </aside>
        <div className="portal-content">
          {error && <div className="portal-alert error">{error}</div>}
          {notice && <div className="portal-alert success">{notice}</div>}
          {busy && <div className="portal-loading"><RefreshCw size={16} className="spin" /> Updating portal…</div>}

          {section === "overview" && <>
            <div className="portal-stats-grid">
              {Object.entries(dashboard || {}).filter(([key]) => key !== "role").map(([key, value]) => <StatCard key={key} icon={key.includes("sales") ? CircleDollarSign : key.includes("user") ? Users : key.includes("refund") ? Wallet : key.includes("booking") ? Ticket : Activity} label={key.replaceAll("_", " ")} value={key.includes("sales") ? `₹${Number(value).toLocaleString("en-IN")}` : value} />)}
            </div>
            <Panel title="Quick actions" subtitle="Your available tasks based on account permissions">
              <div className="portal-quick-actions">
                {isCustomer && <button onClick={() => setSection("organizer")}><HeartHandshake /> Apply to become an organizer</button>}
                {(isOrganizer || isAdmin) && <button onClick={() => setSection("events")}><CalendarDays /> Manage events</button>}
                {isAdmin && <button onClick={() => setSection("moderation")}><ShieldCheck /> Review pending submissions</button>}
                <button onClick={() => setSection("notifications")}><Bell /> View notifications ({notifications.filter((item) => !item.read_at).length})</button>
                <button onClick={() => setSection("profile")}><Users /> Edit profile</button>
              </div>
            </Panel>
            {isAdmin && <Panel title="Platform health" subtitle="Quick operational totals"><p>Use Reports & audit for recent sales and the moderation queues for submitted content. External integrations remain disabled until their backend credentials are configured.</p></Panel>}
          </>}

          {section === "profile" && <Panel title="Profile settings" subtitle="Update the name and contact phone associated with your CineBook account">
            <form className="portal-form" onSubmit={saveProfile}>
              <label>Full name<input required minLength="2" maxLength="100" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} /></label>
              <label>Phone number<input value={profile.phone || ""} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} maxLength="30" /></label>
              <label>Email address<input disabled value={currentUser?.email || ""} /></label>
              <button className="primary-button" disabled={busy}>Save profile</button>
            </form>
          </Panel>}

          {section === "organizer" && isCustomer && <Panel title="Become an organizer" subtitle="Submit your organization details for admin review">
            {myApplication ? <div className="portal-list-row"><div><b>{myApplication.organization_name}</b><small>{myApplication.description}</small></div><Status value={myApplication.status} /></div> : <form className="portal-form" onSubmit={submitOrganizerApplication}>
              <label>Organization name<input required value={applicationForm.organization_name} onChange={(e) => setApplicationForm({ ...applicationForm, organization_name: e.target.value })} /></label>
              <label>Contact phone<input required value={applicationForm.contact_phone} onChange={(e) => setApplicationForm({ ...applicationForm, contact_phone: e.target.value })} /></label>
              <label>Website (optional)<input type="url" value={applicationForm.website} onChange={(e) => setApplicationForm({ ...applicationForm, website: e.target.value })} /></label>
              <label>About your organization<textarea required minLength="30" value={applicationForm.description} onChange={(e) => setApplicationForm({ ...applicationForm, description: e.target.value })} /></label>
              <button className="primary-button" disabled={busy}>Submit application</button>
            </form>}
          </Panel>}

          {section === "events" && (isOrganizer || isAdmin) && <div className="portal-stack">
            <Panel title="Create an event" subtitle={isOrganizer ? "Your submission goes to the admin moderation queue." : "Admin-created events can be published directly after a session is added."}>
              <form className="portal-form portal-form-grid" onSubmit={createEventAndSession}>
                <label>Event title<input required value={eventForm.title} onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })} /></label>
                <label>City<select required value={eventForm.city_id} onChange={(e) => setEventForm({ ...eventForm, city_id: e.target.value })}><option value="">Choose city</option>{cities.map((c) => <option key={c.id} value={c.id}>{c.name}, {c.state}</option>)}</select></label>
                <label>Category<select required value={eventForm.category_id} onChange={(e) => setEventForm({ ...eventForm, category_id: e.target.value })}><option value="">Choose category</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
                <label>Venue<select required value={eventForm.venue_id} onChange={(e) => setEventForm({ ...eventForm, venue_id: e.target.value, venue_space_id: "" })}><option value="">Choose venue</option>{venues.filter((v) => !eventForm.city_id || String(v.city_id) === String(eventForm.city_id)).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
                <label>Venue space<select required value={eventForm.venue_space_id} onChange={(e) => setEventForm({ ...eventForm, venue_space_id: e.target.value })}><option value="">Choose hall/screen</option>{spacesForVenue.map((space) => <option key={space.id} value={space.id}>{space.name} · capacity {space.capacity}</option>)}</select></label>
                <label>Start date/time<input type="datetime-local" required value={eventForm.starts_at} onChange={(e) => setEventForm({ ...eventForm, starts_at: e.target.value })} /></label>
                <label>Duration (minutes)<input type="number" min="15" max="1000" value={eventForm.duration} onChange={(e) => setEventForm({ ...eventForm, duration: e.target.value })} /></label>
                <label>Booking mode<select value={eventForm.booking_mode} onChange={(e) => setEventForm({ ...eventForm, booking_mode: e.target.value })}><option value="general_admission">General admission</option><option value="assigned">Assigned seats</option></select></label>
                <label>General/Premium price (₹)<input type="number" min="1" value={eventForm.price} onChange={(e) => setEventForm({ ...eventForm, price: e.target.value })} /></label>
                <label>Capacity<input type="number" min="1" max="1000000" value={eventForm.capacity} onChange={(e) => setEventForm({ ...eventForm, capacity: e.target.value })} /></label>
                <label>Poster URL (optional)<input type="url" value={eventForm.poster_url} onChange={(e) => setEventForm({ ...eventForm, poster_url: e.target.value })} /></label>
                <label className="span-2">Description<textarea required value={eventForm.description} onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })} /></label>
                <div className="span-2"><button className="primary-button" disabled={busy}>Create event & schedule session</button></div>
              </form>
            </Panel>
            <Panel title="Your event listings" subtitle="Check the moderation state and the sessions you've submitted">
              {myEvents.length ? myEvents.map((item) => <div className="portal-list-row" key={item.id}><div><b>{item.title}</b><small>Event #{item.id} · City #{item.city_id}</small></div><Status value={item.status} /></div>) : <p className="portal-muted">No events have been created yet.</p>}
            </Panel>
            {isAdmin && <Panel title="Create a venue" subtitle="Add a venue directory record; then configure spaces/seats through the management API">
              <form className="portal-form portal-form-grid" onSubmit={createVenue}>
                <label>City<select required value={newVenue.city_id} onChange={(e) => setNewVenue({ ...newVenue, city_id: e.target.value })}><option value="">Choose city</option>{cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
                <label>Venue name<input required value={newVenue.name} onChange={(e) => setNewVenue({ ...newVenue, name: e.target.value })} /></label>
                <label>Venue type<select value={newVenue.venue_type} onChange={(e) => setNewVenue({ ...newVenue, venue_type: e.target.value })}>{["cinema","auditorium","stadium","open_ground","convention_center","club","other"].map((v) => <option key={v} value={v}>{v.replaceAll("_", " ")}</option>)}</select></label>
                <label>Address<input required value={newVenue.address} onChange={(e) => setNewVenue({ ...newVenue, address: e.target.value })} /></label>
                <div className="span-2"><button className="secondary-button" disabled={busy}>Add venue</button></div>
              </form>
            </Panel>}
          </div>}

          {section === "analytics" && (isOrganizer || isAdmin) && <Panel title="Sales analytics" subtitle="Confirmed bookings and gross demo sales by event">
            {isOrganizer && myEvents.map((event) => <div className="portal-list-row" key={event.id}><div><b>{event.title}</b><small>Event status: {event.status}</small></div><span>Open dashboard stats for revenue & bookings</span></div>)}
            <p className="portal-muted">Summary cards above show the current account totals. Admins can open Reports & audit for the daily platform sales series.</p>
          </Panel>}

          {section === "moderation" && isAdmin && <div className="portal-stack">
            <Panel title="Organizer applications" subtitle="Approve or reject organizer access">
              {organizerApps.length ? organizerApps.map((item) => <div className="portal-moderation-row" key={item.id}><div><b>{item.organization_name}</b><small>{item.user?.name} · {item.user?.email} · {item.contact_phone}</small><p>{item.description}</p></div><div className="portal-row-actions"><button className="primary-button" onClick={() => decide(`/portal/admin/organizer-applications/${item.id}/decision`, { decision: "approve" }, "Organizer approved.")}>Approve</button><button className="secondary-button" onClick={() => decide(`/portal/admin/organizer-applications/${item.id}/decision`, { decision: "reject", note: reviewNote }, "Application rejected.")}>Reject</button></div></div>) : <p className="portal-muted">No pending organizer applications.</p>}
            </Panel>
            <Panel title="Events awaiting approval" subtitle="Only approved events are visible in public discovery">
              {pendingEvents.length ? pendingEvents.map((item) => <div className="portal-moderation-row" key={item.id}><div><b>{item.title}</b><small>{item.organizer?.name} · {item.city} · {item.venue}</small><p>{item.description}</p></div><div className="portal-row-actions"><button className="primary-button" onClick={() => decide(`/portal/admin/events/${item.id}/decision`, { decision: "approve" }, "Event approved and published.")}>Approve</button><button className="secondary-button" onClick={() => decide(`/portal/admin/events/${item.id}/decision`, { decision: "reject", note: reviewNote }, "Event returned for changes.")}>Reject</button></div></div>) : <p className="portal-muted">No events are waiting for review.</p>}
              <label className="portal-note-field">Moderation note<input value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} placeholder="Optional note for the organizer" /></label>
            </Panel>
          </div>}

          {section === "users" && isAdmin && <div className="portal-stack">
            <Panel title="User management" subtitle="Search users and activate or suspend customer/organizer accounts">
              <label className="portal-search"><Search size={15} /><input value={userQuery} onChange={(e) => setUserQuery(e.target.value)} placeholder="Filter name or email" /></label>
              {users.filter((u) => `${u.name} ${u.email} ${u.role}`.toLowerCase().includes(userQuery.toLowerCase())).map((u) => <div className="portal-list-row" key={u.id}><div><b>{u.name}</b><small>{u.email} · {u.role}</small></div><div className="portal-row-actions"><Status value={u.is_active ? "active" : "disabled"} /><button className="secondary-button" disabled={u.id === currentUser.id || u.role === "admin"} onClick={() => toggleUser(u.id, u.is_active)}>{u.is_active ? "Suspend" : "Activate"}</button></div></div>)}
            </Panel>
          </div>}

          {section === "refund-queue" && isAdmin && <Panel title="Refund requests" subtitle="Review the customer's request. Processing is simulated until a provider refund integration is configured.">
            {refunds.length ? refunds.map((refund) => <div className="portal-moderation-row" key={refund.id}><div><b>{refund.user?.name} · Booking #{refund.booking_id}</b><small>₹{Number(refund.amount).toFixed(2)} · {refund.created_at ? new Date(refund.created_at).toLocaleString() : ""}</small><p>{refund.reason}</p></div><div className="portal-row-actions"><button className="primary-button" onClick={() => decide(`/portal/admin/refunds/${refund.id}/decision`, { decision: "approve" }, "Refund request approved.")}>Approve</button><button className="secondary-button" onClick={() => decide(`/portal/admin/refunds/${refund.id}/decision`, { decision: "reject", note: reviewNote }, "Refund request rejected.")}>Reject</button></div></div>) : <p className="portal-muted">No pending refunds.</p>}
            <label className="portal-note-field">Resolution note<input value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} /></label>
          </Panel>}

          {section === "refunds" && isCustomer && <Panel title="Your bookings & refund requests" subtitle="Request a review before the scheduled event begins">
            {bookings.length ? bookings.map((booking) => <div className="portal-list-row" key={booking.id}><div><b>{booking.booking_reference}</b><small>Session #{booking.session_id} · ₹{Number(booking.total_amount).toFixed(2)} · {booking.status}</small></div><button className="secondary-button" disabled={booking.status !== "confirmed" || busy} onClick={() => decide(`/portal/bookings/${booking.id}/refund-request`, { reason: refundReasons[booking.id] || "Please review my cancellation and refund eligibility." }, "Refund request submitted.")}>Request refund review</button><input aria-label="Refund reason" placeholder="Reason (10+ characters)" value={refundReasons[booking.id] || ""} onChange={(e) => setRefundReasons({ ...refundReasons, [booking.id]: e.target.value })} /></div>) : <p className="portal-muted">No bookings yet.</p>}
          </Panel>}

          {section === "reports" && isAdmin && <div className="portal-stack">
            <Panel title="Daily sales (last 30 days)" subtitle="Confirmed booking totals from the MySQL report query">
              {report.length ? <div className="portal-report-table"><div className="portal-report-head"><b>Date</b><b>Bookings</b><b>Gross sales</b></div>{report.map((row) => <div key={row.date}><span>{row.date}</span><span>{row.confirmed_bookings}</span><b>₹{Number(row.gross_sales).toLocaleString("en-IN")}</b></div>)}</div> : <p className="portal-muted">No confirmed sales in this period.</p>}
            </Panel>
            <Panel title="Audit trail" subtitle="Recent administrative, event, refund and check-in actions">
              {auditRows.map((row) => <div className="portal-list-row" key={row.id}><div><b>{row.action}</b><small>{row.entity_type} #{row.entity_id} · actor {row.actor_id || "system"} · {row.created_at ? new Date(row.created_at).toLocaleString() : ""}</small></div></div>)}
            </Panel>
          </div>}

          {section === "integrations" && isAdmin && <div className="portal-stack">
            <Panel title="TMDB movie import" subtitle="Search official movie metadata and import a selected movie into MySQL">
              <form className="portal-inline-form" onSubmit={searchTmdb}><input required value={tmdbQuery} onChange={(e) => setTmdbQuery(e.target.value)} placeholder="Search movie title" /><button className="secondary-button" disabled={busy}>Search TMDB</button></form>
              {tmdbResults.map((item) => <div className="portal-import-row" key={item.id}>{item.poster_url && <img src={item.poster_url} alt="" />}<div><b>{item.title}</b><small>{item.release_date || "Release date unknown"}</small><p>{item.overview}</p></div><button className="primary-button" onClick={() => importTmdb(item.id)}>Import</button></div>)}
            </Panel>
            <Panel title="Ticketmaster event discovery" subtitle="Search public event listings by Indian city; review results before creating local CineBook events">
              <form className="portal-inline-form" onSubmit={searchTicketmaster}><input required value={ticketmasterCity} onChange={(e) => setTicketmasterCity(e.target.value)} placeholder="City" /><button className="secondary-button" disabled={busy}>Search events</button></form>
              {ticketmasterResults.map((item) => <div className="portal-list-row" key={item.id}><div><b>{item.name}</b><small>{item.venue?.name || "Venue unknown"} · {item.start?.localDate || "Date unknown"}</small><p>{item.description}</p><a href={item.url} target="_blank" rel="noreferrer">Provider listing</a></div></div>)}
            </Panel>
          </div>}

          {section === "checkin" && isAdmin && <Panel title="Ticket check-in" subtitle="Scan or enter a CineBook ticket code. Each ticket can be checked in only once.">
            <form className="portal-inline-form" onSubmit={(event) => { event.preventDefault(); runAction(() => request(apiBase, token, "/portal/tickets/check-in", { method: "POST", body: JSON.stringify({ ticket_code: ticketCode }) }), "Ticket checked in."); }}>
              <input required minLength="12" value={ticketCode} onChange={(e) => setTicketCode(e.target.value)} placeholder="Ticket code" />
              <button className="primary-button" disabled={busy}>Validate & check in</button>
            </form>
          </Panel>}

          {section === "notifications" && <Panel title="Notifications" subtitle="Booking, organizer review and refund updates">
            <div className="portal-panel-tools"><button className="secondary-button" onClick={() => runAction(() => request(apiBase, token, "/portal/notifications/read-all", { method: "POST" }), "All notifications marked read.")}>Mark all read</button></div>
            {notifications.length ? notifications.map((item) => <div className={item.read_at ? "portal-list-row" : "portal-list-row unread"} key={item.id}><div><b>{item.title}</b><small>{item.message} · {new Date(item.created_at).toLocaleString()}</small></div>{!item.read_at && <button className="secondary-button" onClick={() => runAction(() => request(apiBase, token, `/portal/notifications/${item.id}/read`, { method: "POST" }), "Notification marked read.")}>Mark read</button>}</div>) : <p className="portal-muted">No notifications yet.</p>}
          </Panel>}
        </div>
      </div>
    </section>
  );
}
