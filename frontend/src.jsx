
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

// IMPORTANT: Match this with your FastAPI backend port.
const API =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';


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
    <div className="controls">

      <p className="status">
        {connected
          ? 'Connected — speak to Sunrise Salon'
          : `Connection status: ${state}`}
      </p>

      <button
        onClick={toggleMic}
        disabled={!connected}
      >
        {muted ? 'Unmute microphone' : 'Mute microphone'}
      </button>

      {micError && (
        <p className="error">{micError}</p>
      )}

      <div style={{ marginTop: '15px' }}>
        <StartAudio label="Enable AI speaker audio" />
      </div>

      <p className="hint">
        If you cannot hear Sunrise Salon, click Enable AI speaker audio.
      </p>

    </div>
  );
}


function App() {

  const [session, setSession] = useState(null);

  const [error, setError] = useState('');

  const [loading, setLoading] = useState(false);


  async function call() {

    setError('');
    setLoading(true);

    try {

      const response = await fetch(
        `${API}/api/livekit/token`,
        {
          method: 'POST'
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || 'Could not create call token'
        );
      }

      if (!data.url || !data.token) {
        throw new Error(
          'LiveKit URL or token is missing from backend'
        );
      }

      setSession(data);

    } catch (error) {

      setError(error.message);

    } finally {

      setLoading(false);

    }
  }


  function disconnect() {
    setSession(null);
    setError('');
  }


  return (

    <main>

      <section className="panel">

        <div className="brand">
          ◉ <span>Sunrise Salon</span>
        </div>

        <p className="eyebrow">
          SUNRISE SALON · BENGALURU
        </p>

        <h1>
          Your salon, one conversation away.
        </h1>

        <p className="sub">
          Ask about services, prices and timings,
          or speak to our AI receptionist to
          arrange an appointment.
        </p>


        {!session ? (

          <button
            className="call"
            onClick={call}
            disabled={loading}
          >
            {loading
              ? 'Connecting...'
              : '☎  Call Sunrise Salon'}
          </button>

        ) : (

          <>

            <LiveKitRoom
              serverUrl={session.url}
              token={session.token}
              connect={true}
              audio={true}
              video={false}
              onError={(error) => {
                setError(
                  error.message || 'LiveKit connection error'
                );
              }}
            >

              <CallControls />

              <RoomAudioRenderer />

            </LiveKitRoom>

            <button
              onClick={disconnect}
              style={{ marginTop: '15px' }}
            >
              End Call
            </button>

          </>

        )}


        {error && (
          <p className="error">{error}</p>
        )}

        <p className="hint">
          Allow microphone access and enable speaker audio.
        </p>

      </section>


      <footer>
        12 Lake Road, Indiranagar, Bengaluru · Closed Sundays
      </footer>

    </main>

  );
}


createRoot(
  document.getElementById('root')
).render(<App />);
