import React, { useEffect, useMemo, useState } from "react";
import {

  Search, MapPin, Ticket, CalendarDays, Film, Music2, Laugh,
  GraduationCap, ChevronRight, Heart, Menu, X, Clock3, ArrowUpRight,
  Sparkles, SlidersHorizontal, RefreshCw, CircleUserRound
} from "lucide-react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const demoMovies = [
  { id: "dm1", title: "Drishyam The Conclusion", language: "Hindi", duration_minutes: 150, certificate: "UA16+", synopsis: "The Salgaonkar family tries to protect the secret behind a past killing as new evidence and a determined Crime Branch officer threaten to reopen the case.", poster_url: "https://imgix.hoyts.com.au/mx/posters/au/drishyam-the-conclusion-3d42e8ed.jpg", release_date: "2026-10-02", demo: true },
  { id: "dm2", title: "Prahaar", language: "Hindi", duration_minutes: 141, certificate: "UA16+", synopsis: "Inspired by public prosecutor Ujjwal Nikam, the courtroom drama follows the legal battle after the 26/11 Mumbai attacks and the pursuit of justice against all odds.", poster_url: "https://www.tribuneindia.com/sortd-service/imaginary/v22-01/jpg/large/high?url=dGhldHJpYnVuZS1zb3J0ZC1wcm8tcHJvZC1zb3J0ZC9tZWRpYTcwOTc4MjgwLTcwNzgtMTFmMS1hZmFlLTJkNzNlMTMwYzExYi5qcGc%3D", release_date: "2026-10-16", demo: true },
  { id: "dm3", title: "Rajini: The Jailer 2", language: "Hindi", duration_minutes: 165, certificate: "UA16+", synopsis: "A retired jailer is pulled back into a dangerous underworld conflict when a new threat puts his family and the legacy he built at risk.", poster_url: "https://m.media-amazon.com/images/M/MV5BYmE0MTFjOTYtMWYxNC00YjFjLTlhNzYtMWQ5ZDEwNjRmYzE1XkEyXkFqcGc%40._V1_.jpg", release_date: "2026-10-15", demo: true },
  { id: "dm4", title: "Nayyi Navelli", language: "Hindi", duration_minutes: 138, certificate: "UA16+", synopsis: "A picture-perfect bride brings unexpected joy to a chaotic Meerut household, until her brother-in-law begins to suspect that their blessing may be a witch in disguise.", poster_url: "https://m.media-amazon.com/images/M/MV5BZmJjYzUyMmYtNDgyNy00MzlkLWE1ZDAtZDFjNzgxYzQxOGY5XkEyXkFqcGc%40._V1_.jpg", release_date: "2026-10-16", demo: true },
  { id: "dm5", title: "Namit Malhotra's Ramayana", language: "Hindi, Tamil, Telugu, Kannada", duration_minutes: 195, certificate: "U", synopsis: "The timeless story of Rama and Ravana returns as a large-scale cinematic retelling, following the epic conflict that has shaped generations.", poster_url: "https://cf-img-a-in.tosshub.com/sites/visualstory/wp/2025/07/ramayanaITG-1751608352043.jpeg?size=%2A%3A900", release_date: "2026-11-05", demo: true }
];

const demoEvents = [
  { id: "de1", title: "Bhumika", event_type: "local", city: { name: "Nagpur" }, venue: { name: "Vasantrao Deshpande Hall" }, category: { name: "Theatre" }, starts_at: "2026-11-09T11:00:00", poster_url: "https://in.bmscdn.com/events/moviecard/ET00437976.jpg", description: "Marathi drama, approximately 2 hours 10 minutes. Actor Vivek Jayant, played by Sachin Khedekar, encounters a dream role that challenges his core and begins to transform him as he inhabits the character. Age guidance: 5 years and above.", starting_price: 300, demo: true },
  { id: "de2", title: "The Messi Experience: A Dream Come True", event_type: "major", city: { name: "Mumbai" }, venue: { name: "Century Mills, Lower Parel" }, category: { name: "Experiences" }, starts_at: "2026-11-07T10:00:00", poster_url: "/posters/experience.svg", description: "An immersive football experience celebrating Lionel Messi's career through interactive exhibits and fan-focused installations.", starting_price: 999, demo: true },
  { id: "de3", title: "Papa Yaar by Zakir Khan", event_type: "major", city: { name: "Mumbai" }, venue: { name: "DOME, SVP Stadium" }, category: { name: "Comedy Shows" }, starts_at: "2026-11-14T20:00:00", poster_url: "/posters/comedy.svg", description: "A live stand-up evening built around observational humour, family stories and everyday relationships.", starting_price: 1299, demo: true },
  { id: "de4", title: "CALVIN HARRIS - Live in Mumbai", event_type: "major", city: { name: "Mumbai" }, venue: { name: "Infinity Bay, Sewri" }, category: { name: "Music Shows" }, starts_at: "2026-12-12T18:30:00", poster_url: "/posters/concert.svg", description: "A large-scale electronic music night featuring DJ and producer Calvin Harris in Mumbai.", starting_price: 3500, demo: true }
];

const categories = [
  { name: "Concerts", icon: Music2, filter: "Concert", poster: "/posters/concert.svg" },
  { name: "Comedy", icon: Laugh, filter: "Comedy", poster: "/posters/comedy.svg" },
  { name: "College fests", icon: GraduationCap, filter: "College Fest", poster: "/posters/college-fest.svg" },
  { name: "Workshops", icon: Sparkles, filter: "Workshop", poster: "/posters/workshop.svg" },
];

function prettyDate(value) {
  if (!value) return "Date to be announced";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date to be announced";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", weekday: "short" }).format(date);
}
function prettyTime(value) {
  if (!value) return "Time to be announced";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time to be announced";
  return new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(date);
}

function getCategoryPoster(item) {
  const category = String(item?.category?.name || item?.event_type || "").toLowerCase();
  if (category.includes("concert") || category.includes("music") || category.includes("major")) return "/posters/concert.svg";
  if (category.includes("comedy")) return "/posters/comedy.svg";
  if (category.includes("college") || category.includes("fest") || category.includes("campus")) return "/posters/college-fest.svg";
  if (category.includes("workshop") || category.includes("education") || category.includes("tech")) return "/posters/workshop.svg";
  if (item?.duration_minutes || item?.language || item?.synopsis) return "/posters/cinema.svg";
  return "/posters/experience.svg";
}

function ImageOrFallback({ src, alt, className = "", fallbackSrc = "/posters/experience.svg" }) {
  const [failed, setFailed] = useState(false);
  const [fallbackFailed, setFallbackFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
    setFallbackFailed(false);
  }, [src, fallbackSrc]);

  if ((!src || failed) && fallbackFailed) {
    return <div className={`image-fallback ${className}`} role="img" aria-label={alt}><Film size={30} /><span>CineBook</span></div>;
  }
  const imageSrc = !src || failed ? fallbackSrc : src;
  return (
    <img
      className={className}
      src={imageSrc}
      alt={alt || "CineBook poster"}
      loading="lazy"
      decoding="async"
      onError={() => {
        if (src && !failed) setFailed(true);
        else setFallbackFailed(true);
      }}
    />
  );
}

function EventCard({ item, saved, onSave, onBook }) {
  return (
    <article className="event-card">
      <div className="event-poster-wrap">
        <ImageOrFallback src={item.poster_url} fallbackSrc={getCategoryPoster(item)} alt={item.title} className="event-poster" />
        <span className={`event-type ${item.event_type === "major" ? "major" : ""}`}>{item.event_type === "major" ? "FEATURED" : "LOCAL PICK"}</span>
        <button className={`icon-button save-button ${saved ? "is-saved" : ""}`} onClick={() => onSave(item.id)} aria-label={saved ? "Unsave event" : "Save event"}><Heart size={17} fill={saved ? "currentColor" : "none"} /></button>
      </div>
      <div className="event-card-body">
        <p className="eyebrow">{item.category?.name || "Experience"} <span>·</span> {item.city?.name || "Your city"}</p>
        <h3>{item.title}</h3>
        <p className="event-description">{item.description || "Discover something worth stepping out for."}</p>
        <div className="event-meta"><span><CalendarDays size={15} />{prettyDate(item.starts_at || item.start_time)}</span><span><Clock3 size={15} />{prettyTime(item.starts_at || item.start_time)}</span>{item.starting_price != null && <span>From ₹{Number(item.starting_price).toFixed(0)}</span>}</div>
        <div className="event-card-footer">
          <span className="venue-label"><MapPin size={14} />{item.venue?.name || "Venue details soon"}</span>
          <button className="text-button" onClick={() => onBook(item)}>Explore <ChevronRight size={16} /></button>
        </div>
      </div>
    </article>
  );
}

function MovieCard({ item, onBook }) {
  return (
    <article className="movie-card">
      <button className="poster-click" onClick={() => onBook(item)} aria-label={`Explore ${item.title}`}>
        <ImageOrFallback src={item.poster_url} fallbackSrc="/posters/cinema.svg" alt={item.title} className="movie-poster" />
        <span className="poster-overlay"><span>View showtimes <ArrowUpRight size={16} /></span></span>
      </button>
      <div className="movie-info"><h3>{item.title}</h3><p>{item.language || "Language TBA"} <span>·</span> {item.duration_minutes ? `${item.duration_minutes} min` : "Duration TBA"}</p></div>
    </article>
  );
}

function VenueBrowser({ apiBase, cityId, cityName, onChooseEvent }) {
  const [query, setQuery] = useState("");
  const [venues, setVenues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedVenue, setSelectedVenue] = useState(null);
  const [venueEvents, setVenueEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState("");
  useEffect(() => {
    if (!cityId) { setVenues([]); return; }
    const controller = new AbortController();
    setLoading(true); setError("");
    fetch(`${apiBase}/api/v1/venues?city_id=${encodeURIComponent(cityId)}`, { signal: controller.signal })
      .then(async (response) => { const data = await response.json().catch(() => []); if (!response.ok) throw new Error(data.detail || "Could not load venues."); return data; })
      .then((data) => setVenues(Array.isArray(data) ? data : []))
      .catch((failure) => { if (failure.name !== "AbortError") setError(failure.message || "Could not load venues."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [apiBase, cityId]);
  useEffect(() => {
    if (!selectedVenue) { setVenueEvents([]); return; }
    const controller = new AbortController();
    setEventsLoading(true); setEventsError("");
    fetch(`${apiBase}/api/v1/venues/${selectedVenue.id}/events`, { signal: controller.signal })
      .then(async (response) => { const data = await response.json().catch(() => []); if (!response.ok) throw new Error(data.detail || "Could not load venue events."); return data; })
      .then((data) => setVenueEvents(Array.isArray(data) ? data : []))
      .catch((failure) => { if (failure.name !== "AbortError") setEventsError(failure.message || "Could not load venue events."); })
      .finally(() => { if (!controller.signal.aborted) setEventsLoading(false); });
    return () => controller.abort();
  }, [apiBase, selectedVenue]);
  if (!cityId) return <section className="venue-discovery"><div className="section-header"><div><span className="mini-label">DISCOVER BY LOCATION</span><h2>Choose a <em>city first.</em></h2><p>Select a database location from the city selector above to explore registered venues.</p></div></div></section>;
  return (
    <section className="venue-discovery" id="venue-discovery">
      <div className="section-header"><div><span className="mini-label">DISCOVER BY LOCATION</span><h2>{selectedVenue ? selectedVenue.name : `Venues in ${cityName}`} <em>{selectedVenue ? "events." : "await."}</em></h2><p>{selectedVenue ? selectedVenue.address : "Browse the venues registered in your selected city."}</p></div>
      <label className="venue-search"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter venues" aria-label="Filter venues" /></label></div>
      {selectedVenue && <button className="text-button venue-back" onClick={() => setSelectedVenue(null)}>← Back to all venues</button>}
      {!selectedVenue && (loading ? <div className="loading-state"><RefreshCw className="spin" size={22} /> Loading venues...</div> : error ? <div className="empty-state"><p>{error}</p></div> : <div className="venue-grid">{venues.filter((venue) => `${venue.name} ${venue.venue_type} ${venue.address}`.toLowerCase().includes(query.toLowerCase())).map((venue) => <button type="button" className="venue-card" key={venue.id} onClick={() => { setSelectedVenue(venue); setQuery(""); }}><div className="venue-card-mark"><MapPin size={24} /></div><div><span className="eyebrow">{String(venue.venue_type || "venue").replaceAll("_", " ")}</span><h3>{venue.name}</h3><p>{venue.address}</p><small>{venue.capacity || 0} capacity · {venue.spaces?.length || 0} spaces</small></div><ChevronRight size={19} /></button>)}{venues.length === 0 && <div className="empty-state"><h3>No registered venues in {cityName}</h3><p>Ask an administrator to add a venue and its seating spaces.</p></div>}</div>)}
      {selectedVenue && (eventsLoading ? <div className="loading-state"><RefreshCw className="spin" size={22} /> Loading upcoming events...</div> : eventsError ? <div className="empty-state"><p>{eventsError}</p></div> : venueEvents.length ? <div className="event-grid">{venueEvents.map((eventItem) => <article className="event-card" key={eventItem.id}><div className="event-poster-wrap"><ImageOrFallback src={eventItem.poster_url} alt={eventItem.title} fallbackSrc={getCategoryPoster(eventItem)} className="event-poster" /></div><div className="event-card-body"><p className="eyebrow">{eventItem.category?.name || "Event"}</p><h3>{eventItem.title}</h3><p className="event-description">{eventItem.description || "Upcoming experience at this venue."}</p><div className="event-meta"><span><CalendarDays size={15} />{prettyDate(eventItem.starts_at)}</span><span>From ₹{Number(eventItem.starting_price || 0).toFixed(0)}</span></div><button className="text-button" onClick={() => onChooseEvent(eventItem)}>Explore showtimes <ChevronRight size={16} /></button></div></article>)}</div> : <div className="empty-state"><CalendarDays size={28} /><h3>No upcoming events at this venue</h3><p>Only events registered against {selectedVenue.name} are shown here.</p></div>)}
    </section>
  );
}
export default function App() {
  const [tab, setTab] = useState("events");
  const [city, setCity] = useState("All cities");
  const [citySearch, setCitySearch] = useState("");
  const [search, setSearch] = useState("");
  const [eventType, setEventType] = useState("all");
  const [events, setEvents] = useState([]);
  const [movies, setMovies] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);
  const [notice, setNotice] = useState("");
  const [saved, setSaved] = useState([]);
  const [selected, setSelected] = useState(null);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [token, setToken] = useState(() => localStorage.getItem("cinebook-token") || "");
  const [currentUser, setCurrentUser] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authName, setAuthName] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPhone, setAuthPhone] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [availableSessions, setAvailableSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [sessionAvailability, setSessionAvailability] = useState(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [selectedTicketTypeId, setSelectedTicketTypeId] = useState("");
  const [bookingQuantity, setBookingQuantity] = useState(1);
  const [bookingBusy, setBookingBusy] = useState(false);
  const [bookingError, setBookingError] = useState("");
  const [bookingStep, setBookingStep] = useState("select");
  const [bookingResult, setBookingResult] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState("demo_upi");
  const [bookingAccepted, setBookingAccepted] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [bookings, setBookings] = useState([]);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingsError, setBookingsError] = useState("");
  const [cancellingBookingId, setCancellingBookingId] = useState(null);

  useEffect(() => {
    const fromStorage = localStorage.getItem("cinebook-saved");
    if (fromStorage) {
      try { setSaved(JSON.parse(fromStorage)); } catch { localStorage.removeItem("cinebook-saved"); }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("cinebook-saved", JSON.stringify(saved));
  }, [saved]);

  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      localStorage.removeItem("cinebook-token");
      return;
    }
    localStorage.setItem("cinebook-token", token);
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => {
        if (!response.ok) throw new Error("Your session expired. Please sign in again.");
        return response.json();
      })
      .then((user) => { if (!cancelled) setCurrentUser(user); })
      .catch(() => {
        if (!cancelled) {
          setCurrentUser(null);
          setToken("");
          localStorage.removeItem("cinebook-token");
        }
      });
    return () => { cancelled = true; };
  }, [token]);

  useEffect(() => {
    if (!token) {
      setBookings([]);
      setBookingsError("");
      setBookingsLoading(false);
      return;
    }
    let cancelled = false;
    setBookingsLoading(true);
    setBookingsError("");
    fetch(`${API_BASE}/api/v1/bookings/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(async (response) => {
      const data = await response.json().catch(() => []);
      if (!response.ok) throw new Error(data.detail || "Could not load your bookings.");
      return data;
    }).then((data) => {
      if (!cancelled) setBookings(Array.isArray(data) ? data : []);
    }).catch((error) => {
      if (!cancelled) setBookingsError(error.message || "Could not load bookings.");
    }).finally(() => {
      if (!cancelled) setBookingsLoading(false);
    });
    return () => { cancelled = true; };
  }, [token]);

  useEffect(() => {
    if (!selectedSessionId || !selected || selected.demo) {
      setSessionAvailability(null);
      return;
    }
    let cancelled = false;
    setAvailabilityLoading(true);
    setBookingError("");
    setSelectedSeats([]);
    setSelectedTicketTypeId("");
    fetch(`${API_BASE}/api/v1/sessions/${selectedSessionId}/availability`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load availability for this session.");
        return response.json();
      })
      .then((data) => {
        if (cancelled) return;
        setSessionAvailability(data);
        const firstAvailableTicket = data.ticket_types?.find((ticket) => ticket.remaining > 0);
        if (firstAvailableTicket) setSelectedTicketTypeId(String(firstAvailableTicket.id));
      })
      .catch((error) => { if (!cancelled) setBookingError(error.message); })
      .finally(() => { if (!cancelled) setAvailabilityLoading(false); });
    return () => { cancelled = true; };
  }, [selectedSessionId, selected]);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoading(true);
      const health = fetch(`${API_BASE}/health/db`).then((r) => { if (!r.ok) throw new Error(); return r.json(); }).catch(() => null);
      const cityRequest = fetch(`${API_BASE}/api/v1/cities`).then((r) => { if (!r.ok) throw new Error(); return r.json(); }).catch(() => []);
      const eventRequest = fetch(`${API_BASE}/api/v1/events`).then((r) => { if (!r.ok) throw new Error(); return r.json(); }).catch(() => []);
      const movieRequest = fetch(`${API_BASE}/api/v1/movies`).then((r) => { if (!r.ok) throw new Error(); return r.json(); }).catch(() => []);
      const [healthData, cityData, eventData, movieData] = await Promise.all([health, cityRequest, eventRequest, movieRequest]);
      if (cancelled) return;
      setApiOnline(Boolean(healthData?.status === "connected"));
      setCities(Array.isArray(cityData) ? cityData : []);
      setEvents(Array.isArray(eventData) && eventData.length ? eventData : demoEvents);
      setMovies(Array.isArray(movieData) && movieData.length ? movieData : demoMovies);
      setLoading(false);
    }
    loadData();
    return () => { cancelled = true; };
  }, []);

  const cityId = cities.find((item) => item.name.toLowerCase() === city.toLowerCase())?.id;
  const selectedCityId = cities.find((item) => item.name.toLowerCase() === city.toLowerCase())?.id;
  const visibleEvents = useMemo(() => {
    const items = events.filter((item) => {
      const matchesType = eventType === "all" || item.event_type === eventType;
      const matchesCity = city === "All cities" || item.city?.name?.toLowerCase() === city.toLowerCase();
      const haystack = `${item.title || ""} ${item.description || ""} ${item.category?.name || ""} ${item.city?.name || ""}`.toLowerCase();
      return matchesType && matchesCity && haystack.includes(search.toLowerCase());
    });
    return items;
  }, [events, eventType, city, search]);

  const visibleMovies = useMemo(() => movies.filter((item) => `${item.title} ${item.language || ""}`.toLowerCase().includes(search.toLowerCase())), [movies, search]);

  function toggleSaved(id) {
    setSaved((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  }
  function chooseCategory(category) {
    setTab("events");
    setEventType("all");
    setSearch(category);
    document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" });
  }
  async function bookItem(item) {
    setSelected(item);
    setBookingError("");
    setAvailableSessions([]);
    setSelectedSessionId("");
    setSessionAvailability(null);
    setSelectedSeats([]);
    setSelectedTicketTypeId("");
    setBookingQuantity(1);
    setBookingStep("select");
    setBookingResult(null);
    setPaymentMethod("demo_upi");
    setBookingAccepted(false);
    if (item.demo) return;
    try {
      const isEvent = item.event_type === "local" || item.event_type === "major";
      const query = isEvent ? `event_id=${item.id}` : `movie_id=${item.id}`;
      const response = await fetch(`${API_BASE}/api/v1/sessions?${query}`);
      if (!response.ok) throw new Error("Could not load sessions. Please try again.");
      const data = await response.json();
      setAvailableSessions(Array.isArray(data) ? data : []);
      if (Array.isArray(data) && data.length) setSelectedSessionId(String(data[0].id));
      else setBookingError("No upcoming sessions are available for this listing yet.");
    } catch (error) {
      setBookingError(error.message || "Could not load sessions.");
    }
  }

  async function submitAuth(event) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      if (authMode === "register") {
        const registerResponse = await fetch(`${API_BASE}/api/v1/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: authName, email: authEmail, password: authPassword, phone: authPhone || null }),
        });
        if (!registerResponse.ok) {
          const body = await registerResponse.json().catch(() => ({}));
          throw new Error(body.detail || "Could not create the account.");
        }
      }
      const loginResponse = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: authEmail, password: authPassword }),
      });
      if (!loginResponse.ok) {
        const body = await loginResponse.json().catch(() => ({}));
        throw new Error(body.detail || "Sign-in failed. Check your email and password.");
      }
      const data = await loginResponse.json();
      setToken(data.access_token);
      setAuthOpen(false);
      setAuthPassword("");
      setNotice("You're signed in. You can continue booking.");
    } catch (error) {
      setAuthError(error.message || "Authentication failed.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function cancelBooking(bookingId) {
    if (!token) return;
    setCancellingBookingId(bookingId);
    setBookingsError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/bookings/${bookingId}/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Could not cancel booking.");
      setBookings((current) => current.map((booking) => booking.id === bookingId ? data : booking));
      setNotice(`Booking ${data.booking_reference} cancelled. Demo refund record created.`);
    } catch (error) {
      setBookingsError(error.message || "Cancellation failed.");
    } finally {
      setCancellingBookingId(null);
    }
  }

  function continueToCheckout() {
    if (!token) {
      setAuthError("");
      setAuthMode("login");
      setAuthOpen(true);
      setNotice("Sign in to continue to checkout.");
      return;
    }
    if (!selectedSessionId || !sessionAvailability) {
      setBookingError("Choose an available session first.");
      return;
    }
    const seatsMode = sessionAvailability.booking_mode === "seats";
    if (seatsMode && selectedSeats.length === 0) {
      setBookingError("Select at least one available seat.");
      return;
    }
    if (!seatsMode && !selectedTicketTypeId) {
      setBookingError("Choose a ticket category with seats remaining.");
      return;
    }
    if (!seatsMode && (selectedTicket?.remaining < bookingQuantity)) {
      setBookingError("The selected ticket category does not have enough tickets remaining.");
      return;
    }
    setBookingError("");
    setBookingAccepted(false);
    setBookingStep("checkout");
  }

  async function submitBooking() {
    if (!bookingAccepted) {
      setBookingError("Please accept the demo booking terms before continuing.");
      return;
    }
    if (!token) {
      setAuthError("");
      setAuthOpen(true);
      setNotice("Sign in to complete your booking.");
      return;
    }
    if (!selected || selected.demo) {
      setBookingError("Preview listings cannot be booked. Add a real listing and session in the backend first.");
      return;
    }
    if (!selectedSessionId || !sessionAvailability) {
      setBookingError("Choose an upcoming session first.");
      return;
    }
    const isSeats = sessionAvailability.booking_mode === "seats";
    if (isSeats && selectedSeats.length === 0) {
      setBookingError("Select at least one available seat.");
      return;
    }
    if (!isSeats && !selectedTicketTypeId) {
      setBookingError("Choose a ticket type.");
      return;
    }
    const payload = isSeats
      ? { session_id: Number(selectedSessionId), seat_ids: selectedSeats, payment_method: paymentMethod }
      : { session_id: Number(selectedSessionId), ticket_type_id: Number(selectedTicketTypeId), quantity: Number(bookingQuantity), payment_method: paymentMethod };
    setBookingBusy(true);
    setBookingError("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/bookings`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Booking failed. Please check availability and retry.");
      setBookingResult(data);
      setBookingStep("confirmed");
      setBookings((current) => [data, ...current.filter((booking) => booking.id !== data.id)]);
      setNotice(`Booking ${data.booking_reference} confirmed. Demo payment only; no money was charged.`);
    } catch (error) {
      setBookingError(error.message || "Booking failed.");
    } finally {
      setBookingBusy(false);
    }
  }

  const selectedSeatRows = (sessionAvailability?.seats || []).filter((seat) => selectedSeats.includes(seat.id));
  const selectedTicket = (sessionAvailability?.ticket_types || []).find((ticket) => String(ticket.id) === selectedTicketTypeId);
  const bookingSubtotal = sessionAvailability?.booking_mode === "seats"
    ? selectedSeatRows.reduce((sum, seat) => sum + Number(seat.price ?? sessionAvailability.base_price ?? 0), 0)
    : selectedTicket && selectedTicket.remaining >= bookingQuantity ? Number(selectedTicket.price) * Number(bookingQuantity) : 0;
  const bookingTaxPercent = Number(sessionAvailability?.tax_percent || 0);
  const bookingTax = Number((bookingSubtotal * bookingTaxPercent / 100).toFixed(2));
  const bookingConvenience = bookingSubtotal > 0 ? Number(sessionAvailability?.convenience_fee || 0) : 0;
  const bookingGrandTotal = bookingSubtotal + bookingTax + bookingConvenience;
  const activeSession = availableSessions.find((session) => String(session.id) === String(selectedSessionId));

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="CineBook home" onClick={() => { setTab("events"); setSearch(""); }}>
          <span className="brand-mark"><Ticket size={21} strokeWidth={2.4} /></span>
          <span>Cine<span>Book</span><small>YOUR CITY. YOUR SCENE.</small></span>
        </a>
        <nav className={`desktop-nav ${mobileMenu ? "nav-open" : ""}`}>
          <button className={tab === "movies" ? "active" : ""} onClick={() => { setTab("movies"); setMobileMenu(false); }}>Movies</button>
          <button className={tab === "events" ? "active" : ""} onClick={() => { setTab("events"); setMobileMenu(false); }}>Events</button>
          <button onClick={() => { setEventType("local"); setTab("events"); setMobileMenu(false); }}>Local finds</button>
        </nav>
        <div className="top-actions">
          <label className="city-select"><MapPin size={16} /><select value={city} onChange={(event) => { setCity(event.target.value); setCitySearch(""); }} aria-label="Choose city"><option>All cities</option>{cities.map((item) => <option key={item.id}>{item.name}</option>)}</select></label>
          {currentUser ? <button className="profile-button" onClick={() => setAccountOpen(true)}><CircleUserRound size={19} /><span>{currentUser.name?.split(" ")[0] || "Account"}</span></button> : <button className="profile-button" onClick={() => { setAuthMode("login"); setAuthError(""); setAuthOpen(true); }}><CircleUserRound size={19} /><span>Sign in</span></button>}
          <button className="icon-button mobile-menu-button" onClick={() => setMobileMenu((value) => !value)} aria-label="Toggle navigation">{mobileMenu ? <X /> : <Menu />}</button>
        </div>
      </header>

      <main>
        <VenueBrowser apiBase={API_BASE} cityId={selectedCityId} cityName={city} onChooseEvent={(item) => bookItem({ ...item, event_type: "local" })} />

        <section className="hero">
          <div className="hero-glow glow-one"></div><div className="hero-glow glow-two"></div>
          <div className="hero-copy">
            <span className="hero-kicker"><Sparkles size={14} /> MORE THAN JUST MOVIES</span>
            <h1>Find your next<br /><em>good story.</em></h1>
            <p>Big stages. Small rooms. Local legends. Find the experiences that bring your city to life.</p>
            <div className="hero-search">
              <Search size={20} />
              <input value={search} onChange={(event) => { setSearch(event.target.value); setTab("events"); }} onKeyDown={(event) => { if (event.key === "Enter") document.getElementById("discover")?.scrollIntoView({behavior: "smooth"}); }} placeholder="Search concerts, workshops, movies..." aria-label="Search movies and events" />
              <button onClick={() => document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" })}>Discover</button>
            </div>
            <div className="hero-tags"><span><span className="status-dot"></span>{apiOnline ? "Live local database" : "Preview mode"} </span><b>·</b><span>Major events</span><b>·</b><span>Local favourites</span></div>
          </div>
          <div className="hero-art" aria-label="Concert crowd image">
            <div className="hero-image hero-image-back"></div>
            <div className="hero-image hero-image-main"></div>
            <div className="floating-note"><span className="note-icon"><Music2 size={18} /></span><span><b>Make a night of it</b><small>Discover something nearby</small></span><ArrowUpRight size={18} /></div>
            <div className="hero-stamp"><span>YOUR CITY</span><strong>IS ALIVE</strong><small>GO FIND OUT</small></div>
          </div>
        </section>

        <section className="category-strip" aria-label="Explore event categories">
          <div className="section-intro"><span className="mini-label">FIND YOUR THING</span><h2>What are you<br />in the mood for?</h2></div>
          <div className="category-list">
            {categories.map(({ name, icon: Icon, filter, poster }) => <button className="category-pill" key={name} onClick={() => chooseCategory(filter)} style={{ "--category-poster": `url("${poster}")` }}><span><Icon size={20} /></span><b>{name}</b><ChevronRight size={16} /></button>)}
          </div>
        </section>

        <section className="discover-section" id="discover">
          <div className="section-header">
            <div><span className="mini-label">OUT THERE, WAITING</span><h2>Discover <em>what's on.</em></h2><p>Experiences for every mood, right around the corner or worth the trip.</p></div>
            <div className="tabs"><button className={tab === "events" ? "selected" : ""} onClick={() => setTab("events")}>Events <span>{visibleEvents.length}</span></button><button className={tab === "movies" ? "selected" : ""} onClick={() => setTab("movies")}>Movies <span>{visibleMovies.length}</span></button></div>
          </div>
          {tab === "events" && <div className="filter-row"><div className="filter-label"><SlidersHorizontal size={16} /> FILTER BY</div>{[["all","All events"],["major","Major events"],["local","Local picks"]].map(([value,label]) => <button key={value} className={eventType === value ? "filter-chip selected" : "filter-chip"} onClick={() => setEventType(value)}>{label}</button>)}<span className="result-count">{visibleEvents.length} experiences</span></div>}
          {loading ? <div className="loading-state"><RefreshCw className="spin" size={22} /> Finding what's on...</div> :
            tab === "events" ? (
              visibleEvents.length ? <div className="event-grid">{visibleEvents.map((item) => <EventCard key={item.id} item={item} saved={saved.includes(item.id)} onSave={toggleSaved} onBook={bookItem} />)}</div> :
                <div className="empty-state"><CalendarDays size={28} /><h3>No events found</h3><p>Try another city, search term, or event filter.</p><button className="secondary-button" onClick={() => { setSearch(""); setCity("All cities"); setEventType("all"); }}>Clear filters</button></div>
            ) : (
              visibleMovies.length ? <div className="movie-grid">{visibleMovies.map((item) => <MovieCard key={item.id} item={item} onBook={bookItem} />)}</div> :
                <div className="empty-state"><Film size={28} /><h3>No movies found</h3><p>Try a different title or language.</p><button className="secondary-button" onClick={() => setSearch("")}>Clear search</button></div>
            )
          }
        </section>

        <section className="local-banner">
          <div className="local-banner-mark"><MapPin size={24} /></div>
          <div><span className="mini-label">YOUR NEIGHBOURHOOD HAS A STORY</span><h2>Great things happen <em>locally.</em></h2><p>From campus stages to community workshops, make room for the things happening close to home.</p></div>
          <button onClick={() => { setEventType("local"); setTab("events"); setSearch(""); document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" }); }}>Explore local events <ArrowUpRight size={17} /></button>
        </section>
      </main>

      <footer className="footer"><a className="brand footer-brand" href="#"><span className="brand-mark"><Ticket size={18} /></span><span>Cine<span>Book</span><small>YOUR CITY. YOUR SCENE.</small></span></a><p>Made for the moments you’ll remember.</p><div><span className={`api-indicator ${apiOnline ? "online" : ""}`}></span>{apiOnline ? "Connected to local API" : "Showing preview data"}</div><small>© 2026 CineBook · DBMS project</small></footer>

      {notice && <div className="toast" role="status"><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Dismiss"><X size={16} /></button></div>}

      {accountOpen && <div className="modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setAccountOpen(false); }}><div className="account-modal" role="dialog" aria-modal="true" aria-labelledby="account-title"><button className="icon-button modal-close" onClick={() => setAccountOpen(false)} aria-label="Close"><X /></button><span className="mini-label">YOUR CINEBOOK</span><h2 id="account-title">Your bookings.</h2><p className="account-email">Signed in as {currentUser?.email}</p>{bookingsError && <p className="form-error" role="alert">{bookingsError}</p>}{bookingsLoading ? <p className="booking-hint">Loading your booking history…</p> : bookings.length ? <div className="booking-list">{bookings.map((booking) => <article className="booking-record" key={booking.id}><div><span className="booking-reference">{booking.booking_reference}</span><span className={`booking-status status-${booking.status}`}>{booking.status}</span></div><p>Session #{booking.session_id} · ₹{Number(booking.total_amount).toFixed(2)}</p><small>Booking ID {booking.id}</small>{booking.status === "confirmed" && <button className="cancel-booking" disabled={cancellingBookingId === booking.id} onClick={() => cancelBooking(booking.id)}>{cancellingBookingId === booking.id ? "Cancelling…" : "Cancel booking"}</button>}</article>)}</div> : <div className="empty-bookings"><Ticket size={27} /><p>No bookings yet. Find a movie or event and book your first experience.</p></div>}<div className="account-actions"><button className="secondary-button" onClick={() => { setAccountOpen(false); setToken(""); setCurrentUser(null); setNotice("You have signed out."); }}>Sign out</button><button className="primary-button" onClick={() => setAccountOpen(false)}>Done</button></div></div></div>}

      {authOpen && <div className="modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setAuthOpen(false); }}><div className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title"><button className="icon-button modal-close" onClick={() => setAuthOpen(false)} aria-label="Close"><X /></button><span className="mini-label">WELCOME TO CINEBOOK</span><h2 id="auth-title">{authMode === "login" ? "Good to see you." : "Create your account."}</h2><p className="auth-subtitle">{authMode === "login" ? "Sign in to save your plans and book tickets." : "Join CineBook and discover things happening around you."}</p><form className="auth-form" onSubmit={submitAuth}>{authMode === "register" && <><label>Full name<input value={authName} onChange={(event) => setAuthName(event.target.value)} minLength={2} required autoComplete="name" /></label><label>Phone number <span className="field-optional">optional</span><input type="tel" value={authPhone} onChange={(event) => setAuthPhone(event.target.value)} maxLength={30} autoComplete="tel" /></label></>}<label>Email address<input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} required autoComplete="email" /></label><label>Password<input type="password" value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} minLength={8} required autoComplete={authMode === "login" ? "current-password" : "new-password"} /></label>{authError && <p className="form-error" role="alert">{authError}</p>}<button className="primary-button auth-submit" type="submit" disabled={authBusy}>{authBusy ? "Please wait..." : authMode === "login" ? "Sign in" : "Create account"}</button></form><p className="auth-switch">{authMode === "login" ? "New to CineBook?" : "Already have an account?"} <button onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }}> {authMode === "login" ? "Create account" : "Sign in"}</button></p></div></div>}

      {selected && <div className="modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget && bookingStep !== "confirmed") setSelected(null); }}>
        <div className={`detail-modal booking-modal ${bookingStep === "confirmed" ? "ticket-confirmed-modal" : ""}`} role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <button className="icon-button modal-close" onClick={() => setSelected(null)} aria-label="Close"><X /></button>
          <ImageOrFallback src={selected.poster_url} fallbackSrc={getCategoryPoster(selected)} alt={selected.title} className="modal-poster" />
          <div className="modal-content">
            <span className="mini-label">{selected.demo ? "SAMPLE PREVIEW" : selected.language || selected.category?.name || "CINEBOOK"}</span>
            <h2 id="modal-title">{selected.title}</h2>
            <p>{selected.description || selected.synopsis || "Explore the details and upcoming sessions for this listing."}</p>
            {selected.event_type && <div className="modal-fact"><MapPin size={16} />{selected.venue?.name || "Venue details"} · {selected.city?.name || "City details"}</div>}

            {selected.demo ? <div className="preview-note"><Sparkles size={17} /><span>Sample catalogue preview. Run the backend demo seeder to create bookable sessions, live seat inventory and checkout pricing for this listing. Preview-only cards cannot take bookings.</span></div> : <>
              <div className="booking-stepper" aria-label="Booking progress">
                <span className={bookingStep === "select" ? "active" : bookingStep !== "select" ? "done" : ""}>1 <b>Show & seats</b></span>
                <i />
                <span className={bookingStep === "checkout" ? "active" : bookingStep === "confirmed" ? "done" : ""}>2 <b>Checkout</b></span>
                <i />
                <span className={bookingStep === "confirmed" ? "active" : ""}>3 <b>Ticket</b></span>
              </div>

              {bookingStep === "select" && <>
                <label className="booking-label">Choose date and showtime
                  <select value={selectedSessionId} onChange={(event) => setSelectedSessionId(event.target.value)}>
                    <option value="">Select session</option>
                    {availableSessions.map((item) => <option key={item.id} value={item.id}>{prettyDate(item.starts_at)} · {prettyTime(item.starts_at)} · From ₹{Number(item.base_price).toFixed(0)}</option>)}
                  </select>
                </label>
                {activeSession && <p className="booking-hint session-location"><MapPin size={14} />{activeSession.venue?.name || selected.venue?.name || "Venue / screen details"} {activeSession.venue_space?.name ? `· ${activeSession.venue_space.name}` : ""}</p>}
                {availabilityLoading && <p className="booking-hint">Checking seats and ticket availability…</p>}

                {sessionAvailability && sessionAvailability.booking_mode === "seats" && <>
                  <div className="seat-picker">
                    <div className="screen-label">SCREEN</div>
                    <div className="seat-legend">
                      <span><i className="legend-seat available" />Available</span>
                      <span><i className="legend-seat chosen" />Selected</span>
                      <span><i className="legend-seat unavailable" />Booked</span>
                    </div>
                    <div className="seat-grid">{sessionAvailability.seats.map((seat) => <button type="button" key={seat.id} title={`Row ${seat.row_label}, seat ${seat.seat_number} · ₹${Number(seat.price ?? sessionAvailability.base_price).toFixed(0)}`} disabled={!seat.available} className={`seat ${seat.available ? "" : "unavailable"} ${selectedSeats.includes(seat.id) ? "chosen" : ""} seat-${String(seat.seat_category || "standard").toLowerCase()}`} onClick={() => setSelectedSeats((current) => current.includes(seat.id) ? current.filter((id) => id !== seat.id) : [...current, seat.id])}>{seat.row_label}{seat.seat_number}</button>)}</div>
                    <p className="booking-hint">{selectedSeats.length} seat(s) selected · ₹{bookingSubtotal.toFixed(2)} subtotal</p>
                    {selectedSeatRows.length > 0 && <div className="selected-seat-chips">{selectedSeatRows.map((seat) => <span key={seat.id}>{seat.row_label}{seat.seat_number} · ₹{Number(seat.price ?? sessionAvailability.base_price).toFixed(0)}</span>)}</div>}
                  </div>
                </>}

                {sessionAvailability && sessionAvailability.booking_mode === "general_admission" && <div className="ticket-picker">
                  <label className="booking-label">Ticket category
                    <select value={selectedTicketTypeId} onChange={(event) => setSelectedTicketTypeId(event.target.value)}>
                      <option value="">Choose ticket type</option>
                      {sessionAvailability.ticket_types.map((ticket) => <option key={ticket.id} value={ticket.id} disabled={ticket.remaining < 1}>{ticket.name} · ₹{Number(ticket.price).toFixed(0)} · {ticket.remaining} left</option>)}
                    </select>
                  </label>
                  <label className="booking-label">Number of tickets
                    <select value={bookingQuantity} onChange={(event) => setBookingQuantity(Number(event.target.value))}>
                      {Array.from({ length: Math.min(10, selectedTicket?.remaining || 10) }, (_, index) => index + 1).map((amount) => <option key={amount} value={amount}>{amount}</option>)}
                    </select>
                  </label>
                </div>}

                {sessionAvailability && <div className="price-breakdown">
                  <div><span>Ticket subtotal</span><b>₹{bookingSubtotal.toFixed(2)}</b></div>
                  <div><span>Taxes {bookingTaxPercent ? `(${bookingTaxPercent}%)` : ""}</span><b>₹{bookingTax.toFixed(2)}</b></div>
                  <div><span>Convenience fee</span><b>₹{bookingConvenience.toFixed(2)}</b></div>
                  <div className="price-total"><span>Payable total</span><b>₹{bookingGrandTotal.toFixed(2)}</b></div>
                </div>}
                {bookingError && <p className="form-error" role="alert">{bookingError}</p>}
                <div className="modal-actions">
                  <button className="primary-button" disabled={availabilityLoading || !sessionAvailability || bookingSubtotal <= 0} onClick={continueToCheckout}>Continue to checkout <ChevronRight size={17} /></button>
                  <button className="secondary-button" onClick={() => { toggleSaved(selected.id); setNotice(saved.includes(selected.id) ? "Removed from saved listings." : "Saved for later."); }}><Heart size={16} /> Save</button>
                </div>
                <p className="demo-payment-note">Preview inventory and prices are seeded for this academic demo. Availability is not a live venue feed.</p>
              </>}

              {bookingStep === "checkout" && <div className="checkout-panel">
                <h3>Complete your booking</h3>
                <p className="booking-hint">Review the details before confirming this simulated payment.</p>
                <div className="checkout-recap">
                  <div><span>Experience</span><b>{selected.title}</b></div>
                  <div><span>Show</span><b>{activeSession ? `${prettyDate(activeSession.starts_at)} · ${prettyTime(activeSession.starts_at)}` : `Session #${selectedSessionId}`}</b></div>
                  <div><span>Venue</span><b>{selected.venue?.name || activeSession?.venue?.name || "Venue details"}</b></div>
                  <div><span>Tickets</span><b>{sessionAvailability?.booking_mode === "seats" ? selectedSeatRows.map((seat) => `${seat.row_label}${seat.seat_number}`).join(", ") : `${bookingQuantity} × ${selectedTicket?.name || "Ticket"}`}</b></div>
                  <div><span>Booking under</span><b>{currentUser?.name || currentUser?.email}</b></div>
                  <div><span>Contact email</span><b>{currentUser?.email}</b></div>
                  {currentUser?.phone && <div><span>Phone</span><b>{currentUser.phone}</b></div>}
                </div>
                <h4>Choose a demo payment method</h4>
                <div className="payment-methods">
                  {[
                    ["demo_upi", "UPI", "Simulated UPI approval"],
                    ["demo_card", "Card", "No card number required"],
                    ["demo_netbanking", "Netbanking", "Simulated bank redirect"],
                  ].map(([value, label, detail]) => <button type="button" key={value} className={paymentMethod === value ? "payment-method selected" : "payment-method"} onClick={() => setPaymentMethod(value)}><span className="payment-radio">{paymentMethod === value ? "●" : ""}</span><span><b>{label}</b><small>{detail}</small></span></button>)}
                </div>
                <div className="price-breakdown">
                  <div><span>Ticket subtotal</span><b>₹{bookingSubtotal.toFixed(2)}</b></div>
                  <div><span>Taxes</span><b>₹{bookingTax.toFixed(2)}</b></div>
                  <div><span>Convenience fee</span><b>₹{bookingConvenience.toFixed(2)}</b></div>
                  <div className="price-total"><span>Total to pay</span><b>₹{bookingGrandTotal.toFixed(2)}</b></div>
                </div>
                {bookingError && <p className="form-error" role="alert">{bookingError}</p>}
                <div className="demo-safe-note"><span>DEMO CHECKOUT</span><p>No real payment is processed. Do not enter bank, card, CVV, UPI PIN or OTP details.</p></div>
                <label className="booking-terms"><input type="checkbox" checked={bookingAccepted} onChange={(event) => setBookingAccepted(event.target.checked)} /><span>I have reviewed the show details, ticket quantity, price breakdown and demo-only cancellation policy.</span></label>
                <div className="modal-actions">
                  <button className="secondary-button" onClick={() => setBookingStep("select")}>← Back to seats</button>
                  <button className="primary-button" disabled={bookingBusy || !bookingAccepted} onClick={submitBooking}>{bookingBusy ? "Processing demo payment…" : `Pay ₹${bookingGrandTotal.toFixed(2)} (Demo)`</button>
                </div>
              </div>}

              {bookingStep === "confirmed" && bookingResult && <div className="ticket-confirmation" id="printable-ticket">
                <div className="ticket-success-mark">✓</div>
                <span className="mini-label">CINEBOOK E-TICKET</span>
                <h3>Booking confirmed!</h3>
                <p>Your demo ticket has been issued. Keep this code for check-in simulation.</p>
                <div className="issued-ticket-code">{bookingResult.ticket_code || bookingResult.booking_reference}</div>
                <div className="checkout-recap">
                  <div><span>Booking reference</span><b>{bookingResult.booking_reference}</b></div>
                  <div><span>Experience</span><b>{selected.title}</b></div>
                  <div><span>Show</span><b>{activeSession ? `${prettyDate(activeSession.starts_at)} · ${prettyTime(activeSession.starts_at)}` : `Session #${bookingResult.session_id}`}</b></div>
                  <div><span>Tickets / seats</span><b>{sessionAvailability?.booking_mode === "seats" ? selectedSeatRows.map((seat) => `${seat.row_label}${seat.seat_number}`).join(", ") : `${bookingQuantity} × ${selectedTicket?.name || "Ticket"}`}</b></div>
                  <div><span>Total paid (simulation)</span><b>₹{Number(bookingResult.total_amount).toFixed(2)}</b></div>
                  <div><span>Payment status</span><b className="payment-approved">Demo payment successful</b></div>
                </div>
                <div className="demo-safe-note"><span>NO MONEY CHARGED</span><p>This is a simulated ticket for your CineBook project. It is not valid for entry to the real venue.</p></div>
                <div className="modal-actions">
                  <button className="secondary-button" onClick={() => window.print()}>Print ticket</button>
                  <button className="primary-button" onClick={() => { setSelected(null); setBookingStep("select"); setBookingResult(null); }}>Back to discovery</button>
                </div>
              </div>}
            </>}
          </div>
        </div>
      </div>}
    </div>
  );
}
