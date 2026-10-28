import { useEffect, useMemo, useState } from "react";
import {
  Search, MapPin, Ticket, CalendarDays, Film, Music2, Laugh,
  GraduationCap, ChevronRight, Heart, Menu, X, Clock3, ArrowUpRight,
  Sparkles, SlidersHorizontal, RefreshCw, CircleUserRound
} from "lucide-react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const demoMovies = [
  { id: "dm1", title: "The Last Horizon", language: "English", duration_minutes: 128, synopsis: "An unforgettable journey beyond the edge of the known world.", poster_url: "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?auto=format&fit=crop&w=800&q=85", demo: true },
  { id: "dm2", title: "Midnight in Mumbai", language: "Hindi", duration_minutes: 142, synopsis: "One city. One night. A thousand untold stories.", poster_url: "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=85", demo: true },
  { id: "dm3", title: "Echoes of Tomorrow", language: "English", duration_minutes: 116, synopsis: "A scientist discovers that tomorrow is closer than it seems.", poster_url: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=85", demo: true },
  { id: "dm4", title: "The Blue Hour", language: "Hindi", duration_minutes: 104, synopsis: "A small-town musician gets one chance to change everything.", poster_url: "https://images.unsplash.com/photo-1506157786151-b8491531f063?auto=format&fit=crop&w=800&q=85", demo: true }
];

const demoEvents = [
  { id: "de1", title: "Guwahati Riverfront Music Fest", event_type: "major", city: { name: "Guwahati" }, venue: { name: "Brahmaputra Riverside Grounds" }, category: { name: "Concert" }, starts_at: "2026-12-12T17:30:00", poster_url: "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?auto=format&fit=crop&w=900&q=85", description: "An open-air night of live music on the Brahmaputra.", demo: true },
  { id: "de2", title: "Campus Creators Day", event_type: "local", city: { name: "Tezpur" }, venue: { name: "University Auditorium" }, category: { name: "College Fest" }, starts_at: "2026-11-18T10:00:00", poster_url: "https://images.unsplash.com/photo-1523580494863-6f3031224c94?auto=format&fit=crop&w=900&q=85", description: "Student showcases, clubs, workshops, and performances.", demo: true },
  { id: "de3", title: "Stand-up by the River", event_type: "local", city: { name: "Guwahati" }, venue: { name: "The Laugh Room" }, category: { name: "Comedy" }, starts_at: "2026-11-21T19:00:00", poster_url: "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?auto=format&fit=crop&w=900&q=85", description: "A local comedy line-up for your weekend plans.", demo: true },
  { id: "de4", title: "Build with AI: Weekend Workshop", event_type: "local", city: { name: "Guwahati" }, venue: { name: "Innovation Studio" }, category: { name: "Workshop" }, starts_at: "2026-11-28T11:00:00", poster_url: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=85", description: "A practical, beginner-friendly build day for curious minds.", demo: true }
];

const categories = [
  { name: "Concerts", icon: Music2, filter: "Concert" },
  { name: "Comedy", icon: Laugh, filter: "Comedy" },
  { name: "College fests", icon: GraduationCap, filter: "College Fest" },
  { name: "Workshops", icon: Sparkles, filter: "Workshop" },
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

function ImageOrFallback({ src, alt, className = "" }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return <div className={`image-fallback ${className}`} aria-label={alt}><Film size={30} /><span>CineBook</span></div>;
  return <img className={className} src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}

function EventCard({ item, saved, onSave, onBook }) {
  return (
    <article className="event-card">
      <div className="event-poster-wrap">
        <ImageOrFallback src={item.poster_url} alt={item.title} className="event-poster" />
        <span className={`event-type ${item.event_type === "major" ? "major" : ""}`}>{item.event_type === "major" ? "FEATURED" : "LOCAL PICK"}</span>
        <button className={`icon-button save-button ${saved ? "is-saved" : ""}`} onClick={() => onSave(item.id)} aria-label={saved ? "Unsave event" : "Save event"}><Heart size={17} fill={saved ? "currentColor" : "none"} /></button>
      </div>
      <div className="event-card-body">
        <p className="eyebrow">{item.category?.name || "Experience"} <span>·</span> {item.city?.name || "Your city"}</p>
        <h3>{item.title}</h3>
        <p className="event-description">{item.description || "Discover something worth stepping out for."}</p>
        <div className="event-meta"><span><CalendarDays size={15} />{prettyDate(item.starts_at || item.start_time)}</span><span><Clock3 size={15} />{prettyTime(item.starts_at || item.start_time)}</span></div>
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
        <ImageOrFallback src={item.poster_url} alt={item.title} className="movie-poster" />
        <span className="poster-overlay"><span>View showtimes <ArrowUpRight size={16} /></span></span>
      </button>
      <div className="movie-info"><h3>{item.title}</h3><p>{item.language || "Language TBA"} <span>·</span> {item.duration_minutes ? `${item.duration_minutes} min` : "Duration TBA"}</p></div>
    </article>
  );
}

export default function App() {
  const [tab, setTab] = useState("events");
  const [city, setCity] = useState("All cities");
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
    setSearch(category);
    document.getElementById("discover")?.scrollIntoView({ behavior: "smooth" });
  }
  function bookItem(item) {
    setSelected(item);
  }

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
          <label className="city-select"><MapPin size={16} /><select value={city} onChange={(event) => setCity(event.target.value)} aria-label="Choose city"><option>All cities</option>{cities.map((item) => <option key={item.id}>{item.name}</option>)}{!cities.some((item) => item.name === "Guwahati") && <option>Guwahati</option>}{!cities.some((item) => item.name === "Tezpur") && <option>Tezpur</option>}</select></label>
          <button className="profile-button" onClick={() => setNotice("Account sign-in is available through the backend API; a dedicated account screen is the next frontend extension.")}><CircleUserRound size={19} /><span>Sign in</span></button>
          <button className="icon-button mobile-menu-button" onClick={() => setMobileMenu((value) => !value)} aria-label="Toggle navigation">{mobileMenu ? <X /> : <Menu />}</button>
        </div>
      </header>

      <main>
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
            {categories.map(({ name, icon: Icon, filter }) => <button className="category-pill" key={name} onClick={() => chooseCategory(filter)}><span><Icon size={20} /></span><b>{name}</b><ChevronRight size={16} /></button>)}
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
      {selected && <div className="modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setSelected(null); }}><div className="detail-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button className="icon-button modal-close" onClick={() => setSelected(null)} aria-label="Close"><X /></button><ImageOrFallback src={selected.poster_url} alt={selected.title} className="modal-poster" /><div className="modal-content"><span className="mini-label">{selected.demo ? "PREVIEW LISTING" : selected.language || selected.category?.name || "CINEBOOK"}</span><h2 id="modal-title">{selected.title}</h2><p>{selected.description || selected.synopsis || "Explore the details and upcoming sessions for this listing."}</p>{selected.event_type && <div className="modal-fact"><MapPin size={16} />{selected.venue?.name || "Venue details"} · {selected.city?.name || "City details"}</div>}{selected.starts_at && <div className="modal-fact"><CalendarDays size={16} />{prettyDate(selected.starts_at)} · {prettyTime(selected.starts_at)}</div>}<div className="modal-actions"><button className="primary-button" onClick={() => setNotice(selected.demo ? "This is preview content. Connect the backend and add a future session to enable real bookings." : "Choose a session from the booking API to continue.")}> <Ticket size={17} /> {selected.demo ? "Preview only" : "Check availability"}</button><button className="secondary-button" onClick={() => { toggleSaved(selected.id); setNotice(saved.includes(selected.id) ? "Removed from saved listings." : "Saved for later."); }}><Heart size={16} /> Save</button></div></div></div></div>}
    </div>
  );
}
