"""Manual integration-test outline: run against PostgreSQL, not SQLite.

Create two concurrent POST /api/bookings requests with identical service_id and
starts_at. Assert exactly one returns 200 and the other returns 409. The unique
database constraint is the final guard against races.
"""
