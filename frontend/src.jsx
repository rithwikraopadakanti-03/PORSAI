
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

import {
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  useConnectionState,
  useLocalParticipant
} from '@livekit/components-react';

import { ConnectionState } from 'livekit-client';

import '@livekit/components-styles';
import './style.css';

const API =
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000';

function formatDate(value) {
  return new Date(value).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Request failed (${response.status})`
    );
  }

  return data;
}

// --------------------------------------------------
// VOICE CALL CONTROLS
// --------------------------------------------------

function CallControls() {
  const state = useConnectionState();
  const { localParticipant } = useLocalParticipant();

  const [muted, setMuted] = useState(false);
  const [micError, setMicError] = useState('');

  const connected = state === ConnectionState.Connected;

  async function toggleMic() {
    try {
      const next = !muted;

      await localParticipant.setMicrophoneEnabled(!next);

      setMuted(next);
      setMicError('');
    } catch (error) {
      setMicError(error.message || 'Microphone error');
    }
  }

  return (
    <div className="call-controls">
      <div className="live-indicator">
        <span className="live-dot" />
        {connected ? 'CONNECTED TO AI RECEPTIONIST' : `STATUS: ${state}`}
      </div>

      <p className="call-message">
        {connected
          ? 'Your Sunrise Salon assistant is ready. Start speaking.'
          : 'Connecting to your receptionist...'}
      </p>

      <button
        className="secondary-button"
        onClick={toggleMic}
        disabled={!connected}
      >
        {muted ? 'Unmute microphone' : 'Mute microphone'}
      </button>

      {micError && <p className="error-message">{micError}</p>}

      <div className="audio-start">
        <StartAudio label="Enable AI speaker audio" />
      </div>

      <p className="muted-text">
        Allow microphone access and enable speaker audio.
      </p>
    </div>
  );
}

// --------------------------------------------------
// VOICE RECEPTIONIST
// --------------------------------------------------

function VoicePage() {
  const [session, setSession] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function startCall() {
    setError('');
    setLoading(true);

    try {
      const data = await request('/api/livekit/token', {
        method: 'POST'
      });

      if (!data.url || !data.token) {
        throw new Error('LiveKit URL or token is missing.');
      }

      setSession(data);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  function endCall() {
    setSession(null);
    setError('');
  }

  return (
    <div className="page-content">
      <section className="hero-section">
        <div className="hero-copy">
          <span className="eyebrow">SUNRISE SALON · BENGALURU</span>

          <h1>
            Beauty begins
            <br />
            with a <span>conversation.</span>
          </h1>

          <p>
            Meet your personal AI salon receptionist.
            Ask about services, prices and appointments,
            or simply speak to arrange your next visit.
          </p>

          {!session ? (
            <button
              className="primary-button"
              onClick={startCall}
              disabled={loading}
            >
              {loading ? 'Connecting...' : '☎  Call Sunrise Salon'}
            </button>
          ) : (
            <button className="danger-button" onClick={endCall}>
              End Call
            </button>
          )}

          {error && <p className="error-message">{error}</p>}

          <div className="hero-note">
            <span>✦</span>
            Available to help with your salon appointments
          </div>
        </div>

        <div className="hero-art">
          <div className="art-circle">
            <div className="art-inner">
              <span className="art-flower">✿</span>
              <span className="art-name">SUNRISE</span>
              <span className="art-small">BEAUTY · CARE · YOU</span>
            </div>
          </div>

          <div className="floating-card">
            <span className="floating-icon">✧</span>
            <div>
              <strong>Your beauty, our priority.</strong>
              <small>Personalised salon assistance</small>
            </div>
          </div>
        </div>
      </section>

      {session && (
        <section className="call-panel">
          <LiveKitRoom
            serverUrl={session.url}
            token={session.token}
            connect={true}
            audio={true}
            video={false}
            onError={(error) =>
              setError(error.message || 'LiveKit connection error')
            }
          >
            <CallControls />
            <RoomAudioRenderer />
          </LiveKitRoom>
        </section>
      )}

      <section className="feature-strip">
        <div>
          <span>01</span>
          <h3>Speak naturally</h3>
          <p>Talk to our AI receptionist.</p>
        </div>

        <div>
          <span>02</span>
          <h3>Explore services</h3>
          <p>Ask about salon treatments.</p>
        </div>

        <div>
          <span>03</span>
          <h3>Book an appointment</h3>
          <p>Find a suitable available slot.</p>
        </div>
      </section>
    </div>
  );
}

// --------------------------------------------------
// CUSTOMER DASHBOARD
// --------------------------------------------------

function CustomerDashboard() {
  const [phone, setPhone] = useState('');
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');

  async function findBookings(event) {
    event.preventDefault();

    if (phone.trim().length < 5) {
      setError('Please enter a valid phone number.');
      return;
    }

    setLoading(true);
    setError('');
    setSearched(false);

    try {
      const data = await request(
        `/api/customer/bookings?phone=${encodeURIComponent(phone.trim())}`
      );

      setBookings(data.bookings || []);
      setSearched(true);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-content dashboard-page">
      <div className="section-heading">
        <span className="eyebrow">YOUR SALON EXPERIENCE</span>
        <h1>My appointments<span>.</span></h1>
        <p>View your Sunrise Salon booking history in one place.</p>
      </div>

      <section className="lookup-card">
        <div className="lookup-icon">♙</div>

        <div className="lookup-content">
          <h2>Find your bookings</h2>
          <p>Enter the phone number used when making your appointment.</p>

          <form onSubmit={findBookings} className="lookup-form">
            <input
              type="tel"
              placeholder="Enter your phone number"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
            />

            <button className="primary-button" disabled={loading}>
              {loading ? 'Searching...' : 'Find appointments'}
            </button>
          </form>

          {error && <p className="error-message">{error}</p>}
        </div>
      </section>

      {searched && (
        <section className="results-section">
          <div className="results-heading">
            <div>
              <span className="eyebrow">BOOKING HISTORY</span>
              <h2>Your appointments</h2>
            </div>

            <span className="count-pill">
              {bookings.length} found
            </span>
          </div>

          {bookings.length === 0 ? (
            <div className="empty-state">
              <span>✧</span>
              <h3>No appointments found</h3>
              <p>We couldn't find bookings for this phone number.</p>
            </div>
          ) : (
            <div className="booking-grid">
              {bookings.map((booking) => (
                <BookingCard
                  key={booking.id}
                  booking={booking}
                  customerView={true}
                />
              ))}
            </div>
          )}
        </section>
      )}

      <p className="privacy-note">
        For this demonstration, booking lookup uses a phone number.
        It does not verify customer identity.
      </p>
    </div>
  );
}

// --------------------------------------------------
// BOOKING CARD
// --------------------------------------------------

function BookingCard({
  booking,
  customerView = false,
  onComplete,
  onDelete,
  busy
}) {
  return (
    <article className="booking-card">
      <div className="booking-card-top">
        <span className="booking-id">
          BOOKING #{booking.id}
        </span>

        <span className={`status-pill ${booking.status}`}>
          {booking.status}
        </span>
      </div>

      <h3>{booking.service}</h3>

      <div className="booking-details">
        <div>
          <span>Customer</span>
          <strong>{booking.customer_name}</strong>
        </div>

        {!customerView && (
          <div>
            <span>Phone</span>
            <strong>{booking.customer_phone}</strong>
          </div>
        )}

        <div>
          <span>Stylist</span>
          <strong>{booking.stylist}</strong>
        </div>

        <div>
          <span>Appointment date</span>
          <strong>{formatDate(booking.starts_at)}</strong>
        </div>

        <div>
          <span>Appointment time</span>
          <strong>{formatTime(booking.starts_at)}</strong>
        </div>
      </div>

      {!customerView && (
        <div className="booking-actions">
          {booking.status === 'booked' && (
            <button
              className="complete-button"
              onClick={() => onComplete(booking.id)}
              disabled={busy}
            >
              Mark completed
            </button>
          )}

          {booking.status === 'completed' && (
            <button
              className="delete-button"
              onClick={() => onDelete(booking.id)}
              disabled={busy}
            >
              Delete booking
            </button>
          )}
        </div>
      )}
    </article>
  );
}

// --------------------------------------------------
// STAFF DASHBOARD
// --------------------------------------------------

function StaffDashboard() {
  const [password, setPassword] = useState('');
  const [authenticated, setAuthenticated] = useState(false);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function loadBookings(event) {
    if (event) event.preventDefault();

    setLoading(true);
    setError('');
    setNotice('');

    try {
      const data = await request('/api/staff/bookings', {
        headers: {
          'x-staff-password': password
        }
      });

      setBookings(data.bookings || []);
      setAuthenticated(true);
    } catch (error) {
      setAuthenticated(false);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function completeBooking(id) {
    if (!window.confirm(`Mark booking #${id} as completed?`)) {
      return;
    }

    setBusyId(id);
    setError('');
    setNotice('');

    try {
      await request(`/api/staff/bookings/${id}/complete`, {
        method: 'PATCH',
        headers: {
          'x-staff-password': password
        }
      });

      setNotice(`Booking #${id} marked as completed.`);
      await loadBookings();
    } catch (error) {
      setError(error.message);
    } finally {
      setBusyId(null);
    }
  }

  async function deleteBooking(id) {
    if (!window.confirm(`Permanently delete completed booking #${id}?`)) {
      return;
    }

    setBusyId(id);
    setError('');
    setNotice('');

    try {
      await request(`/api/staff/bookings/${id}`, {
        method: 'DELETE',
        headers: {
          'x-staff-password': password
        }
      });

      setNotice(`Booking #${id} deleted successfully.`);
      await loadBookings();
    } catch (error) {
      setError(error.message);
    } finally {
      setBusyId(null);
    }
  }

  function logout() {
    setAuthenticated(false);
    setPassword('');
    setBookings([]);
    setNotice('');
    setError('');
  }

  if (!authenticated) {
    return (
      <div className="page-content dashboard-page">
        <div className="section-heading">
          <span className="eyebrow">TEAM PORTAL</span>
          <h1>Staff access<span>.</span></h1>
          <p>Sign in to manage Sunrise Salon appointments.</p>
        </div>

        <section className="staff-login-card">
          <div className="login-icon">♙</div>
          <h2>Welcome back</h2>
          <p>Enter your staff password to continue.</p>

          <form onSubmit={loadBookings}>
            <label htmlFor="staff-password">Staff password</label>

            <input
              id="staff-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter staff password"
              required
            />

            <button className="primary-button" disabled={loading}>
              {loading ? 'Signing in...' : 'Access dashboard'}
            </button>
          </form>

          {error && <p className="error-message">{error}</p>}
        </section>
      </div>
    );
  }

  const bookedCount = bookings.filter(
    (booking) => booking.status === 'booked'
  ).length;

  const completedCount = bookings.filter(
    (booking) => booking.status === 'completed'
  ).length;

  return (
    <div className="page-content dashboard-page">
      <div className="staff-heading">
        <div className="section-heading">
          <span className="eyebrow">SALON MANAGEMENT</span>
          <h1>Staff dashboard<span>.</span></h1>
          <p>Manage appointments and daily salon activity.</p>
        </div>

        <div className="staff-heading-actions">
          <button
            className="secondary-button"
            onClick={() => loadBookings()}
            disabled={loading}
          >
            ↻ Refresh
          </button>

          <button className="logout-button" onClick={logout}>
            Sign out
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span>Total appointments</span>
          <strong>{bookings.length}</strong>
          <small>All booking records</small>
        </div>

        <div className="stat-card">
          <span>Upcoming / booked</span>
          <strong>{bookedCount}</strong>
          <small>Awaiting completion</small>
        </div>

        <div className="stat-card">
          <span>Completed</span>
          <strong>{completedCount}</strong>
          <small>Finished appointments</small>
        </div>
      </div>

      {notice && <div className="success-message">{notice}</div>}
      {error && <div className="error-message">{error}</div>}

      <div className="results-heading staff-results-heading">
        <div>
          <span className="eyebrow">APPOINTMENT MANAGEMENT</span>
          <h2>All bookings</h2>
        </div>

        <span className="count-pill">
          {bookings.length} records
        </span>
      </div>

      {bookings.length === 0 ? (
        <div className="empty-state">
          <span>✧</span>
          <h3>No appointments yet</h3>
          <p>New salon bookings will appear here.</p>
        </div>
      ) : (
        <div className="booking-grid">
          {bookings.map((booking) => (
            <BookingCard
              key={booking.id}
              booking={booking}
              onComplete={completeBooking}
              onDelete={deleteBooking}
              busy={busyId === booking.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --------------------------------------------------
// MAIN APPLICATION
// --------------------------------------------------

function App() {
  const [activePage, setActivePage] = useState('home');

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          className="brand"
          onClick={() => setActivePage('home')}
        >
          <span className="brand-symbol">✿</span>
          <span>
            SUNRISE
            <small>SALON & BEAUTY</small>
          </span>
        </button>

        <nav className="navigation">
          <button
            className={activePage === 'home' ? 'nav-active' : ''}
            onClick={() => setActivePage('home')}
          >
            Home
          </button>

          <button
            className={activePage === 'customer' ? 'nav-active' : ''}
            onClick={() => setActivePage('customer')}
          >
            My Appointments
          </button>

          <button
            className={activePage === 'staff' ? 'nav-active' : ''}
            onClick={() => setActivePage('staff')}
          >
            Staff Portal
          </button>
        </nav>

        <button
          className="header-cta"
          onClick={() => setActivePage('home')}
        >
          <span>✧</span> AI Receptionist
        </button>
      </header>

      <main>
        {activePage === 'home' && <VoicePage />}
        {activePage === 'customer' && <CustomerDashboard />}
        {activePage === 'staff' && <StaffDashboard />}
      </main>

      <footer className="site-footer">
        <div className="footer-brand">
          <span className="brand-symbol">✿</span>
          <strong>Sunrise Salon</strong>
        </div>

        <p>12 Lake Road, Indiranagar, Bengaluru</p>
        <p>Beauty, care and a little sunshine.</p>

        <span className="copyright">
          © {new Date().getFullYear()} Sunrise Salon. All rights reserved.
        </span>
      </footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
